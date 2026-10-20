"""Verificador determinista de precios.

Descarga la ficha de producto y aplica las reglas: el precio aparece en el
HTML, el €/L es coherente con el formato y la desviación respecto al último
precio conocido no es excesiva.
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation

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
            return "rechazado", [MOTIVO_NO_ENCONTRADO]

        url = candidato.get("url_fuente")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return "rechazado", [MOTIVO_URL_INVALIDA]

        precio = _a_decimal(candidato.get("precio_eur"))
        if precio is None or precio <= 0:
            return "rechazado", [MOTIVO_PRECIO_INVALIDO]

        try:
            respuesta = await self._cliente_http.get(
                url,
                headers=CABECERAS_NAVEGADOR,
                timeout=TIMEOUT_SEGUNDOS,
                follow_redirects=True,
            )
        except httpx.HTTPError as error:
            logger.warning("No se pudo descargar %s: %s", url, type(error).__name__)
            return "rechazado", [MOTIVO_FETCH_ERROR]

        if respuesta.status_code >= 400:
            logger.warning("La ficha %s respondió HTTP %s", url, respuesta.status_code)
            return "rechazado", [MOTIVO_FETCH_ERROR]

        html = respuesta.text
        if not self._precio_presente(html, precio):
            return "rechazado", [MOTIVO_PRECIO_AUSENTE]

        motivos = self._sospechas(html, candidato, precio)
        if motivos:
            return "sospechoso", motivos
        return "verificado", []

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
