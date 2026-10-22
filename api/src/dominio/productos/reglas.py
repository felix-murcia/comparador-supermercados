"""Reglas puras de formato de producto."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from src.dominio.normalizacion import normalizar_texto
from src.dominio.productos.entidades import DescripcionProducto, Formato

_PATRON_FORMATO = re.compile(r"(\d+(?:[.,]\d+)?)\s*(l|ml|kg|g)\b")

# Espacio entre la cantidad y la unidad: "1 L" y "1L" son el mismo producto.
# Se cubren todas las unidades que usan los retailers (litros, kilos, gramos,
# mililitros, unidades, rollos...). El "x" del multiplicador ("4x120 g") se
# deja aparte: no es una unidad.
_ESPACIO_ANTES_UNIDAD = re.compile(r"(\d)\s+(?!x\b)([a-záéíóúñ]+)\b")

# Multiplicador sin espacio: "4x120 g" y "4 x 120 g" son el mismo formato.
_MULTIPLICADOR = re.compile(r"(\d)\s*x\s*(\d)")

_UNIDADES = {"l": "L", "ml": "ml", "kg": "kg", "g": "g"}


def parsear_formato(texto: str | None) -> Formato | None:
    """Convierte "1L", "500 g" o "1,5 L" en `Formato`; None si no se entiende."""
    if not texto:
        return None

    coincidencia = _PATRON_FORMATO.search(texto.strip().lower())
    if not coincidencia:
        return None

    try:
        cantidad = Decimal(coincidencia.group(1).replace(",", "."))
    except InvalidOperation:
        return None

    return Formato(litros_o_kg=cantidad, unidad=_UNIDADES[coincidencia.group(2)])


def familia_unidad(unidad: str) -> str:
    """Familia de la unidad para comparar precios: "l" (volumen) o "kg" (masa)."""
    return "l" if unidad in ("L", "ml") else "kg"


def normalizar_nombre(texto: str) -> str:
    """Minúsculas, sin tildes y sin espacios repetidos, para comparar nombres.

    Además quita el espacio entre la cantidad y la unidad ("1 L" y "1L" son el
    mismo producto): los retailers escriben la unidad de las dos formas y, sin
    esta normalización, la ingesta crearía dos productos distintos para el
    mismo artículo y el precio se quedaría solo en uno de ellos.

    La base de datos aplica la misma normalización en la función
    `nombre_buscable_normalizado` (migración 0004), que es la que usa la
    búsqueda por texto completo. `test_normalizar_nombre_coincide_con_sql`
    comprueba que las dos coinciden.
    """
    normalizado = normalizar_texto(texto)
    normalizado = _MULTIPLICADOR.sub(r"\1x\2", normalizado)
    return _ESPACIO_ANTES_UNIDAD.sub(r"\1\2", normalizado)


# Tokens que describen la medida del producto, no su identidad. El volumen
# se compara aparte (campo `litros_o_kg`), así que aquí sobran.
_TOKENS_MEDIDA = {"l", "ml", "kg", "g", "gr", "cl", "dl", "x"}

# Medida con cantidad pegada: "1l", "250g", "1,5l". `normalizar_nombre` quita
# el espacio entre la cantidad y la unidad, así que "1 L" acaba siendo "1l".
_MEDIDA_CON_CANTIDAD = re.compile(r"^\d+(?:[.,]\d+)?(l|ml|kg|g|gr|cl|dl)\.?$")


def _tokens_significativos(texto: str) -> set[str]:
    """Palabras con contenido de un nombre, sin medidas ni números sueltos."""
    palabras = normalizar_nombre(texto).split()
    return {
        palabra
        for palabra in palabras
        if palabra not in _TOKENS_MEDIDA
        and not palabra.isdigit()
        and not _MEDIDA_CON_CANTIDAD.match(palabra)
    }


def _quitar_marca(nombre: str, marca: str | None) -> str:
    """Elimina la marca del nombre, aunque el orden de las palabras varíe."""
    if not marca:
        return nombre
    objetivo = normalizar_nombre(marca)
    if not objetivo:
        return nombre
    palabras = normalizar_nombre(nombre).split()
    objetivo_palabras = objetivo.split()
    if len(objetivo_palabras) == 1:
        return " ".join(p for p in palabras if p != objetivo_palabras[0])
    # Marca de varias palabras: se busca la secuencia completa.
    for largo in range(len(objetivo_palabras), 0, -1):
        for inicio in range(len(palabras) - largo + 1):
            if palabras[inicio : inicio + largo] == objetivo_palabras[:largo]:
                resto = palabras[:inicio] + palabras[inicio + largo :]
                return " ".join(resto)
    return normalizar_nombre(nombre)


def descripcion_base(nombre: str, marca: str | None = None) -> str:
    """Descripción del producto sin la marca, para saber si dos son el mismo.

    Un producto de DIA («Leche desnatada Dia Láctea 1 L») y el equivalente de
    otra cadena («Leche desnatada brik 1 l.», marca SIMPL) describen la misma
    necesidad de compra aunque no compartan nombre. Quitando la marca y las
    medidas queda la descripción common: «leche desnatada» y «leche desnatada
    brik».

    La marca se busca también dentro del nombre porque el retailer la escribe
    como parte del título, no siempre en un campo aparte.
    """
    sin_marca = _quitar_marca(nombre, marca)
    return " ".join(sorted(_tokens_significativos(sin_marca)))


def similitud_base(primera: str, segunda: str) -> float:
    """Jaccard sobre los tokens de dos descripciones base (0 a 1).

    Jaccard y no similitud de cadenas porque el orden de las palabras varía
    entre cadenas: «Leche desnatada brik» y «Leche desnatada» son la misma
    necesidad, pero «Leche desnatada» y «Leche semidesnatada» no, aunque las
    cadenas se parezcan mucho.
    """
    tokens_primera = set(primera.split())
    tokens_segunda = set(segunda.split())
    if not tokens_primera or not tokens_segunda:
        return 0.0
    interseccion = len(tokens_primera & tokens_segunda)
    union = len(tokens_primera | tokens_segunda)
    return interseccion / union


def _formato_legible(texto: str) -> str:
    """Muestra las medidas con espacio: "1l" → "1 l", "1 l." → "1 L"."""
    normalizado = normalizar_nombre(texto).replace(".", "")
    return re.sub(r"(\d+(?:[.,]\d+)?)([a-z]+)", r"\1 \2", normalizado)


def nombre_generico(
    nombre: str, marca: str | None = None, formato: str | None = None
) -> str:
    """Nombre del producto sin la marca, con el formato, para los avisos.

    «Leche desnatada Dia Láctea 1 L» (marca «Dia Láctea») se muestra como
    «Leche desnatada 1 L»: es la necesidad de compra, no el artículo concreto
    de una marca, que es lo que se compara entre cadenas.
    """
    sin_marca = _quitar_marca(nombre, marca).strip()
    if not sin_marca:
        sin_marca = normalizar_nombre(nombre)
    if not formato:
        return _formato_legible(sin_marca)
    formato_normalizado = normalizar_nombre(formato)
    if not formato_normalizado:
        return _formato_legible(sin_marca)
    if formato_normalizado in sin_marca:
        return _formato_legible(sin_marca)
    return f"{_formato_legible(sin_marca)} {_formato_legible(formato)}"


# Dos descripciones son equivalentes si comparten al menos estas palabras.
# «leche desnatada» y «leche desnatada brik» (0,67) sí; «leche desnatada» y
# «leche semidesnatada» (0,33) no.
UMBRAL_EQUIVALENCIA = 0.6

# Tolerancia al comparar el tamaño: 1 L y 1,0 L son el mismo producto.
_TOLERANCIA_VOLUMEN = Decimal("0.001")


def _mismo_volumen(primero: Decimal | None, segundo: Decimal | None) -> bool:
    """Dos volúmenes son el mismo si ambos faltan o coinciden."""
    if primero is None or segundo is None:
        return primero is None and segundo is None
    return abs(primero - segundo) <= _TOLERANCIA_VOLUMEN


def es_equivalente(
    primero: DescripcionProducto,
    segundo: DescripcionProducto,
    *,
    umbral: float = UMBRAL_EQUIVALENCIA,
) -> bool:
    """Si dos productos de cadenas distintas cubren la misma necesidad.

    Se exige que coincidan la categoría y el tamaño, y que las descripciones
    base (sin marca) se parezcan. Sin el requisito de tamaño, «Leche
    desnatada 1 L» sería equivalente a «Leche desnatada 3 L», y el cálculo de
    ahorro de la lista compararía precios de cosas distintas.
    """
    if (
        primero.categoria
        and segundo.categoria
        and primero.categoria != segundo.categoria
    ):
        return False
    if not _mismo_volumen(primero.litros_o_kg, segundo.litros_o_kg):
        return False

    base_primero = descripcion_base(primero.nombre, primero.marca)
    base_segundo = descripcion_base(segundo.nombre, segundo.marca)
    if not base_primero or not base_segundo:
        return False
    return similitud_base(base_primero, base_segundo) >= umbral
