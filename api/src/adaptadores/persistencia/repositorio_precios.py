"""Implementación SQLAlchemy de `RepositorioPrecios` (append-only)."""

from __future__ import annotations

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
    PrecioNuevo,
    PrecioRegistrado,
    ResultadoComparacion,
)
from src.dominio.precios.estados import AmbitoPrecio


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
            ProductoModelo.nombre.icontains(filtros.query, autoescape=True),
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
        )
