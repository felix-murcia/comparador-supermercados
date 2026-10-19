"""Catálogo de muestra para el seed de desarrollo.

Los precios son la base de DIA; cada cadena aplica su factor en `seed.py`.
`litros_o_kg` va normalizado (0,5 kg para 500 g; 1,5 para 1,5 L).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CadenaSeed:
    slug: str
    nombre: str
    logo_svg: str
    factor_precio: Decimal


@dataclass(frozen=True)
class ProductoSeed:
    nombre: str
    marca: str
    categoria: str
    formato: str
    litros_o_kg: Decimal
    precio_eur: Decimal


_LOGO_DIA = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
    '<rect width="48" height="48" rx="10" fill="#e30613"/>'
    '<text x="24" y="31" text-anchor="middle" font-family="Arial" '
    'font-size="17" font-weight="bold" fill="#ffffff">DIA</text>'
    "</svg>"
)

_LOGO_CARREFOUR = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
    '<rect width="48" height="48" rx="10" fill="#004e9f"/>'
    '<path d="M24 10 38 24 24 38 10 24Z" fill="#ffffff"/>'
    '<path d="M24 18 30 24 24 30 18 24Z" fill="#e30613"/>'
    "</svg>"
)

_LOGO_MERCADONA = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">'
    '<circle cx="24" cy="24" r="22" fill="#00913f"/>'
    '<text x="24" y="31" text-anchor="middle" font-family="Arial" '
    'font-size="18" font-weight="bold" fill="#ffffff">M</text>'
    "</svg>"
)

CADENAS: tuple[CadenaSeed, ...] = (
    CadenaSeed("dia", "DIA", _LOGO_DIA, Decimal("1.00")),
    CadenaSeed("carrefour", "Carrefour", _LOGO_CARREFOUR, Decimal("1.05")),
    CadenaSeed("mercadona", "Mercadona", _LOGO_MERCADONA, Decimal("1.02")),
)

# (nombre, marca, categoría, formato, litros_o_kg, precio base en DIA)
_PRODUCTOS_CRUDOS: tuple[tuple[str, str, str, str, str, str], ...] = (
    # Lácteos
    ("Leche entera", "Pascual", "lacteos", "1 L", "1", "1.19"),
    ("Leche semidesnatada", "Central Lechera Asturiana", "lacteos", "1 L", "1", "1.15"),
    ("Leche desnatada", "Puleva", "lacteos", "1 L", "1", "1.12"),
    ("Yogur natural", "Danone", "lacteos", "4x125 g", "0.5", "2.19"),
    ("Yogur griego", "Fage", "lacteos", "500 g", "0.5", "2.49"),
    ("Queso curado", "García Baquero", "lacteos", "250 g", "0.25", "3.99"),
    ("Queso fresco", "Burgos", "lacteos", "250 g", "0.25", "1.79"),
    ("Mantequilla", "Flora", "lacteos", "250 g", "0.25", "2.29"),
    ("Nata líquida", "Pascual", "lacteos", "200 ml", "0.2", "1.09"),
    ("Kéfir natural", "Kaiku", "lacteos", "500 ml", "0.5", "2.09"),
    # Bebidas
    ("Agua mineral", "Bezoya", "bebidas", "1,5 L", "1.5", "0.55"),
    ("Agua con gas", "Vichy Catalán", "bebidas", "1 L", "1", "0.95"),
    ("Refresco de cola", "Coca-Cola", "bebidas", "2 L", "2", "1.89"),
    ("Refresco de naranja", "Fanta", "bebidas", "2 L", "2", "1.79"),
    ("Zumo de naranja", "Don Simón", "bebidas", "1 L", "1", "1.29"),
    ("Zumo de piña", "Juver", "bebidas", "1 L", "1", "1.39"),
    ("Cerveza rubia", "Mahou", "bebidas", "6x330 ml", "1.98", "3.99"),
    (
        "Cerveza sin alcohol",
        "Estrella Galicia",
        "bebidas",
        "6x330 ml",
        "1.98",
        "3.79",
    ),
    ("Vino tinto joven", "Marqués de Cáceres", "bebidas", "750 ml", "0.75", "5.49"),
    ("Tónica", "Schweppes", "bebidas", "1 L", "1", "1.09"),
    # Aceites y condimentos
    (
        "Aceite de oliva virgen extra",
        "Carbonell",
        "aceites",
        "1 L",
        "1",
        "7.99",
    ),
    ("Aceite de girasol", "Koipesol", "aceites", "1 L", "1", "2.19"),
    ("Vinagre de vino", "Heinz", "aceites", "1 L", "1", "1.49"),
    ("Salsa de tomate frito", "Orlando", "aceites", "560 g", "0.56", "1.69"),
    ("Mayonesa", "Hellmann's", "aceites", "450 ml", "0.45", "2.49"),
    ("Kétchup", "Heinz", "aceites", "570 g", "0.57", "2.09"),
    ("Miel de romero", "Granja San Francisco", "aceites", "500 g", "0.5", "4.29"),
    ("Sal marina", "Salinas de Añana", "aceites", "1 kg", "1", "1.19"),
    ("Pimienta negra molida", "Ducros", "aceites", "50 g", "0.05", "1.59"),
    ("Orégano seco", "Hacendado", "aceites", "20 g", "0.02", "0.99"),
    # Arroz, pasta y legumbres
    ("Arroz redondo", "SOS", "arroz_pasta", "1 kg", "1", "1.59"),
    ("Arroz basmati", "Fallera", "arroz_pasta", "1 kg", "1", "2.49"),
    ("Pasta espagueti", "Barilla", "arroz_pasta", "500 g", "0.5", "1.29"),
    ("Pasta macarrones", "Gallo", "arroz_pasta", "500 g", "0.5", "0.99"),
    ("Lentejas pardinas", "Luengo", "arroz_pasta", "1 kg", "1", "2.19"),
    ("Garbanzos pedrosillanos", "Luengo", "arroz_pasta", "1 kg", "1", "2.29"),
    ("Alubias blancas", "Luengo", "arroz_pasta", "1 kg", "1", "2.39"),
    ("Quinoa real", "Nomen", "arroz_pasta", "500 g", "0.5", "3.29"),
    ("Cuscús precocido", "Gallo", "arroz_pasta", "500 g", "0.5", "1.79"),
    ("Harina de trigo", "Santa Rita", "arroz_pasta", "1 kg", "1", "0.89"),
    # Conservas
    ("Atún claro en aceite", "Calvo", "conservas", "3x80 g", "0.24", "2.99"),
    ("Atún en agua", "Isabel", "conservas", "3x80 g", "0.24", "2.79"),
    ("Sardinas en aceite", "Cuca", "conservas", "120 g", "0.12", "1.49"),
    ("Tomate triturado", "Solís", "conservas", "400 g", "0.4", "1.09"),
    ("Tomate pelado", "Mutti", "conservas", "400 g", "0.4", "1.39"),
    ("Maíz dulce", "Hacendado", "conservas", "300 g", "0.3", "1.19"),
    ("Aceitunas verdes", "La Española", "conservas", "340 g", "0.34", "1.49"),
    ("Pimientos del piquillo", "Coquet", "conservas", "220 g", "0.22", "2.19"),
    ("Champiñones laminados", "Carretilla", "conservas", "400 g", "0.4", "1.29"),
    ("Espárragos blancos", "Coquet", "conservas", "330 g", "0.33", "2.49"),
    # Panadería y bollería
    ("Pan de molde blanco", "Bimbo", "panaderia", "460 g", "0.46", "1.89"),
    ("Pan de molde integral", "Hacendado", "panaderia", "460 g", "0.46", "1.79"),
    ("Pan rústico", "Panrico", "panaderia", "400 g", "0.4", "1.59"),
    ("Galletas maría", "Fontaneda", "panaderia", "800 g", "0.8", "2.49"),
    ("Galletas de chocolate", "Chiquilín", "panaderia", "500 g", "0.5", "2.29"),
    ("Magdalenas", "Valenciana", "panaderia", "400 g", "0.4", "1.99"),
    ("Croissants", "Dulcesol", "panaderia", "360 g", "0.36", "1.89"),
    ("Cereales de maíz", "Kellogg's", "panaderia", "500 g", "0.5", "3.19"),
    ("Copos de avena", "Quaker", "panaderia", "500 g", "0.5", "2.09"),
    ("Tostadas integrales", "Bimbo", "panaderia", "400 g", "0.4", "1.69"),
    # Limpieza
    ("Detergente líquido", "Ariel", "limpieza", "1,5 L", "1.5", "8.99"),
    ("Detergente en cápsulas", "Persil", "limpieza", "30 uds", "1.2", "9.99"),
    ("Suavizante", "Mimosín", "limpieza", "1,5 L", "1.5", "3.49"),
    ("Lavavajillas líquido", "Fairy", "limpieza", "900 ml", "0.9", "3.29"),
    ("Pastillas lavavajillas", "Finish", "limpieza", "40 uds", "0.8", "9.49"),
    ("Limpiador multiusos", "Ajax", "limpieza", "1 L", "1", "2.19"),
    ("Lejía", "Estrella", "limpieza", "2 L", "2", "1.39"),
    ("Fregasuelos", "Don Limpio", "limpieza", "1,5 L", "1.5", "3.09"),
    ("Limpiacristales", "Cristasol", "limpieza", "750 ml", "0.75", "2.49"),
    ("Ambientador", "Glade", "limpieza", "300 ml", "0.3", "2.29"),
    # Higiene
    ("Gel de ducha", "Sanex", "higiene", "750 ml", "0.75", "2.99"),
    ("Champú", "Pantene", "higiene", "500 ml", "0.5", "3.99"),
    ("Pasta de dientes", "Colgate", "higiene", "100 g", "0.1", "2.09"),
    ("Enjuague bucal", "Listerine", "higiene", "500 ml", "0.5", "4.29"),
    ("Jabón de manos", "Dove", "higiene", "500 ml", "0.5", "2.39"),
    ("Desodorante", "Rexona", "higiene", "150 ml", "0.15", "2.89"),
    ("Crema hidratante", "Nivea", "higiene", "400 ml", "0.4", "5.99"),
    ("Papel higiénico", "Scottex", "higiene", "8 rollos", "1.2", "4.99"),
    ("Crema de manos", "Neutrogena", "higiene", "75 ml", "0.075", "3.49"),
    ("Gel de afeitado", "Gillette", "higiene", "200 ml", "0.2", "3.19"),
    # Congelados
    ("Guisantes congelados", "Findus", "congelados", "1 kg", "1", "2.49"),
    ("Verduras para sopa", "La Sirena", "congelados", "1 kg", "1", "2.79"),
    ("Patatas fritas congeladas", "McCain", "congelados", "1 kg", "1", "2.99"),
    (
        "Pizza cuatro quesos",
        "Casa Tarradellas",
        "congelados",
        "400 g",
        "0.4",
        "3.49",
    ),
    ("Pizza margarita", "Dr. Oetker", "congelados", "350 g", "0.35", "2.99"),
    ("Helado de vainilla", "Häagen-Dazs", "congelados", "500 ml", "0.5", "5.99"),
    ("Helado de chocolate", "Nestlé", "congelados", "1 L", "1", "3.99"),
    ("Croquetas de jamón", "La Cocinera", "congelados", "800 g", "0.8", "4.49"),
    ("Pescado empanado", "Pescanova", "congelados", "600 g", "0.6", "4.99"),
    ("Fruta del bosque", "Hacendado", "congelados", "500 g", "0.5", "3.29"),
    # Snacks y dulces
    ("Patatas fritas", "Lay's", "snacks", "300 g", "0.3", "2.29"),
    ("Patatas fritas onduladas", "Lay's", "snacks", "300 g", "0.3", "2.39"),
    ("Chocolate con leche", "Milka", "snacks", "300 g", "0.3", "2.49"),
    ("Chocolate negro 70%", "Valor", "snacks", "250 g", "0.25", "2.69"),
    ("Frutos secos variados", "Borges", "snacks", "500 g", "0.5", "3.99"),
    ("Almendras crudas", "Borges", "snacks", "500 g", "0.5", "4.99"),
    ("Cacahuetes salados", "Facundo", "snacks", "500 g", "0.5", "2.49"),
    ("Caramelos de menta", "Halls", "snacks", "200 g", "0.2", "1.29"),
    ("Chicles sin azúcar", "Orbit", "snacks", "100 g", "0.1", "1.59"),
    ("Palomitas microondas", "Popitas", "snacks", "300 g", "0.3", "1.79"),
)

PRODUCTOS: tuple[ProductoSeed, ...] = tuple(
    ProductoSeed(
        nombre=nombre,
        marca=marca,
        categoria=categoria,
        formato=formato,
        litros_o_kg=Decimal(litros),
        precio_eur=Decimal(precio),
    )
    for nombre, marca, categoria, formato, litros, precio in _PRODUCTOS_CRUDOS
)
