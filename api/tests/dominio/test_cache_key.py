"""Tests de la clave de caché de búsquedas."""

from __future__ import annotations

from src.dominio.busquedas.reglas import PREFIJO_CACHE, calcular_cache_key


def test_la_clave_lleva_el_prefijo_de_version() -> None:
    clave = calcular_cache_key("leche", ["dia"])

    assert clave.startswith(PREFIJO_CACHE)
    assert len(clave) == len(PREFIJO_CACHE) + 64


def test_la_misma_busqueda_da_la_misma_clave() -> None:
    primera = calcular_cache_key("leche", ["dia", "carrefour"])
    segunda = calcular_cache_key("leche", ["dia", "carrefour"])

    assert primera == segunda


def test_normaliza_la_query() -> None:
    con_tildes = calcular_cache_key("Leche  Entera", ["dia"])
    sin_tildes = calcular_cache_key("leche entera", ["dia"])

    assert con_tildes == sin_tildes


def test_normaliza_tildes_en_la_query() -> None:
    con_tildes = calcular_cache_key("jamón de york", ["dia"])
    sin_tildes = calcular_cache_key("jamon de york", ["dia"])

    assert con_tildes == sin_tildes


def test_ordena_las_cadenas_alfabeticamente() -> None:
    primero = calcular_cache_key("leche", ["mercadona", "dia"])
    segundo = calcular_cache_key("leche", ["dia", "mercadona"])

    assert primero == segundo


def test_distinta_provincia_da_distinta_clave() -> None:
    nacional = calcular_cache_key("leche", ["dia"], provincia=None)
    madrid = calcular_cache_key("leche", ["dia"], provincia="Madrid")
    barcelona = calcular_cache_key("leche", ["dia"], provincia="Barcelona")

    assert nacional != madrid
    assert madrid != barcelona


def test_distinto_orden_da_distinta_clave() -> None:
    precio = calcular_cache_key("leche", ["dia"], orden="precio")
    relevancia = calcular_cache_key("leche", ["dia"], orden="relevancia")

    assert precio != relevancia


def test_los_filtros_se_serializan_de_forma_canonica() -> None:
    primero = calcular_cache_key(
        "leche", ["dia"], filtros={"marca": "Pascual", "categoria": "lacteos"}
    )
    segundo = calcular_cache_key(
        "leche", ["dia"], filtros={"categoria": "lacteos", "marca": "pascual"}
    )

    assert primero == segundo


def test_distinto_filtro_da_distinta_clave() -> None:
    con_marca = calcular_cache_key("leche", ["dia"], filtros={"marca": "Pascual"})
    con_categoria = calcular_cache_key(
        "leche", ["dia"], filtros={"categoria": "lacteos"}
    )

    assert con_marca != con_categoria


def test_los_filtros_vacios_no_cambian_la_clave() -> None:
    sin_filtros = calcular_cache_key("leche", ["dia"])
    con_filtros_vacios = calcular_cache_key(
        "leche", ["dia"], filtros={"marca": "", "categoria": None}
    )

    assert sin_filtros == con_filtros_vacios


def test_distinta_query_da_distinta_clave() -> None:
    leche = calcular_cache_key("leche", ["dia"])
    avena = calcular_cache_key("avena", ["dia"])

    assert leche != avena
