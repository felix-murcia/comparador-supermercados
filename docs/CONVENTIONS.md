# CONVENTIONS.md

**Propósito**: Convenciones de código, nombres, estructura y estilo para todo el repositorio. Este documento amplía la sección 6 de `AGENTS.md` con ejemplos concretos.

**Última actualización**: 2026-10-19
**Aplica a**: `api/`, `web/`, `infra/`, `docs/`

---

## 1. Principios generales

1. **Claridad sobre cleverness**: el código se lee más veces de las que se escribe.
2. **Consistencia sobre preferencia personal**: si existe una convención, se sigue aunque no sea tu favorita.
3. **Un tema = un archivo**: si un archivo crece, divídelo por responsabilidad.
4. **Funciones cortas**: idealmente <30 líneas. Si supera 50, extrae.
5. **Nombres que revelan intención**: `calcular_ahorro_cesta` > `calc` > `f`.
6. **Sin comentarios que repitan el código**: los comentarios explican *por qué*, no *qué*.
7. **Errores explícitos**: falla rápido y con mensaje claro. No silencies excepciones.

---

## 2. Estructura de carpetas

### 2.1 Backend (`api/`)

```
api/
├── src/
│   ├── dominio/                    # Entidades + reglas de negocio puras
│   │   ├── productos/
│   │   │   ├── entidades.py        # Producto, Formato
│   │   │   ├── errores.py          # ProductoNoEncontrado, etc.
│   │   │   └── reglas.py           # Cálculo €/L, normalización
│   │   ├── precios/
│   │   ├── listas/
│   │   ├── usuarios/
│   │   └── busquedas/
│   ├── aplicacion/                 # Casos de uso (orquestan dominio + puertos)
│   │   ├── buscar_producto.py
│   │   ├── comparar_lista.py
│   │   ├── calcular_ahorro.py
│   │   └── gestionar_listas.py
│   ├── puertos/                    # Interfaces (Protocol en Python)
│   │   ├── repositorios.py
│   │   ├── productor.py
│   │   ├── verificador.py
│   │   ├── cache.py
│   │   └── auth.py
│   ├── adaptadores/                # Implementaciones concretas
│   │   ├── persistencia/           # SQLAlchemy
│   │   ├── ingesta/                # LLM, fetch
│   │   ├── cache/                  # Redis
│   │   └── auth/                   # OAuth
│   ├── api_http/                   # FastAPI (traduce, no decide)
│   │   ├── v1/
│   │   │   ├── busquedas.py
│   │   │   ├── comparar.py
│   │   │   ├── listas.py
│   │   │   └── usuarios.py
│   │   ├── dependencias.py         # Depends() de FastAPI
│   │   ├── errores.py              # Exception handlers
│   │   └── schemas.py              # DTOs Pydantic (Request/Response)
│   ├── config.py                   # pydantic-settings
│   ├── logging.py                  # Configuración de logs
│   ├── worker.py                   # Punto de entrada del worker
│   ├── scheduler.py                # Punto de entrada del scheduler
│   └── main.py                     # Punto de entrada de la API
├── tests/
│   ├── dominio/                    # Tests puros, sin BD
│   ├── aplicacion/                 # Tests con mocks de puertos
│   ├── adaptadores/                # Tests de integración (BD, Redis)
│   └── api_http/                   # Tests de endpoints (TestClient)
├── alembic/
│   └── versions/
├── Dockerfile
├── pyproject.toml
└── .env.example
```

### 2.2 Frontend (`web/`)

```
web/
├── src/
│   ├── app/                        # Next.js App Router
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── callback/
│   │   ├── (app)/
│   │   │   ├── buscar/
│   │   │   ├── producto/[slug]/
│   │   │   ├── listas/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   └── perfil/
│   │   ├── layout.tsx
│   │   └── page.tsx                # Hero inicial
│   ├── components/
│   │   ├── ui/                     # Primitivos (Button, Input, Card)
│   │   ├── busqueda/               # BarraBusqueda, SelectorCadenas
│   │   ├── producto/               # CardProducto, ListaCards
│   │   ├── listas/                 # ListaCompra, ResumenAhorro
│   │   └── layout/                 # MenuLateral, Header
│   ├── lib/
│   │   ├── api.ts                  # Cliente HTTP tipado
│   │   ├── auth.ts                 # Config Auth.js
│   │   ├── format.ts               # Formateo €, €/L
│   │   └── i18n.ts                 # t(key)
│   ├── locales/
│   │   └── es.json
│   └── types/
│       └── api.d.ts                # Tipos generados o manuales
├── public/
│   └── logos/
│       ├── dia.svg
│       ├── carrefour.svg
│       └── mercadona.svg
├── Dockerfile
├── package.json
├── tsconfig.json
└── next.config.js
```

