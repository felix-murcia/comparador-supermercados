"""Implementación SQLAlchemy de `RepositorioPrecios` (append-only)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from src.adaptadores.persistencia.mapeo import precio_desde_modelo
from src.adaptadores.persistencia.modelos import (
    CadenaModelo,
    PrecioModelo,
    ProductoCadenaModelo,
    ProductoModelo,
)
from src.dominio.precios.entidades import (
    FiltrosComparacion,
    HistoricoPrecio,
    PrecioNuevo,
    PrecioRegistrado,
    PrecioVigente,
    ResultadoComparacion,
)
from src.dominio.precios.estados import AmbitoPrecio

# Umbral de similitud de trigramas para encontrar un producto por nombre.
# Por debajo de 0,5 la similitud da falsos positivos ("leche" parecería con
# "leche de avena"); con consultas de menos de 6 letras solo se admite la
# coincidencia literal.
UMBRAL_SIMILITUD = 0.5
LONGITUD_MINIMA_SIMILITUD = 6


class SQLAlchemyRepositorioPrecios:
    """Solo `insertar` escribe; el histórico nunca se actualiza ni borra."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insertar(self, datos: PrecioNuevo) -> PrecioRegistrado:
        modelo = PrecioModelo(
            producto_cadena_id=datos.producto_cadena_id,
            precio_eur=datos.importe_eur,
            precio_por_litro_kg=datos.por_litro_kg,
            disponible=datos.disponible,
            promocion=datos.promocion,
            ambito=datos.ambito,
            provincia=datos.provincia,
            estado=datos.estado,
            url_fuente=datos.url_fuente,
            fecha_consulta=datos.fecha_consulta,
        )
        self._session.add(modelo)
        await self._session.flush()
        await self._session.refresh(modelo)
        return precio_desde_modelo(modelo)

    async def ultimo_verificado(
        self, producto_cadena_id: UUID
    ) -> PrecioRegistrado | None:
        modelo = await self._session.scalar(
            select(PrecioModelo)
            .where(
                PrecioModelo.producto_cadena_id == producto_cadena_id,
                PrecioModelo.estado == "verificado",
            )
            .order_by(
                PrecioModelo.fecha_consulta.desc(),
                PrecioModelo.creado_en.desc(),
            )
            .limit(1)
        )
        if modelo is None:
            return None
        return precio_desde_modelo(modelo)

    async def historico(
        self, producto_cadena_id: UUID, limite: int = 10
    ) -> list[PrecioRegistrado]:
        modelos = (
            await self._session.scalars(
                select(PrecioModelo)
                .where(PrecioModelo.producto_cadena_id == producto_cadena_id)
                .order_by(
                    PrecioModelo.fecha_consulta.desc(),
                    PrecioModelo.creado_en.desc(),
                )
                .limit(limite)
            )
        ).all()
        return [precio_desde_modelo(modelo) for modelo in modelos]

    async def buscar_comparativa(
        self, filtros: FiltrosComparacion
    ) -> list[ResultadoComparacion]:
        """Precios vigentes para la comparativa, con el alcance de ADR-009."""
        elegido = self._consulta_elegidos(filtros).cte("elegido")
        sentencia = (
            select(elegido)
            .where(*self._filtros_de_precio(elegido, filtros))
            .order_by(*self._orden(elegido, filtros))
            .limit(filtros.limite)
            .offset(filtros.offset)
        )
        filas = (await self._session.execute(sentencia)).mappings().all()
        return [self._a_resultado(fila) for fila in filas]

    @staticmethod
    def _coincide_con_el_nombre(consulta: str) -> Any:
        """Condición SQL que encuentra el producto pedido.

        El `icontains` solo encuentra el nombre si la consulta aparece tal
        cual, así que "leche entera Pascual 1L" no encontraba "Leche entera
        Pascual 1 L". Se añade la similitud de trigramas (con el índice GIN
        que hay sobre `productos.nombre`), que ya usa el repositorio de
        productos para resolver el producto canónico.
        """
        literal = ProductoModelo.nombre.icontains(consulta, autoescape=True)
        if len(consulta) < LONGITUD_MINIMA_SIMILITUD:
            # Con poche letras la similitud da falsos positivos ("leche"
            # parecería con "leche de avena"): solo se admite la coincidencia
            # literal.
            return literal
        similitud = func.similarity(ProductoModelo.nombre, consulta)
        return or_(literal, similitud >= UMBRAL_SIMILITUD)

    def _consulta_elegidos(self, filtros: FiltrosComparacion) -> Any:
        """Un precio por producto y cadena, prefiriendo el de la provincia."""
        preferencia = case(
            (
                and_(
                    PrecioModelo.ambito == "provincia",
                    PrecioModelo.provincia == filtros.provincia,
                ),
                0,
            ),
            (PrecioModelo.ambito == "nacional", 1),
            else_=2,
        )
        condiciones = [
            PrecioModelo.estado == "verificado",
            self._coincide_con_el_nombre(filtros.query),
        ]
        if filtros.cadenas:
            condiciones.append(CadenaModelo.slug.in_(filtros.cadenas))
        if filtros.marca:
            condiciones.append(
                func.lower(ProductoModelo.marca) == filtros.marca.lower()
            )
        if filtros.categoria:
            condiciones.append(ProductoModelo.categoria == filtros.categoria)
        if filtros.provincia:
            condiciones.append(
                or_(
                    PrecioModelo.ambito == "nacional",
                    and_(
                        PrecioModelo.ambito == "provincia",
                        PrecioModelo.provincia == filtros.provincia,
                    ),
                )
            )
        else:
            condiciones.append(PrecioModelo.ambito == "nacional")

        return (
            select(
                ProductoModelo.id.label("producto_id"),
                ProductoCadenaModelo.id.label("producto_cadena_id"),
                ProductoModelo.nombre.label("nombre"),
                ProductoModelo.marca.label("marca"),
                ProductoModelo.formato.label("formato"),
                ProductoModelo.categoria.label("categoria"),
                ProductoModelo.ean.label("ean"),
                CadenaModelo.slug.label("cadena"),
                CadenaModelo.id.label("cadena_id"),
                ProductoCadenaModelo.url_producto.label("url_producto"),
                PrecioModelo.precio_eur.label("precio_eur"),
                PrecioModelo.precio_por_litro_kg.label("precio_por_litro_kg"),
                PrecioModelo.ambito.label("ambito"),
                PrecioModelo.provincia.label("provincia"),
                PrecioModelo.disponible.label("disponible"),
            )
            .select_from(ProductoCadenaModelo)
            .join(ProductoModelo, ProductoModelo.id == ProductoCadenaModelo.producto_id)
            .join(CadenaModelo, CadenaModelo.id == ProductoCadenaModelo.cadena_id)
            .join(
                PrecioModelo,
                PrecioModelo.producto_cadena_id == ProductoCadenaModelo.id,
            )
            .where(*condiciones)
            .ext(distinct_on(ProductoCadenaModelo.id))
            .order_by(
                ProductoCadenaModelo.id,
                preferencia,
                PrecioModelo.fecha_consulta.desc(),
            )
        )

    def _filtros_de_precio(
        self, elegido: Any, filtros: FiltrosComparacion
    ) -> list[Any]:
        condiciones: list[Any] = []
        if filtros.precio_min is not None:
            condiciones.append(elegido.c.precio_eur >= filtros.precio_min)
        if filtros.precio_max is not None:
            condiciones.append(elegido.c.precio_eur <= filtros.precio_max)
        if filtros.solo_con_stock:
            condiciones.append(elegido.c.disponible.is_(True))
        return condiciones

    def _orden(self, elegido: Any, filtros: FiltrosComparacion) -> list[Any]:
        if filtros.orden == "precio_kg_l":
            return [
                elegido.c.precio_por_litro_kg.is_(None),
                elegido.c.precio_por_litro_kg,
                elegido.c.nombre,
                elegido.c.cadena,
            ]
        if filtros.orden == "relevancia":
            return [
                func.similarity(elegido.c.nombre, filtros.query).desc(),
                elegido.c.nombre,
                elegido.c.cadena,
            ]
        return [elegido.c.precio_eur, elegido.c.nombre, elegido.c.cadena]

    def _a_resultado(self, fila: Any) -> ResultadoComparacion:
        return ResultadoComparacion(
            producto_id=fila["producto_id"],
            producto_cadena_id=fila["producto_cadena_id"],
            nombre=fila["nombre"],
            cadena=fila["cadena"],
            precio_eur=fila["precio_eur"],
            marca=fila["marca"],
            formato=fila["formato"],
            categoria=fila["categoria"],
            ean=fila["ean"],
            precio_por_litro_kg=fila["precio_por_litro_kg"],
            ambito=cast(AmbitoPrecio, fila["ambito"]),
            provincia=fila["provincia"],
            url_producto=fila["url_producto"],
            disponible=fila["disponible"],
            cadena_id=fila["cadena_id"],
        )

    async def precios_actuales(
        self, producto_id: UUID, provincia: str | None = None
    ) -> list[PrecioVigente]:
        """Un precio vigente por cadena, prefiriendo el de la provincia."""
        condiciones = [
            PrecioModelo.estado == "verificado",
            ProductoCadenaModelo.producto_id == producto_id,
        ]
        if provincia:
            condiciones.append(
                or_(
                    PrecioModelo.ambito == "nacional",
                    and_(
                        PrecioModelo.ambito == "provincia",
                        PrecioModelo.provincia == provincia,
                    ),
                )
            )
        else:
            condiciones.append(PrecioModelo.ambito == "nacional")

        preferencia = case(
            (
                and_(
                    PrecioModelo.ambito == "provincia",
                    PrecioModelo.provincia == provincia,
                ),
                0,
            ),
            (PrecioModelo.ambito == "nacional", 1),
            else_=2,
        )

        filas = (
            (
                await self._session.execute(
                    select(
                        ProductoCadenaModelo.id.label("producto_cadena_id"),
                        CadenaModelo.slug.label("cadena"),
                        CadenaModelo.nombre.label("nombre_cadena"),
                        PrecioModelo.precio_eur.label("precio_eur"),
                        PrecioModelo.precio_por_litro_kg.label("precio_por_litro_kg"),
                        ProductoCadenaModelo.url_producto.label("url_producto"),
                        PrecioModelo.ambito.label("ambito"),
                        PrecioModelo.provincia.label("provincia"),
                        PrecioModelo.disponible.label("disponible"),
                        PrecioModelo.fecha_consulta.label("fecha_consulta"),
                    )
                    .select_from(ProductoCadenaModelo)
                    .join(
                        PrecioModelo,
                        PrecioModelo.producto_cadena_id == ProductoCadenaModelo.id,
                    )
                    .join(
                        CadenaModelo, CadenaModelo.id == ProductoCadenaModelo.cadena_id
                    )
                    .where(*condiciones)
                    .ext(distinct_on(ProductoCadenaModelo.id))
                    .order_by(
                        ProductoCadenaModelo.id,
                        preferencia,
                        PrecioModelo.fecha_consulta.desc(),
                    )
                )
            )
            .mappings()
            .all()
        )

        return [
            PrecioVigente(
                producto_cadena_id=fila["producto_cadena_id"],
                cadena=fila["cadena"],
                nombre_cadena=fila["nombre_cadena"],
                precio_eur=fila["precio_eur"],
                precio_por_litro_kg=fila["precio_por_litro_kg"],
                url_producto=fila["url_producto"],
                ambito=cast(AmbitoPrecio, fila["ambito"]),
                provincia=fila["provincia"],
                disponible=fila["disponible"],
                fecha_consulta=fila["fecha_consulta"],
            )
            for fila in filas
        ]

    async def historico_producto(
        self, producto_id: UUID, desde: datetime | None = None
    ) -> list[HistoricoPrecio]:
        """Histórico de precios verificados del producto, por cadena y fecha."""
        condiciones = [
            PrecioModelo.estado == "verificado",
            ProductoCadenaModelo.producto_id == producto_id,
        ]
        if desde is not None:
            condiciones.append(PrecioModelo.fecha_consulta >= desde)

        filas = (
            (
                await self._session.execute(
                    select(
                        CadenaModelo.slug.label("cadena"),
                        PrecioModelo.fecha_consulta.label("fecha"),
                        PrecioModelo.precio_eur.label("precio_eur"),
                    )
                    .select_from(ProductoCadenaModelo)
                    .join(
                        PrecioModelo,
                        PrecioModelo.producto_cadena_id == ProductoCadenaModelo.id,
                    )
                    .join(
                        CadenaModelo, CadenaModelo.id == ProductoCadenaModelo.cadena_id
                    )
                    .where(*condiciones)
                    .order_by(CadenaModelo.slug, PrecioModelo.fecha_consulta)
                )
            )
            .mappings()
            .all()
        )

        return [
            HistoricoPrecio(
                cadena=fila["cadena"],
                fecha=fila["fecha"],
                precio_eur=fila["precio_eur"],
            )
            for fila in filas
        ]
