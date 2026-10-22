"""Reglas puras de las listas de la compra."""

from __future__ import annotations

# Grupo de claves de la caché donde viven los resúmenes de las listas.
#
# Va en su propio grupo (y no bajo `v1:`) porque un resumen depende de los
# items de la lista: al añadir, cambiar o quitar un producto hay que
# invalidarlo, y no tiene sentido tirar también la caché de búsquedas, que
# es la cara de recalcular. La ingesta diaria invalida el grupo entero,
# porque los precios cambian.
PREFIJO_RESUMEN = "resumen"
