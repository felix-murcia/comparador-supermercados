"""Seed idempotente de desarrollo.

Uso:
    python -m scripts.seed

Inserta 3 cadenas, 100 productos, sus mapeos y un precio verificado nacional
por producto/cadena. Los ids son deterministas (uuid5) y los INSERT usan
`ON CONFLICT DO NOTHING`, así que ejecutarlo varias veces no duplica filas.
"""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import FromClause, Table, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scripts.datos_seed import CADENAS, PRODUCTOS
from src.adaptadores.persistencia.engines import dispose_engines, get_engine_rw
from src.adaptadores.persistencia.modelos import (
    CadenaModelo,
    PrecioModelo,
    ProductoCadenaModelo,
    ProductoModelo,
)
from src.config import settings
from src.dominio.precios.reglas import calcular_precio_por_litro

logger = logging.getLogger(__name__)

_ESPACIO_IDS = uuid5(NAMESPACE_URL, "https://comparador-precios.local/seed")

_DOMINIOS = {
    "dia": "https://www.dia.es/producto",
    "carrefour": "https://www.carrefour.es/supermercado",
    "mercadona": "https://tienda.mercadona.es/producto",
}


def _id(tipo: str, clave: str) -> UUID:
    return uuid5(_ESPACIO_IDS, f"{tipo}:{clave}")


def _slug(texto: str) -> str:
    sin_acentos = "".join(
        caracter
        for caracter in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caracter)
    )
    return re.sub(r"[^a-z0-9]+", "-", sin_acentos.lower()).strip("-")


def _url_producto(slug_cadena: str, slug_producto: str) -> str:
    return f"{_DOMINIOS[slug_cadena]}/{slug_producto}"


async def _insertar_si_falta(
    sesion: AsyncSession, tabla: FromClause, filas: list[dict[str, Any]]
) -> None:
    if filas:
        await sesion.execute(insert(cast(Table, tabla)).on_conflict_do_nothing(), filas)


async def _contar(sesion: AsyncSession) -> dict[str, int]:
    tablas = {
        "cadenas": CadenaModelo.__table__,
        "productos": ProductoModelo.__table__,
        "productos_cadena": ProductoCadenaModelo.__table__,
        "precios": PrecioModelo.__table__,
    }
    totales: dict[str, int] = {}
    for nombre, tabla in tablas.items():
        total = await sesion.scalar(select(func.count()).select_from(tabla))
        totales[nombre] = int(total or 0)
    return totales


async def ejecutar_seed(sesion: AsyncSession) -> None:
    fecha = datetime.now(UTC)

    filas_cadenas: list[dict[str, Any]] = []
    filas_productos: list[dict[str, Any]] = []
    filas_productos_cadena: list[dict[str, Any]] = []
    filas_precios: list[dict[str, Any]] = []

    for cadena in CADENAS:
        filas_cadenas.append(
            {
                "id": _id("cadena", cadena.slug),
                "slug": cadena.slug,
                "nombre": cadena.nombre,
                "logo_svg": cadena.logo_svg,
            }
        )

    for producto in PRODUCTOS:
        id_producto = _id("producto", producto.nombre)
        slug_producto = _slug(producto.nombre)
        filas_productos.append(
            {
                "id": id_producto,
                "nombre": producto.nombre,
                "marca": producto.marca,
                "categoria": producto.categoria,
                "formato": producto.formato,
                "litros_o_kg": producto.litros_o_kg,
                "ean": None,
            }
        )
        for cadena in CADENAS:
            id_producto_cadena = _id(
                "producto_cadena", f"{producto.nombre}:{cadena.slug}"
            )
            url = _url_producto(cadena.slug, slug_producto)
            precio_eur = (producto.precio_eur * cadena.factor_precio).quantize(
                Decimal("0.01")
            )
            filas_productos_cadena.append(
                {
                    "id": id_producto_cadena,
                    "producto_id": id_producto,
                    "cadena_id": _id("cadena", cadena.slug),
                    "url_producto": url,
                    "nombre_en_cadena": f"{producto.nombre} {producto.marca}",
                }
            )
            filas_precios.append(
                {
                    "id": _id("precio", f"{producto.nombre}:{cadena.slug}"),
                    "producto_cadena_id": id_producto_cadena,
                    "precio_eur": precio_eur,
                    "precio_por_litro_kg": calcular_precio_por_litro(
                        precio_eur, producto.litros_o_kg
                    ),
                    "disponible": True,
                    "promocion": None,
                    "ambito": "nacional",
                    "provincia": None,
                    "estado": "verificado",
                    "url_fuente": url,
                    "fecha_consulta": fecha,
                }
            )

    for tabla, filas in (
        (CadenaModelo.__table__, filas_cadenas),
        (ProductoModelo.__table__, filas_productos),
        (ProductoCadenaModelo.__table__, filas_productos_cadena),
        (PrecioModelo.__table__, filas_precios),
    ):
        await _insertar_si_falta(sesion, tabla, filas)


async def main() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(levelname)s %(name)s %(message)s",
    )
    if settings.app_env == "prod":
        raise SystemExit("El seed solo puede ejecutarse con APP_ENV=dev")

    motor = get_engine_rw()
    fabrica = async_sessionmaker(motor, expire_on_commit=False)
    try:
        async with fabrica() as sesion:
            antes = await _contar(sesion)
            await ejecutar_seed(sesion)
            await sesion.commit()
            despues = await _contar(sesion)
    finally:
        await dispose_engines()

    logger.info("Seed completado: %s -> %s", antes, despues)


if __name__ == "__main__":
    asyncio.run(main())