---

## 3. Convenciones de nombres

### 3.1 Python

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Módulos | `snake_case` | `buscar_producto.py` |
| Paquetes | `snake_case` | `api_http/` |
| Clases | `PascalCase` | `Producto`, `VerificadorPrecio` |
| Funciones | `snake_case` | `calcular_precio_por_litro` |
| Variables | `snake_case` | `precio_eur`, `lista_items` |
| Constantes | `UPPER_SNAKE_CASE` | `CACHE_TTL_SEGUNDOS`, `MAX_REINTENTOS` |
| Privados | prefijo `_` | `_normalizar_query` |
| Puertos (interfaces) | nombre de dominio | `Productor`, `Verificador`, `RepositorioPrecios` |
| Adaptadores | prefijo por tecnología | `LLMProductor`, `SQLAlchemyRepositorioPrecios`, `RedisCache` |
| Casos de uso | verbo infinitivo | `BuscarProducto`, `CalcularAhorroLista` |
| DTOs API | sufijo `Request`/`Response` | `BusquedaRequest`, `CompararResponse` |
| Errores de dominio | sufijo `Error` | `ProductoNoEncontradoError` |

### 3.2 TypeScript / React

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Componentes | `PascalCase` + archivo igual | `CardProducto.tsx` |
| Hooks | `useCamelCase` | `useBusqueda.ts` |
| Utilidades | `camelCase` | `formatPrecio.ts` |
| Tipos/Interfaces | `PascalCase`, sin prefijo `I` | `Producto`, `Precio` |
| Constantes | `UPPER_SNAKE_CASE` | `CACHE_TTL_MS` |
| Carpetas de componentes | `kebab-case` o dominio | `producto/`, `listas/` |
| Funciones | `camelCase` | `calcularAhorro` |
| Variables | `camelCase` | `precioUnitario` |

**Regla**: un componente por archivo. Si dos componentes van juntos porque son triviales (ej: `CardHeader` + `CardBody`), extrae a un archivo `Card.tsx` con subcomponentes exportados.

### 3.3 SQL

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Tablas | `snake_case`, plural | `productos`, `precios`, `lista_items` |
| Columnas | `snake_case` | `precio_eur`, `fecha_consulta` |
| Claves foráneas | `<tabla_singular>_id` | `producto_id`, `cadena_id` |
| Claves primarias | `id` (UUID) | `id UUID PRIMARY KEY` |
| Timestamps | `creado_en`, `actualizado_en` | `creado_en TIMESTAMPTZ` |
| Booleanos | adjetivo o `tiene_`/`es_` | `disponible`, `es_activo` |
| Enums (texto) | `snake_case` en valor | `'verificado'`, `'sospechoso'` |
| Índices | `idx_<tabla>_<columnas>` | `idx_precios_producto_fecha` |
| Constraints | `chk_<tabla>_<regla>` | `chk_precios_ambito_provincia` |

### 3.4 API HTTP

| Elemento | Convención | Ejemplo |
|----------|-----------|---------|
| Recursos | plural, `kebab-case` si compuesto | `/productos`, `/lista-items` |
| Versionado | prefijo `/v1/` | `/v1/productos` |
| Acciones no CRUD | verbo en path solo si necesario | `/v1/busquedas/{id}/cancelar` |
| Query params | `snake_case` | `?precio_min=1&precio_max=10` |
| JSON keys | `snake_case` | `{ "precio_eur": 4.45 }` |
| Códigos de error | `UPPER_SNAKE_CASE` | `PRODUCTO_NO_ENCONTRADO` |

---

## 4. Estilo de código

### 4.1 Python

**Formato**: `ruff format` (línea 100). **Lint**: `ruff check`. **Tipos**: `mypy --strict`.

