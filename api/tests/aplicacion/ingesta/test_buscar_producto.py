"""Tests del caso de uso `BuscarProducto` con dobles de los puertos."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest

from src.aplicacion.ingesta.buscar_producto import (
    MOTIVO_AGENTE_NO_ENCONTRO,
    MOTIVO_CADENA_DESCONOCIDA,
    BuscarProducto,
)
from src.dominio.cadenas.entidades import Cadena
from src.dominio.precios.entidades import (
    FiltrosComparacion,
    HistoricoPrecio,
    PrecioNuevo,
    PrecioRegistrado,
    PrecioVigente,
    ResultadoComparacion,
)
from src.dominio.precios.errores import ErrorProductor
from src.dominio.productos.entidades import Producto, ProductoIngestable, ProductoNuevo
from src.puertos.productor import Candidato
from src.puertos.verificador import ResultadoVerificacion

CANDIDATO: Candidato = {
    "encontrado": True,
    "nombre": "Leche entera",
    "marca": "Pascual",
    "categoria": "lacteos",
    "formato": "1L",
    "litros_o_kg": 1.0,
    "ean": "8412345678901",
    "precio_eur": 1.29,
    "url_fuente": "https://www.dia.test/leche-entera",
    "nombre_en_cadena": "Leche entera Pascual 1L",
    "confianza": 0.9,
}


class ProductorFake:
    def __init__(self, respuestas: list[Any]) -> None:
        self.respuestas = list(respuestas)
        self.llamadas: list[tuple[str, str]] = []

    async def producir(self, query: str, cadena: str) -> Candidato:
        self.llamadas.append((query, cadena))
        siguiente = self.respuestas.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


class VerificadorFake:
    def __init__(self, resultados: list[ResultadoVerificacion]) -> None:
        self.resultados = list(resultados)
        self.candidatos: list[Candidato] = []

    async def verificar(self, candidato: Candidato) -> ResultadoVerificacion:
        self.candidatos.append(candidato)
        if not self.resultados:
            return "rechazado", ["sin_resultados"]
        return self.resultados.pop(0)


class CadenasFake:
    def __init__(self, cadenas: dict[str, Cadena]) -> None:
        self.cadenas = cadenas

    async def obtener_por_slug(self, slug: str) -> Cadena | None:
        return self.cadenas.get(slug)

    async def obtener_por_id(self, cadena_id: UUID) -> Cadena | None:
        return next(
            (cadena for cadena in self.cadenas.values() if cadena.id == cadena_id),
            None,
        )


class ProductosFake:
    def __init__(self) -> None:
        self.creados: list[ProductoNuevo] = []
        self.por_ean: dict[str, Producto] = {}
        self.por_nombre: list[Producto] = []

    async def obtener(self, producto_id: UUID) -> Producto | None:
        return None

    async def obtener_por_ean(self, ean: str) -> Producto | None:
        return self.por_ean.get(ean)

    async def buscar_por_nombre(
        self, consulta: str, limite: int = 20
    ) -> list[Producto]:
        return self.por_nombre

    async def crear(self, datos: ProductoNuevo) -> Producto:
        self.creados.append(datos)
        return Producto(
            id=uuid4(),
            nombre=datos.nombre,
            marca=datos.marca,
            categoria=datos.categoria,
            formato=datos.formato,
            litros_o_kg=datos.litros_o_kg,
            ean=datos.ean,
            creado_en=datetime.now(UTC),
        )

    async def listar_ingestables(self) -> list[ProductoIngestable]:
        return []

    async def obtener_por_slug(self, slug: str) -> Producto | None:
        return None


class ProductosCadenasFake:
    def __init__(self) -> None:
        self.existentes: dict[tuple[UUID, UUID], UUID] = {}
        self.creados: list[tuple[UUID, UUID, str, str]] = []

    async def obtener_por_producto_y_cadena(
        self, producto_id: UUID, cadena_id: UUID
    ) -> UUID | None:
        return self.existentes.get((producto_id, cadena_id))

    async def crear(
        self,
        producto_id: UUID,
        cadena_id: UUID,
        url_producto: str,
        nombre_en_cadena: str,
    ) -> UUID:
        self.creados.append((producto_id, cadena_id, url_producto, nombre_en_cadena))
        return uuid4()


class PreciosFake:
    def __init__(self) -> None:
        self.insertados: list[PrecioNuevo] = []
        self.anterior: PrecioRegistrado | None = None

    async def insertar(self, datos: PrecioNuevo) -> PrecioRegistrado:
        self.insertados.append(datos)
        return PrecioRegistrado(
            id=uuid4(),
            producto_cadena_id=datos.producto_cadena_id,
            importe_eur=datos.importe_eur,
            por_litro_kg=datos.por_litro_kg,
            disponible=datos.disponible,
            promocion=datos.promocion,
            ambito=datos.ambito,
            provincia=datos.provincia,
            estado=datos.estado,
            url_fuente=datos.url_fuente,
            fecha_consulta=datos.fecha_consulta,
            creado_en=datetime.now(UTC),
        )

    async def ultimo_verificado(
        self, producto_cadena_id: UUID
    ) -> PrecioRegistrado | None:
        return self.anterior

    async def historico(
        self, producto_cadena_id: UUID, limite: int = 10
    ) -> list[PrecioRegistrado]:
        return []

    async def buscar_comparativa(
        self, filtros: FiltrosComparacion
    ) -> list[ResultadoComparacion]:
        return []

    async def precios_actuales(
        self, producto_id: UUID, provincia: str | None = None
    ) -> list[PrecioVigente]:
        return []

    async def historico_producto(
        self, producto_id: UUID, desde: datetime | None = None
    ) -> list[HistoricoPrecio]:
        return []


def _cadena() -> Cadena:
    return Cadena(id=uuid4(), slug="dia", nombre="DIA", logo_svg="<svg></svg>")


def _caso(
    productor: ProductorFake,
    verificador: VerificadorFake,
    cadenas: CadenasFake,
    productos: ProductosFake,
    productos_cadenas: ProductosCadenasFake,
    precios: PreciosFake,
) -> BuscarProducto:
    return BuscarProducto(
        productor=productor,
        verificador=verificador,
        repositorio_cadenas=cadenas,
        repositorio_productos=productos,
        repositorio_productos_cadenas=productos_cadenas,
        repositorio_precios=precios,
    )


@pytest.mark.asyncio
async def test_guarda_el_precio_verificado_y_devuelve_exito() -> None:
    productor = ProductorFake([CANDIDATO])
    verificador = VerificadorFake([("verificado", [])])
    precios = PreciosFake()
    caso = _caso(
        productor,
        verificador,
        CadenasFake({"dia": _cadena()}),
        ProductosFake(),
        ProductosCadenasFake(),
        precios,
    )

    resultado = await caso.ejecutar("leche entera", "dia")

    assert resultado.estado == "verificado"
    assert resultado.guardado is True
    assert len(precios.insertados) == 1
    assert precios.insertados[0].estado == "verificado"
    assert precios.insertados[0].importe_eur == Decimal("1.29")
    assert precios.insertados[0].por_litro_kg == Decimal("1.2900")
    assert precios.insertados[0].url_fuente == "https://www.dia.test/leche-entera"


@pytest.mark.asyncio
async def test_no_reintenta_si_el_agente_no_encontro_el_producto() -> None:
    productor = ProductorFake(
        [{"encontrado": False, "motivo_si_no_encontrado": "agente_no_encontro"}]
    )
    verificador = VerificadorFake([])
    precios = PreciosFake()
    caso = _caso(
        productor,
        verificador,
        CadenasFake({"dia": _cadena()}),
        ProductosFake(),
        ProductosCadenasFake(),
        precios,
    )

    resultado = await caso.ejecutar("quinoa", "dia")

    assert resultado.estado == "rechazado"
    assert resultado.guardado is False
    assert MOTIVO_AGENTE_NO_ENCONTRO in resultado.motivos
    assert len(productor.llamadas) == 1
    assert verificador.candidatos == []
    assert precios.insertados == []


@pytest.mark.asyncio
async def test_hasta_tres_pasadas_y_guarda_el_precio_sospechoso() -> None:
    productor = ProductorFake([CANDIDATO, CANDIDATO, CANDIDATO])
    verificador = VerificadorFake([("sospechoso", ["desviacion_precio"])] * 3)
    precios = PreciosFake()
    caso = _caso(
        productor,
        verificador,
        CadenasFake({"dia": _cadena()}),
        ProductosFake(),
        ProductosCadenasFake(),
        precios,
    )

    resultado = await caso.ejecutar("leche entera", "dia")

    assert resultado.estado == "sospechoso"
    assert resultado.guardado is True
    assert len(productor.llamadas) == 3
    assert len(precios.insertados) == 1
    assert precios.insertados[0].estado == "sospechoso"


@pytest.mark.asyncio
async def test_no_guarda_nada_si_el_verificador_rechaza() -> None:
    productor = ProductorFake([CANDIDATO, CANDIDATO, CANDIDATO])
    verificador = VerificadorFake([("rechazado", ["precio_no_encontrado_en_html"])] * 3)
    precios = PreciosFake()
    caso = _caso(
        productor,
        verificador,
        CadenasFake({"dia": _cadena()}),
        ProductosFake(),
        ProductosCadenasFake(),
        precios,
    )

    resultado = await caso.ejecutar("leche entera", "dia")

    assert resultado.estado == "rechazado"
    assert resultado.guardado is False
    assert precios.insertados == []
    assert len(productor.llamadas) == 3


@pytest.mark.asyncio
async def test_pasa_el_ultimo_precio_conocido_al_verificador() -> None:
    productor = ProductorFake([CANDIDATO])
    verificador = VerificadorFake([("verificado", [])])
    precios = PreciosFake()
    precios.anterior = PrecioRegistrado(
        id=uuid4(),
        producto_cadena_id=uuid4(),
        importe_eur=Decimal("1.25"),
        por_litro_kg=Decimal("1.25"),
        disponible=True,
        promocion=None,
        ambito="nacional",
        provincia=None,
        estado="verificado",
        url_fuente="https://www.dia.test/leche-entera",
        fecha_consulta=datetime.now(UTC),
        creado_en=datetime.now(UTC),
    )
    caso = _caso(
        productor,
        verificador,
        CadenasFake({"dia": _cadena()}),
        ProductosFake(),
        ProductosCadenasFake(),
        precios,
    )

    await caso.ejecutar("leche entera", "dia")

    assert verificador.candidatos[0]["precio_eur_anterior"] == Decimal("1.25")


@pytest.mark.asyncio
async def test_crea_el_producto_cuando_no_existe() -> None:
    productor = ProductorFake([CANDIDATO])
    verificador = VerificadorFake([("verificado", [])])
    productos = ProductosFake()
    productos_cadenas = ProductosCadenasFake()
    caso = _caso(
        productor,
        verificador,
        CadenasFake({"dia": _cadena()}),
        productos,
        productos_cadenas,
        PreciosFake(),
    )

    await caso.ejecutar("leche entera", "dia")

    assert len(productos.creados) == 1
    assert productos.creados[0].nombre == "Leche entera"
    assert productos.creados[0].ean == "8412345678901"
    assert len(productos_cadenas.creados) == 1
    assert productos_cadenas.creados[0][2] == "https://www.dia.test/leche-entera"


@pytest.mark.asyncio
async def test_reutiliza_el_producto_que_ya_existe_por_ean() -> None:
    productor = ProductorFake([CANDIDATO])
    verificador = VerificadorFake([("verificado", [])])
    productos = ProductosFake()
    producto = Producto(
        id=uuid4(),
        nombre="Leche entera",
        marca="Pascual",
        categoria="lacteos",
        formato="1L",
        litros_o_kg=Decimal(1),
        ean="8412345678901",
        creado_en=datetime.now(UTC),
    )
    productos.por_ean["8412345678901"] = producto
    productos_cadenas = ProductosCadenasFake()
    caso = _caso(
        productor,
        verificador,
        CadenasFake({"dia": _cadena()}),
        productos,
        productos_cadenas,
        PreciosFake(),
    )

    await caso.ejecutar("leche entera", "dia")

    assert productos.creados == []
    assert len(productos_cadenas.creados) == 1
    assert productos_cadenas.creados[0][0] == producto.id


@pytest.mark.asyncio
async def test_devuelve_fallo_si_la_cadena_no_existe() -> None:
    productor = ProductorFake([CANDIDATO])
    caso = _caso(
        productor,
        VerificadorFake([]),
        CadenasFake({}),
        ProductosFake(),
        ProductosCadenasFake(),
        PreciosFake(),
    )

    resultado = await caso.ejecutar("leche entera", "desconocida")

    assert resultado.estado == "rechazado"
    assert resultado.motivos == (MOTIVO_CADENA_DESCONOCIDA,)
    assert productor.llamadas == []


@pytest.mark.asyncio
async def test_no_reintenta_un_error_no_reintentable_del_productor() -> None:
    productor = ProductorFake([ErrorProductor("el LLM no devolvió JSON válido")])
    caso = _caso(
        productor,
        VerificadorFake([]),
        CadenasFake({"dia": _cadena()}),
        ProductosFake(),
        ProductosCadenasFake(),
        PreciosFake(),
    )

    resultado = await caso.ejecutar("leche entera", "dia")

    assert resultado.estado == "rechazado"
    assert len(productor.llamadas) == 1


@pytest.mark.asyncio
async def test_reintenta_un_error_reintentable_del_productor() -> None:
    productor = ProductorFake(
        [
            ErrorProductor("HTTP 503", reintentable=True),
            CANDIDATO,
        ]
    )
    verificador = VerificadorFake([("verificado", [])])
    precios = PreciosFake()
    caso = _caso(
        productor,
        verificador,
        CadenasFake({"dia": _cadena()}),
        ProductosFake(),
        ProductosCadenasFake(),
        precios,
    )

    resultado = await caso.ejecutar("leche entera", "dia")

    assert resultado.estado == "verificado"
    assert len(productor.llamadas) == 2
    assert len(precios.insertados) == 1
