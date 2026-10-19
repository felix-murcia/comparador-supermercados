"""Conversión de modelos SQLAlchemy a entidades de dominio."""

from __future__ import annotations

from typing import cast

from src.adaptadores.persistencia.modelos import (
    BusquedaModelo,
    ItemListaModelo,
    ListaModelo,
    PrecioModelo,
    ProductoModelo,
)
from src.dominio.busquedas.entidades import Busqueda
from src.dominio.busquedas.estados import EstadoBusqueda
from src.dominio.listas.entidades import ItemLista, Lista
from src.dominio.precios.entidades import PrecioRegistrado
from src.dominio.precios.estados import AmbitoPrecio, EstadoPrecio
from src.dominio.productos.entidades import Producto


def producto_desde_modelo(modelo: ProductoModelo) -> Producto:
    return Producto(
        id=modelo.id,
        nombre=modelo.nombre,
        marca=modelo.marca,
        categoria=modelo.categoria,
        formato=modelo.formato,
        litros_o_kg=modelo.litros_o_kg,
        ean=modelo.ean,
        creado_en=modelo.creado_en,
    )


def precio_desde_modelo(modelo: PrecioModelo) -> PrecioRegistrado:
    return PrecioRegistrado(
        id=modelo.id,
        producto_cadena_id=modelo.producto_cadena_id,
        importe_eur=modelo.precio_eur,
        por_litro_kg=modelo.precio_por_litro_kg,
        disponible=modelo.disponible,
        promocion=modelo.promocion,
        ambito=cast(AmbitoPrecio, modelo.ambito),
        provincia=modelo.provincia,
        estado=cast(EstadoPrecio, modelo.estado),
        url_fuente=modelo.url_fuente,
        fecha_consulta=modelo.fecha_consulta,
        creado_en=modelo.creado_en,
    )


def lista_desde_modelo(modelo: ListaModelo) -> Lista:
    return Lista(
        id=modelo.id,
        nombre=modelo.nombre,
        creado_en=modelo.creado_en,
        usuario_id=modelo.usuario_id,
    )


def item_lista_desde_modelo(modelo: ItemListaModelo) -> ItemLista:
    return ItemLista(
        id=modelo.id,
        lista_id=modelo.lista_id,
        producto_id=modelo.producto_id,
        cantidad=modelo.cantidad,
        creado_en=modelo.creado_en,
        cadena_compra_id=modelo.cadena_compra_id,
        precio_snapshot=modelo.precio_snapshot,
    )


def busqueda_desde_modelo(modelo: BusquedaModelo) -> Busqueda:
    return Busqueda(
        id=modelo.id,
        query=modelo.query,
        cadenas=tuple(modelo.cadenas),
        estado=cast(EstadoBusqueda, modelo.estado),
        progreso=modelo.progreso,
        cache_key=modelo.cache_key,
        creado_en=modelo.creado_en,
        usuario_id=modelo.usuario_id,
        provincia=modelo.provincia,
        completado_en=modelo.completado_en,
    )