```python
# ✅ Bien: función corta, tipada, early return
from decimal import Decimal

def calcular_precio_por_litro(
    precio_eur: Decimal,
    litros: Decimal,
) -> Decimal | None:
    if litros <= 0:
        return None
    return (precio_eur / litros).quantize(Decimal("0.0001"))


# ❌ Mal: sin tipos, sin guarda, nombre ambiguo
def calc(p, l):
    return p / l
```

**Imports**: ordenados por `ruff` (stdlib → third-party → first-party). Sin imports relativos profundos (`from ...dominio`): usa imports absolutos desde `src`.

```python
# ✅ Bien
from src.dominio.precios.reglas import calcular_precio_por_litro

# ❌ Mal
from ...dominio.precios.reglas import calcular_precio_por_litro
```

**Errores de dominio**: clases propias, no `ValueError` genérico.

```python
# ✅ Bien
class ProductoNoEncontradoError(Exception):
    def __init__(self, producto_id: str) -> None:
        self.producto_id = producto_id
        super().__init__(f"Producto no encontrado: {producto_id}")

# ❌ Mal
raise ValueError("no encontrado")
```

**Async**: usa `async def` en adaptadores que hacen I/O (BD, Redis, HTTP). Dominio y casos de uso pueden ser síncronos si no hay I/O.

**Logging**: nunca `print`. Usa el logger configurado.

```python
import logging

logger = logging.getLogger(__name__)

logger.info("busqueda_iniciada", extra={"query": query, "cadenas": cadenas})
```

**Nunca loguees**: `authorization`, `api_key`, `password`, `token`, `cookie`, `client_secret`.

### 4.2 TypeScript / React

**Formato**: `prettier`. **Lint**: `eslint` + `@typescript-eslint`. **Tipos**: `strict: true`.

```tsx
// ✅ Bien: props tipadas, componente puro, sin any
type CardProductoProps = {
  producto: Producto;
  onAñadir: (productoId: string) => void;
};

export function CardProducto({ producto, onAñadir }: CardProductoProps) {
  return (
    <article className="card">
      <h3>{producto.nombre}</h3>
      <p>{formatPrecio(producto.precioEur)}</p>
      <button onClick={() => onAñadir(producto.id)}>Añadir</button>
    </article>
  );
}

// ❌ Mal: any, sin tipos, lógica mezclada
export function Card(props: any) {
  return <div onClick={() => fetch('/api/x')}>{props.data.n}</div>;
}
```

**Server vs. Client Components**:
- Por defecto, `Server Component` (sin `"use client"`).
- `"use client"` solo si hay estado, efectos o eventos del navegador.
- Lógica de datos (fetch a API) en Server Components o en `lib/api.ts`.

**Estado**: `useState` para local, `useReducer` para estado complejo, `Context` solo para temas/auth. No Redux/Zustand en MVP.

**Estilos**: `Tailwind CSS` (a decidir en ADR-002). Sin CSS-in-JS. Clases utilitarias, sin componentes con estilos embebidos salvo primitivos en `components/ui/`.

**i18n**: nunca strings en JSX. Siempre `t("clave")`.

```tsx
// ✅ Bien
<h1>{t("busqueda.titulo")}</h1>

// ❌ Mal
<h1>Buscar productos</h1>
```

### 4.3 SQL / Alembic

**Migraciones**: una por cambio lógico. Nombre descriptivo.

```bash
alembic revision --autogenerate -m "add_provincia_to_precios"
```

**Nunca** edites una migración ya aplicada. Crea una nueva.

**Índices**: añade índice si una consulta filtra/ordena por columna en tablas grandes (>10k filas previstas).

**Constraints**: valida en BD lo que el dominio asume (ej: `ambito='nacional' OR provincia IS NOT NULL`).

---

## 5. Patrones por capa

### 5.1 Dominio

- **Entidades**: dataclasses o clases puras. Sin dependencias externas.
- **Value Objects**: `Formato`, `Precio`, `Provincia`. Inmutables (`frozen=True`).
- **Reglas**: funciones puras, testeables sin mocks.
- **Errores**: clases propias, con contexto.

```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Formato:
    litros_o_kg: Decimal
    unidad: str  # "L" | "ml" | "kg" | "g"

    def a_litros_o_kg(self) -> Decimal:
        if self.unidad in ("ml", "g"):
            return self.litros_o_kg / Decimal(1000)
        return self.litros_o_kg
```

