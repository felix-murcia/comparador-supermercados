"""Caso de uso: buscar el precio de un producto en una cadena.

Orquesta productor → verificador → repositorios con un número acotado de
pasadas: se reintenta mientras el resultado no sea concluyente y se guarda
en la base de datos el precio verificado (o, agotadas las pasadas, el
sospechoso).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from src.dominio.precios.entidades import PrecioNuevo
from src.dominio.precios.errores import ErrorProductor
from src.dominio.precios.estados import EstadoPrecio
from src.dominio.precios.reglas import calcular_precio_por_litro
from src.dominio.productos.entidades import ProductoNuevo
from src.dominio.productos.reglas import normalizar_nombre
from src.puertos.productor import Candidato, Productor
from src.puertos.repositorios import (
    RepositorioCadenas,
    RepositorioPrecios,
    RepositorioProductos,
    RepositorioProductosCadenas,
)
from src.puertos.verificador import Verificador

logger = logging.getLogger(__name__)

MAX_PASADAS = 3
MOTIVO_CADENA_DESCONOCIDA = "cadena_desconocida"
MOTIVO_AGENTE_NO_ENCONTRO = "agente_no_encontro"
MOTIVO_SIN_CANDIDATO = "sin_candidato"


@dataclass(frozen=True)
class ResultadoBusqueda:
    """Resultado de una búsqueda: estado final, precio guardado y motivos."""

    estado: EstadoPrecio
    producto_cadena_id: UUID | None = None
    precio_id: UUID | None = None
    motivos: tuple[str, ...] = ()

    @property
    def guardado(self) -> bool:
        return self.precio_id is not None


def _a_decimal(valor: object) -> Decimal | None:
    if isinstance(valor, bool):
        return None
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    if isinstance(valor, str):
        try:
            return Decimal(valor.strip().replace(",", "."))
        except InvalidOperation:
            return None
    return None


def _texto(valor: object) -> str | None:
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    return None


class BuscarProducto:
    """Busca un producto en una cadena y persiste el precio encontrado."""

    def __init__(
        self,
        *,
        productor: Productor,
        verificador: Verificador,
        repositorio_cadenas: RepositorioCadenas,
        repositorio_productos: RepositorioProductos,
        repositorio_productos_cadenas: RepositorioProductosCadenas,
        repositorio_precios: RepositorioPrecios,
        max_pasadas: int = MAX_PASADAS,
    ) -> None:
        self._productor = productor
        self._verificador = verificador
        self._repositorio_cadenas = repositorio_cadenas
        self._repositorio_productos = repositorio_productos
        self._repositorio_productos_cadenas = repositorio_productos_cadenas
        self._repositorio_precios = repositorio_precios
        self._max_pasadas = max(1, max_pasadas)

    async def ejecutar(self, query: str, cadena: str) -> ResultadoBusqueda:
        datos_cadena = await self._repositorio_cadenas.obtener_por_slug(cadena)
        if datos_cadena is None:
            logger.warning("Cadena desconocida: %s", cadena)
            return ResultadoBusqueda(
                estado="rechazado", motivos=(MOTIVO_CADENA_DESCONOCIDA,)
            )

        pendiente: tuple[Candidato, UUID, EstadoPrecio, list[str]] | None = None

        for pasada in range(self._max_pasadas):
            try:
                candidato = await self._productor.producir(query, cadena)
            except ErrorProductor as error:
                if not error.reintentable or pasada + 1 >= self._max_pasadas:
                    return ResultadoBusqueda(
                        estado="rechazado", motivos=(error.motivo,)
                    )
                logger.info(
                    "El productor falló (pasada %s de %s): %s",
                    pasada + 1,
                    self._max_pasadas,
                    error.motivo,
                )
                continue

            if not candidato.get("encontrado"):
                return ResultadoBusqueda(
                    estado="rechazado", motivos=(MOTIVO_AGENTE_NO_ENCONTRO,)
                )

            producto_cadena_id = await self._resolver_producto_cadena(
                candidato, datos_cadena.id
            )
            candidato = await self._con_precio_anterior(candidato, producto_cadena_id)

            estado, motivos = await self._verificador.verificar(candidato)

            if estado == "verificado":
                return await self._guardar(
                    candidato, producto_cadena_id, "verificado", motivos
                )

            if MOTIVO_AGENTE_NO_ENCONTRO in motivos:
                return ResultadoBusqueda(estado="rechazado", motivos=tuple(motivos))

            pendiente = (candidato, producto_cadena_id, estado, motivos)

        if pendiente is not None and pendiente[2] == "sospechoso":
            return await self._guardar(
                pendiente[0], pendiente[1], "sospechoso", pendiente[3]
            )

        motivos = pendiente[3] if pendiente is not None else [MOTIVO_SIN_CANDIDATO]
        return ResultadoBusqueda(estado="rechazado", motivos=tuple(motivos))

    async def _guardar(
        self,
        candidato: Candidato,
        producto_cadena_id: UUID,
        estado: EstadoPrecio,
        motivos: list[str],
    ) -> ResultadoBusqueda:
        precio = await self._repositorio_precios.insertar(
            self._precio_nuevo(candidato, producto_cadena_id, estado)
        )
        return ResultadoBusqueda(
            estado=estado,
            producto_cadena_id=producto_cadena_id,
            precio_id=precio.id,
            motivos=tuple(motivos),
        )

    def _precio_nuevo(
        self, candidato: Candidato, producto_cadena_id: UUID, estado: EstadoPrecio
    ) -> PrecioNuevo:
        importe = _a_decimal(candidato.get("precio_eur")) or Decimal(0)
        contenido = _a_decimal(candidato.get("litros_o_kg"))
        return PrecioNuevo(
            producto_cadena_id=producto_cadena_id,
            importe_eur=importe,
            url_fuente=str(candidato.get("url_fuente") or ""),
            fecha_consulta=datetime.now(UTC),
            estado=estado,
            por_litro_kg=(
                calcular_precio_por_litro(importe, contenido) if contenido else None
            ),
        )

    async def _resolver_producto_cadena(
        self, candidato: Candidato, cadena_id: UUID
    ) -> UUID:
        producto_id = await self._resolver_producto(candidato)
        existente = (
            await self._repositorio_productos_cadenas.obtener_por_producto_y_cadena(
                producto_id, cadena_id
            )
        )
        if existente is not None:
            return existente

        return await self._repositorio_productos_cadenas.crear(
            producto_id=producto_id,
            cadena_id=cadena_id,
            url_producto=str(candidato.get("url_fuente") or ""),
            nombre_en_cadena=str(
                candidato.get("nombre_en_cadena") or candidato.get("nombre") or ""
            ),
        )

    async def _resolver_producto(self, candidato: Candidato) -> UUID:
        ean = _texto(candidato.get("ean"))
        if ean is not None:
            producto = await self._repositorio_productos.obtener_por_ean(ean)
            if producto is not None:
                return producto.id

        nombre = _texto(candidato.get("nombre")) or ""
        if nombre:
            coincidencias = await self._repositorio_productos.buscar_por_nombre(
                nombre, limite=5
            )
            objetivo = normalizar_nombre(nombre)
            for producto in coincidencias:
                if normalizar_nombre(producto.nombre) == objetivo:
                    return producto.id

        creado = await self._repositorio_productos.crear(
            ProductoNuevo(
                nombre=nombre or "Producto sin nombre",
                marca=_texto(candidato.get("marca")),
                categoria=_texto(candidato.get("categoria")),
                formato=_texto(candidato.get("formato")),
                litros_o_kg=_a_decimal(candidato.get("litros_o_kg")),
                ean=ean,
            )
        )
        return creado.id

    async def _con_precio_anterior(
        self, candidato: Candidato, producto_cadena_id: UUID
    ) -> Candidato:
        anterior = await self._repositorio_precios.ultimo_verificado(producto_cadena_id)
        if anterior is None:
            return candidato
        return {**candidato, "precio_eur_anterior": anterior.importe_eur}
