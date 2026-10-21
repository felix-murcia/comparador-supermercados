"""Verificador determinista de precios.

Descarga la ficha de producto y aplica las reglas: el precio aparece en el
HTML, el €/L es coherente con el formato y la desviación respecto al último
precio conocido no es excesiva.
"""

from __future__ import annotations

import json
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from src.dominio.precios.reglas import (
    calcular_precio_por_litro,
    desviacion_relativa,
    es_coherente_por_unidad,
)
from src.dominio.productos.reglas import familia_unidad, parsear_formato
from src.puertos.productor import Candidato
from src.puertos.verificador import ResultadoVerificacion

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS = 10.0
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
# Cabeceras de una navegación real: los sitios con protección anti-bot
# responden 403 si la petición no parece un navegador.
CABECERAS_NAVEGADOR = {
    "User-Agent": USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}
TOLERANCIA_UNIDAD = Decimal("0.05")
UMBRAL_DESVIACION = Decimal("0.30")
TOLERANCIA_PRECIO = Decimal("0.005")

MOTIVO_NO_ENCONTRADO = "agente_no_encontrado"
MOTIVO_URL_INVALIDA = "url_invalida"
MOTIVO_FETCH_ERROR = "fetch_error"
MOTIVO_PRECIO_INVALIDO = "precio_invalido"
MOTIVO_PRECIO_AUSENTE = "precio_no_encontrado_en_html"
MOTIVO_UNIDAD_INCOHERENTE = "precio_por_unidad_incoherente"
MOTIVO_DESVIACION = "desviacion_precio"

_PATRON_PRECIO = re.compile(r"(\d+(?:[.,]\d{1,2})?)\s*(?:€|eur\b)", re.IGNORECASE)
_PATRON_PRECIO_UNIDAD = re.compile(
    r"(\d+(?:[.,]\d{1,2})?)\s*€\s*/\s*(l|kg)\b", re.IGNORECASE
)


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


def _precios_con_moneda(html: str) -> list[Decimal]:
    precios: list[Decimal] = []
    for coincidencia in _PATRON_PRECIO.finditer(html):
        valor = _a_decimal(coincidencia.group(1))
        if valor is not None:
            precios.append(valor)
    return precios


def _es_producto(item: dict[str, Any]) -> bool:
    tipo = item.get("@type")
    if isinstance(tipo, list):
        return "Product" in tipo
    return tipo == "Product"


def _ofertas(item: dict[str, Any]) -> list[dict[str, Any]]:
    ofertas = item.get("offers")
    if isinstance(ofertas, dict):
        return [ofertas]
    if isinstance(ofertas, list):
        return [oferta for oferta in ofertas if isinstance(oferta, dict)]
    return []