### 5.2 Puertos

- `Protocol` de Python (no ABC, salvo herencia necesaria).
- Un puerto = una responsabilidad.
- Métodos con tipos, sin implementación.

```python
from typing import Protocol

class Productor(Protocol):
    async def producir(self, query: str, cadena: str) -> dict: ...
```

### 5.3 Adaptadores

- Implementan un puerto.
- Prefijo por tecnología: `LLMProductor`, `SQLAlchemyRepositorioPrecios`.
- Toda la I/O aquí. Nada de I/O en dominio ni en casos de uso (salvo vía puerto).

### 5.4 Casos de uso

- Un archivo por caso de uso.
- Reciben puertos por inyección (constructor o argumento).
- Orquestan: leen, deciden, escriben.
- Devuelven DTOs de dominio, no entidades de BD.

```python
class BuscarProducto:
    def __init__(self, productor: Productor, verificador: Verificador, repo: RepositorioPrecios):
        self.productor = productor
        self.verificador = verificador
        self.repo = repo

    async def ejecutar(self, query: str, cadena: str) -> ResultadoBusqueda:
        for _ in range(MAX_REINTENTOS):
            candidato = await self.productor.producir(query, cadena)
            estado, motivos = await self.verificador.verificar(candidato)
            if estado == "verificado":
                await self.repo.guardar(candidato)
                return ResultadoBusqueda.exito(candidato)
        return ResultadoBusqueda.fallo(motivos)
```

### 5.5 API HTTP

- Solo traduce: request HTTP → caso de uso → response HTTP.
- Sin lógica de negocio.
- DTOs Pydantic en `schemas.py`.
- Errores de dominio → HTTP status + `{ code, message }`.

```python
@router.post("/v1/busquedas", response_model=BusquedaResponse)
async def crear_busqueda(
    body: BusquedaRequest,
    caso_uso: BuscarProducto = Depends(get_buscar_producto),
) -> BusquedaResponse:
    resultado = await caso_uso.ejecutar(body.query, body.cadena)
    return BusquedaResponse.from_dominio(resultado)
```

---

## 6. Testing

### 6.1 Pirámide

- **Dominio** (70%): tests puros, sin mocks, rápidos.
- **Aplicación** (20%): casos de uso con puertos mockeados.
- **Adaptadores** (8%): integración con BD/Redis reales (testcontainers o compose).
- **API** (2%): endpoints con `TestClient`, BD real de test.

### 6.2 Convenciones

- Nombres: `test_<que_se_prueba>_<condicion>_<resultado_esperado>`.
- Un `assert` lógico por test (varios asserts permitidos si validan lo mismo).
- Fixtures en `conftest.py`.
- Sin `time.sleep`. Usa `freezegun` o mocks de tiempo.

```python
def test_calcular_precio_por_litro_con_litros_cero_devuelve_none():
    assert calcular_precio_por_litro(Decimal("4.45"), Decimal("0")) is None
```

### 6.3 Cobertura

- Objetivo: 80% en `dominio` y `aplicacion`.
- No persigas 100% en `adaptadores` (integración es costosa).
- CI falla si cobertura de `dominio` < 80%.

---

## 7. Git y commits

### 7.1 Conventional Commits

```
<tipo>(<scope>): <descripción>

[cuerpo opcional]

[footer opcional]
```

**Tipos**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`, `build`.

**Scopes**: `api`, `web`, `worker`, `scheduler`, `infra`, `docs`, `db`.

**Ejemplos**:
```
feat(api): añadir endpoint POST /v1/busquedas
fix(worker): corregir reintento infinito en verificador
docs(plan): actualizar criterios de aceptación del MVP
refactor(dominio): extraer cálculo de €/L a Value Object
test(api): cubrir cache hit en POST /v1/busquedas
chore(infra): actualizar Postgres a 16.4
```

### 7.2 Ramas

- `main`: protegida, solo merge vía PR.
- `feat/<epica>-<descripcion>`: nuevas funcionalidades.
- `fix/<descripcion>`: correcciones.
- `docs/<descripcion>`: solo documentación.
- `chore/<descripcion>`: infra, deps.

### 7.3 PRs

- Título = Conventional Commit.
- Descripción: qué, por qué, cómo probar.
- Un PR = un issue (o varios relacionados).
- No mezclar refactor con feature.
- CI verde obligatorio antes de merge.

---

## 8. Variables de entorno

- **Todo** configurable va en `.env`. Cero hardcode de URLs, puertos, credenciales.
- `.env.example` es la fuente de verdad de las variables disponibles.
- En código, acceso vía `settings` (`pydantic-settings`), nunca `os.getenv` directo.

```python
# ✅ Bien
from src.config import settings
ttl = settings.cache_ttl_segundos

# ❌ Mal
import os
ttl = int(os.getenv("CACHE_TTL", "86400"))
```

- Nuevas variables: añadir a `.env.example` con comentario y valor por defecto cuando aplique.

---

## 9. Manejo de errores

### 9.1 Backend

- **Dominio**: excepciones propias con contexto.
- **Aplicación**: captura excepciones de puertos, las traduce a errores de dominio o las propaga.
- **API**: `exception_handler` global traduce errores de dominio a HTTP.

```python
# api_http/errores.py
@ app.exception_handler(ProductoNoEncontradoError)
async def producto_no_encontrado_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"code": "PRODUCTO_NO_ENCONTRADO", "message": str(exc)},
    )
```

### 9.2 Frontend

- **Errores de red**: mostrar toast con mensaje genérico + reintentar.
- **Errores de validación**: mostrar en el campo correspondiente.
- **Errores inesperados**: `error.tsx` de Next.js + Sentry.
- Nunca mostrar stack traces al usuario.

---

## 10. Formateo de datos

### 10.1 Precios

- Backend: `Decimal` (nunca `float` para dinero). Serializar como string en JSON para evitar pérdida de precisión.
- Frontend: formatear con `Intl.NumberFormat("es-ES", { style: "currency", currency: "EUR" })`.
- €/L y €/kg: 4 decimales en BD, 2 en UI.

### 10.2 Fechas

- Backend: `datetime` con timezone (`TIMESTAMPTZ` en BD). Serializar en ISO 8601 UTC.
- Frontend: formatear a hora local con `Intl.DateTimeFormat("es-ES")`.

### 10.3 Texto

- Normalización de query: `lowercase`, sin tildes, sin espacios múltiples. Función única en `dominio/productos/reglas.py`.
- Nombres de producto: guardar tal cual vienen de la fuente. No traducir.

---

## 11. Accesibilidad y UI

- **Contraste**: mínimo WCAG AA (4.5:1 texto normal).
- **Navegación por teclado**: todo interactivo accesible con Tab. Foco visible.
- **Alt text**: imágenes de producto con `alt` descriptivo. Logos con `alt` del supermercado.
- **Formularios**: `<label>` asociado a cada input.
- **Semántica**: `<button>` para acciones, `<a>` para navegación. No `<div onClick>`.
- **Estilo minimalista tipo Google**: mucho espacio en blanco, tipografía clara, sin sombras ni gradientes innecesarios.

---

## 12. Checklist antes de commitear

- [ ] `ruff format` aplicado (api).
- [ ] `ruff check` sin errores (api).
- [ ] `mypy` sin errores (api).
- [ ] `prettier` aplicado (web).
- [ ] `eslint` sin errores (web).
- [ ] `tsc --noEmit` sin errores (web).
- [ ] Tests pasan (`pytest`, `npm test`).
- [ ] Sin `print` ni `console.log` de depuración.
- [ ] Sin secretos en el diff (`gitleaks` pasa).
- [ ] Sin `TODO` sin issue.
- [ ] Si toqué BD, migración incluida.
- [ ] Si añadí dependencia, justificada en el commit/PR.
- [ ] Mensaje de commit sigue Conventional Commits.

---

## 13. Recursos de referencia

- **Python**: PEP 8, PEP 484 (type hints), PEP 544 (Protocol).
- **FastAPI**: docs oficiales, patrones de dependencias.
- **Next.js**: App Router, Server Components.
- **PostgreSQL**: docs oficiales, `pg_trgm` para búsqueda difusa.
- **Conventional Commits**: https://www.conventionalcommits.org/
- **SOLID**: principios aplicados en `docs/decisions.md` (ADR-001).

---