def _producto_json_ld(html: str) -> dict[str, Any] | None:
    """El producto principal de la página, según sus datos estructurados."""
    for bloque in re.finditer(
        r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>",
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        try:
            datos = json.loads(bloque.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            continue
        for item in datos if isinstance(datos, list) else [datos]:
            if isinstance(item, dict) and _es_producto(item):
                return item
    return None


def _precio_json_ld(html: str) -> Decimal | None:
    """Precio del producto principal de la página, según sus datos JSON-LD.

    La página puede traer varios bloques de producto (relacionados, listas
    de categorías). Se toma el primero, que es el de la propia ficha.
    """
    producto = _producto_json_ld(html)
    if producto is None:
        return None
    for oferta in _ofertas(producto):
        valor = _a_decimal(oferta.get("price"))
        if valor is not None and valor > 0:
            return valor
    return None


def _nombre_json_ld(html: str) -> str | None:
    """Nombre real del producto según la ficha."""
    producto = _producto_json_ld(html)
    if producto is None:
        return None
    nombre = producto.get("name")
    return nombre if isinstance(nombre, str) and nombre.strip() else None


def _precio_por_unidad(html: str) -> tuple[Decimal, str] | None:
    for coincidencia in _PATRON_PRECIO_UNIDAD.finditer(html):
        valor = _a_decimal(coincidencia.group(1))
        if valor is not None:
            return valor, coincidencia.group(2).lower()
    return None


def _contenido_candidato(candidato: Candidato) -> tuple[Decimal | None, str | None]:
    """Contenido en litros/kg y familia de unidad declarados por el candidato."""
    texto_formato = candidato.get("formato")
    formato = parsear_formato(texto_formato if isinstance(texto_formato, str) else None)
    familia = familia_unidad(formato.unidad) if formato else None

    contenido = _a_decimal(candidato.get("litros_o_kg"))
    if contenido is None and formato is not None:
        contenido = formato.a_litros_o_kg()
    return contenido, familia


class FetchVerificador:
    """Verifica el candidato descargando la ficha de producto de la cadena."""

    def __init__(self, cliente_http: httpx.AsyncClient) -> None:
        self._cliente_http = cliente_http

    async def verificar(self, candidato: Candidato) -> ResultadoVerificacion:
        if not candidato.get("encontrado"):
            return ResultadoVerificacion("rechazado", [MOTIVO_NO_ENCONTRADO])

        url = candidato.get("url_fuente")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return ResultadoVerificacion("rechazado", [MOTIVO_URL_INVALIDA])

        precio = _a_decimal(candidato.get("precio_eur"))
        if precio is None or precio <= 0:
            return ResultadoVerificacion("rechazado", [MOTIVO_PRECIO_INVALIDO])

        try:
            respuesta = await self._cliente_http.get(
                url,
                headers=CABECERAS_NAVEGADOR,
                timeout=TIMEOUT_SEGUNDOS,
                follow_redirects=True,
            )
        except httpx.HTTPError as error:
            logger.warning("No se pudo descargar %s: %s", url, type(error).__name__)
            return ResultadoVerificacion("rechazado", [MOTIVO_FETCH_ERROR])

        if respuesta.status_code >= 400:
            logger.warning("La ficha %s respondió HTTP %s", url, respuesta.status_code)
            return ResultadoVerificacion("rechazado", [MOTIVO_FETCH_ERROR])

        html = respuesta.text

        # El precio de la ficha es el de los datos estructurados (JSON-LD),
        # no el que propose el LLM: este ve el resumen de la búsqueda, donde
        # conviven los precios de otros artículos. Si la página no los
        # publica, se recurre a rascar importes del HTML.
        precio_json_ld = _precio_json_ld(html)
        if (
            precio_json_ld is not None
            and abs(precio_json_ld - precio) > TOLERANCIA_PRECIO
        ):
            logger.info(
                "El precio de %s es %s (el LLM propuso %s): se usa el de la página",
                url,
                precio_json_ld,
                precio,
            )
            precio = precio_json_ld

        nombre_json_ld = _nombre_json_ld(html)

        if not self._precio_presente(html, precio):
            logger.warning(
                "La ficha %s no contiene el precio %s (precios en la página: %s)",
                url,
                precio,
                ", ".join(str(p) for p in _precios_con_moneda(html)[:8]) or "ninguno",
            )
            return ResultadoVerificacion("rechazado", [MOTIVO_PRECIO_AUSENTE])

        motivos = self._sospechas(html, candidato, precio)
        if motivos:
            return ResultadoVerificacion("sospechoso", motivos)
        return ResultadoVerificacion("verificado", [], precio, nombre_json_ld)

    def _precio_presente(self, html: str, precio: Decimal) -> bool:
        return any(
            abs(otro - precio) <= TOLERANCIA_PRECIO
            for otro in _precios_con_moneda(html)
        )

    def _sospechas(self, html: str, candidato: Candidato, precio: Decimal) -> list[str]:
        motivos: list[str] = []

        if self._unidad_incoherente(html, candidato, precio):
            motivos.append(MOTIVO_UNIDAD_INCOHERENTE)

        anterior = _a_decimal(candidato.get("precio_eur_anterior"))
        if (
            anterior is not None
            and anterior > 0
            and desviacion_relativa(precio, anterior) > UMBRAL_DESVIACION
        ):
            motivos.append(MOTIVO_DESVIACION)

        return motivos

    def _unidad_incoherente(
        self, html: str, candidato: Candidato, precio: Decimal
    ) -> bool:
        contenido, familia = _contenido_candidato(candidato)
        if contenido is None or contenido <= 0 or familia is None:
            return False

        calculado = calcular_precio_por_litro(precio, contenido)
        if calculado is None:
            return False

        referencia = _precio_por_unidad(html)
        if referencia is None:
            return False

        valor_html, familia_html = referencia
        if familia_html != familia:
            return False

        return not es_coherente_por_unidad(calculado, valor_html, TOLERANCIA_UNIDAD)
