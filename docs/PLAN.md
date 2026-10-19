# Plan de Acción y Requisitos de Negocio
## Comparador de Precios de Supermercados Españoles

**Versión**: 1.0
**Fecha**: 2026-10-19
**Estado**: Aprobado para desarrollo
**Entorno de desarrollo**: OpenCode

---

## 1. Visión del producto

Aplicación web que permite a usuarios en España comparar precios de productos de supermercados (DIA, Carrefour, Mercadona inicialmente), gestionar listas de la compra y calcular el ahorro real de comprar la misma cesta en distintas cadenas o de forma mixta.

**Propuesta de valor**:
- Comparativa de precios verificados (no estimados) entre cadenas.
- Cálculo de ahorro real por cesta completa (no por producto suelto).
- Interfaz minimalista tipo Google: buscar → comparar → decidir.

**Público objetivo**: consumidores españoles que hacen la compra habitual en uno o varios supermercados y quieren optimizar el gasto.

**Idioma**: español en MVP. Arquitectura preparada para i18n (evoluciones posteriores).

---

## 2. Requisitos funcionales

### RF-01 Autenticación
- El usuario accede a la página principal y debe autenticarse para usar la app.
- Métodos: **Google OAuth 2.0** y **Microsoft (Entra ID) OAuth 2.0**.
- No hay login con contraseña propia.
- Al autenticarse se crea o recupera el perfil del usuario.

### RF-02 Búsqueda y comparativa
- Tras login, el usuario ve una barra de búsqueda centrada (estilo Google).
- Opciones de búsqueda:
  - **Orden**: precio unitario (por defecto), precio por kg/L, relevancia.
  - **Filtros**: solo con stock, rango de precio (min/max), marca, categoría.
- Debajo de la barra: selector de supermercados con logos SVG (selección múltiple).
- Botón "Comparar" lanza la búsqueda.
- **Comportamiento de la barra de progreso**:
  - Si la búsqueda está en caché (TTL 24 h): resultados instantáneos, sin barra.
  - Si no está en caché: barra de progreso con polling cada 1–2 s.
- Al mostrar resultados, la barra de búsqueda se mueve al top, desaparece el selector de supermercados y aparecen las cards de producto.
- Flecha "volver" a la izquierda del buscador para iniciar nueva búsqueda.
- Se puede relanzar búsqueda desde la misma página manteniendo filtros.

### RF-03 Card de producto
Cada card debe mostrar:
- Logo del supermercado (SVG).
- Posición en el ranking.
- Imagen del producto (clicable → página del producto en el supermercado).
- Nombre del producto.
- Precio unitario (€).
- Precio por kg/L (€/kg o €/L).

### RF-04 Menú lateral colapsable
- Acceso al perfil del usuario (nombre, email, ubicación, etc.).
- Gestión de listas de la compra: crear, modificar, eliminar.

### RF-05 Listas de la compra
- El usuario puede añadir productos a una o varias listas desde las cards.
- Cada lista muestra:
  - Coste total.
  - **% de ahorro A**: coste de la cesta completa en la cadena más cara vs. cadena actual.
  - **% de ahorro C**: coste de la cesta mixta real vs. coste de la cesta óptima (mezclando lo más barato de cada cadena).
- Datos adicionales se añadirán en evoluciones posteriores.

### RF-06 Ubicación del usuario
- Si el usuario tiene provincia configurada: se muestran precios de su provincia cuando existan.
- Si no la tiene: se muestran precios genéricos (nacionales) con aviso visible al usuario.
- Fallback: provincia → nacional → producto no disponible.

### RF-07 Caché de búsquedas
- TTL de 24 horas.
- Clave de caché: hash de `(query_normalizada, cadenas, orden, filtros, provincia)`.
- Solo se cachean resultados **verificados**.
- Invalidación manual al completar la ingesta diaria.

### RF-08 Histórico de precios
- Incluido en el MVP.
- Visible en la ficha de producto.
- Fuente: tabla `precios` append-only.

### RF-09 Entornos
- **dev**: datos de prueba, hot-reload, sin TLS.
- **prod**: imágenes build, TLS, logs JSON, Sentry activo.
- Configuración separada por variables de entorno. **Cero hardcode**.

---

## 3. Requisitos no funcionales

### RNF-01 Seguridad
- **Cero secretos en código** (API keys, passwords, tokens, nombres propios). Penalización grave.
- `.env.example` en repo con claves vacías.
- `.env` real en `.gitignore`.
- Pre-commit hook con `gitleaks` o `detect-secrets`.
- Secretos en producción: Docker secrets / K8s Secrets / SOPS.
- Rotación de secretos documentada.
- Logs con redacción de campos sensibles (`authorization`, `api_key`, `password`).

### RNF-02 Arquitectura
- **Monolito modular** con capas: `dominio`, `aplicacion`, `puertos`, `adaptadores`, `api_http`.
- **Principios SOLID** estrictos.
- Baja complejidad ciclomática: early returns, diccionarios de dispatch, funciones cortas.
- **Stateless**: la API no guarda estado en disco. Sesiones en JWT o Redis.
- **12-factor**: config por env vars, logs a stdout, procesos separados.
- **Portable a Kubernetes/OpenShift**: healthchecks, manifiestos como plantilla, sin cron interno.

### RNF-03 Base de datos
- **PostgreSQL** con replicación streaming.
- **Primario (RW)**: escrituras, migraciones, ingesta.
- **Réplica (RO)**: lecturas de API pública.
- CQRS ligero: routing de lecturas/escrituras por engine.
- Migraciones con Alembic, ejecutadas como job separado (no en arranque de API).

### RNF-04 Caché y colas
- **Redis** para caché de búsquedas (TTL 24 h) y como soporte de colas.
- Cola de jobs en Postgres con `SKIP LOCKED` para MVP (menos piezas que Redis queue).

### RNF-05 Despliegue
- **dev/MVP**: docker-compose en VPS.
- **prod inicial**: docker-compose en VPS + réplica lectura.
- **escala**: manifiestos K8s/OpenShift (plantilla preparada, no desplegar aún).
- Contenedores separados: `api`, `worker`, `scheduler`, `web`.

### RNF-06 Observabilidad
- Logs estructurados (JSON en prod).
- Sentry para errores.
- UptimeRobot para disponibilidad.
- Métricas de ingesta: % verificado, % rechazado, motivos.

### RNF-07 Calidad
- Tests de dominio (pytest).
- Tests de componentes (Vitest).
- CI con lint + tests + build + gitleaks + trivy.
- ADRs en `decisions.md`.

### RNF-08 i18n
- MVP en español.
- Strings en `locales/es.json` desde el día 1.
- Función `t(key)` en frontend.
- Mensajes de error backend en códigos, no en texto.

---

## 4. Stack tecnológico

| Capa | Tecnología | Justificación |
|------|-----------|---------------|
| Backend | Python 3.12 + FastAPI | Async nativo, tipado, ecosistema LLM/scraping |
| Frontend | Next.js 14 (App Router) + React | SSR para SEO, ecosistema maduro |
| BD | PostgreSQL 16 | Histórico relacional, JSONB, pg_trgm |
| Caché/Cola | Redis 7 | TTL nativo, colas simples |
| Reverse proxy | Caddy 2 | TLS automático, config mínima |
| Contenedores | Docker + docker-compose | Reproducibilidad |
| Orquestación (futuro) | Kubernetes / OpenShift | Portabilidad |
| Auth | Auth.js (NextAuth) | OAuth Google + Microsoft |
| LLM | Proveedor con búsqueda web (configurable) | Productor de precios |
| CI/CD | GitHub Actions | Gratis, integrado |
| Observabilidad | Sentry + UptimeRobot | Free tier suficiente MVP |

---

## 5. Arquitectura de referencia

```
┌──────────────────────────────────────────────────────┐
│                    CLIENTE (web)                     │
│              Next.js 14 (App Router)                 │
└───────────────────────┬──────────────────────────────┘
                        │ HTTPS
┌───────────────────────▼──────────────────────────────┐
│              REVERSE PROXY (Caddy)                   │
│         TLS automático, compresión, rate limit       │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│                  API (FastAPI)                       │
│  - /busquedas, /comparar, /productos, /listas, /me   │
│  - Healthchecks /health/live, /health/ready          │
│  - Lecturas → engine_ro, escrituras → engine_rw      │
└───────┬───────────────────────────────┬──────────────┘
        │                               │
┌───────▼────────┐              ┌───────▼──────────────┐
│  PostgreSQL    │              │  Redis               │
│  - primario RW │              │  - caché TTL 24h     │
│  - réplica RO  │              │  - rate limit        │
└───────▲────────┘              └──────────────────────┘
        │
┌───────┴──────────────────────────────────────────────┐
│           WORKER DE INGESTA (proceso aparte)         │
│  - Productor (LLM con búsqueda)                      │
│  - Verificador (fetch + reglas deterministas)        │
│  - Reintento acotado (máx. 3 pasadas)                │
│  - Escritura en BD primario                          │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│           SCHEDULER (proceso aparte)                 │
│  - Ingesta diaria                                    │
│  - Invalidación de caché tras ingesta                │
└──────────────────────────────────────────────────────┘
```

**Estructura del monorepo**:
```
/app
  /api
    /src
      /dominio          # entidades + reglas (sin frameworks)
      /aplicacion       # casos de uso
      /puertos          # interfaces
      /adaptadores      # implementaciones (SQLAlchemy, LLM, OAuth)
      /api_http         # FastAPI (traduce, no decide)
      config.py
      main.py
    Dockerfile
    pyproject.toml
  /web
    /src
      /app
      /components
      /lib
      /locales
    Dockerfile
    package.json
  /infra
    docker-compose.base.yml
    docker-compose.dev.yml
    docker-compose.prod.yml
    /caddy
    /postgres
    /k8s                # plantillas
  .env.example
  .gitignore
  .pre-commit-config.yaml
  README.md
  decisions.md
```

---

## 6. Modelo de datos (resumen)

Tablas principales:
- `usuarios` (provider, provider_id, email, nombre, provincia, avatar_url)
- `cadenas` (slug, nombre, logo_svg)
- `productos` (nombre, marca, categoria, formato, litros_o_kg, ean)
- `productos_cadena` (producto_id, cadena_id, url_producto, nombre_en_cadena)
- `precios` (append-only: precio_eur, precio_por_litro_kg, disponible, promocion, ambito, provincia, estado, url_fuente, fecha_consulta)
- `busquedas` (usuario_id, query, cadenas, provincia, estado, progreso, cache_key)
- `listas` (usuario_id, nombre)
- `lista_items` (lista_id, producto_id, cadena_compra_id, cantidad, precio_snapshot)

Índices clave:
- `pg_trgm` en `productos.nombre` para búsqueda difusa.
- `(producto_cadena_id, fecha_consulta DESC)` en `precios`.
- `cache_key` en `busquedas`.

---

## 7. Flujos clave

### 7.1 Búsqueda con caché
```
POST /busquedas
  → calcular cache_key
  → ¿existe en Redis?
     → SÍ: devolver { job_id, cache_hit: true, resultados }
     → NO: encolar job, devolver { job_id, cache_hit: false }
        → worker procesa: productor → verificador → BD
        → guardar en Redis con TTL 24h
GET /busquedas/{job_id}
  → devolver estado + progreso + resultados parciales
```

### 7.2 Resolución de precio por ubicación
```
1. ¿usuario.provincia? → buscar precio ambito=provincia y provincia=X
2. Si no existe → fallback ambito=nacional
3. Si no existe → producto no disponible
```

### 7.3 Cálculo de ahorro (listas)
```
Dada una lista con N productos y M cadenas seleccionadas:

A) Para cada cadena:
   coste_cadena = sum(precio_producto_en_cadena)
   % A = (coste_cadena_mas_cara - coste_cadena) / coste_cadena_mas_cara

B) Cesta óptima:
   coste_optimo = sum(min(precio_producto entre cadenas))
   coste_mixta_real = sum(precio donde el usuario compró cada producto)
   % C = (coste_mixta_real - coste_optimo) / coste_mixta_real

Productos no disponibles en una cadena se excluyen con aviso en UI.
```

---

## 8. Backlog por épicas

### Épica 0 — Fundación
- [ ] Monorepo + compose base/dev/prod
- [ ] `.env.example` + `.gitignore` + gitleaks en pre-commit
- [ ] Dockerfiles separados: api, worker, scheduler, web
- [ ] Healthchecks `/health/live`, `/health/ready`
- [ ] Config por entorno con `pydantic-settings` (cero hardcode)
- [ ] CI: lint + tests + build + gitleaks + trivy
- [ ] Deploy VPS con Caddy

### Épica 1 — Autenticación
- [ ] OAuth Google + Microsoft con Auth.js
- [ ] Tabla `usuarios` + `GET /me`
- [ ] Middleware de sesión en Next.js + validación token en FastAPI
- [ ] Pantalla login/signup

### Épica 2 — Modelo de datos
- [ ] Esquema SQL + migraciones Alembic
- [ ] Dos engines SQLAlchemy (RW/RO) + routing
- [ ] Seed dev con datos de prueba (100 productos ficticios o reales de muestra)
- [ ] Repositorios + tests de dominio

### Épica 3 — Ingesta
- [ ] Puerto `Productor` + impl LLM con búsqueda
- [ ] Puerto `Verificador` + impl fetch+reglas
- [ ] Caso de uso `BuscarProducto` con reintento acotado (máx. 3)
- [ ] Cola Postgres `SKIP LOCKED` + worker como proceso aparte
- [ ] Scheduler como proceso aparte (ingesta diaria)
- [ ] Caché Redis TTL 24h + invalidación tras ingesta

### Épica 4 — API de búsqueda y comparativa
- [ ] `POST /busquedas` (cache hit/miss)
- [ ] `GET /busquedas/{id}` polling (estado + progreso)
- [ ] `GET /comparar` con orden y filtros (lectura desde RO)
- [ ] Cálculo determinista €/L y ranking en dominio
- [ ] Rate limit en Caddy

### Épica 5 — Frontend: flujo principal
- [ ] Layout minimalista + menú lateral colapsable
- [ ] Hero buscador + selector SVG de cadenas
- [ ] Flujo hero → resultados + barra de progreso (solo cache miss)
- [ ] Cards de producto (logo, ranking, imagen clicable, nombre, €, €/kg-L)
- [ ] Ficha producto + histórico de precios
- [ ] i18n base (`locales/es.json` + `t()`)

### Épica 6 — Perfil y listas
- [ ] Página perfil + `PATCH /me`
- [ ] CRUD listas (`/listas`, `/listas/{id}`)
- [ ] Añadir producto a lista desde card
- [ ] Caso de uso `CalcularAhorroLista` (A + C)
- [ ] Vista lista: items, coste total, % A, % C

### Épica 7 — Calidad y operación
- [ ] Postgres primario + réplica (compose dev)
- [ ] Backups + Sentry + UptimeRobot
- [ ] Métricas de ingesta (% verificado, motivos)
- [ ] Manifiestos K8s/OpenShift (plantilla)
- [ ] ADRs en `decisions.md`

### Épica 8 — Escala (post-MVP)
- [ ] Más cadenas y productos
- [ ] Separar worker a otro contenedor/VPS
- [ ] Evaluar RQ/Celery, réplicas, balanceo
- [ ] i18n completo (en, otros)

---

## 9. Decisiones de producto cerradas

| Decisión | Valor |
|----------|-------|
| % de ahorro | A + C (vs. cadena más cara + vs. cesta óptima) |
| Orden por defecto | Precio unitario (€), cambiable a €/kg-L |
| Filtros MVP | Stock, rango precio, marca, categoría |
| Ubicación | Afecta a precios (provincia → nacional → no disponible) |
| Idioma MVP | Español, i18n preparado |
| Caché búsquedas | TTL 24h, clave con provincia |
| Histórico precios | Incluido en MVP |
| Barra de progreso | Polling cada 1–2 s |
| Entornos | dev + prod separados |

---

## 10. Restricciones y penalizaciones

- **PENALIZACIÓN GRAVE**: secretos a fuego en código (API keys, passwords, nombres propios, tokens). Bloqueante en revisión.
- **Prohibido** en MVP: Kubernetes desplegado, microservicios, Kafka/RabbitMQ, Elasticsearch, auth con contraseñas propias.
- **Obligatorio**: SOLID, baja complejidad ciclomática, desacoplamiento, stateless, 12-factor.
- **Obligatorio**: dos entornos (dev/prod), contenedores Docker, portabilidad K8s/OpenShift.
- **Obligatorio**: BBDD replicada (RW/RO), migraciones como job separado.

---

## 11. Criterios de aceptación del MVP

El MVP se considera completado cuando:

1. Un usuario puede autenticarse con Google o Microsoft.
2. Puede buscar un producto, seleccionar cadenas y ver resultados en cards con todos los campos requeridos.
3. La barra de progreso aparece solo en cache miss.
4. Puede cambiar orden y filtros sin relanzar búsqueda.
5. Puede ver el histórico de precios de un producto.
6. Puede crear una lista, añadir productos y ver coste total + % A + % C.
7. Puede editar su perfil y provincia; los precios se ajustan a su ubicación.
8. Todo funciona en dev con datos de prueba y en prod con datos reales.
9. No hay secretos en el repo (gitleaks pasa en CI).
10. La API responde en `/health/ready` con RW, RO y Redis OK.

---

## 12. Próximos pasos para OpenCode

1. Leer este documento como contexto maestro.
2. Ejecutar Épica 0 completa (compose + Dockerfiles + env + CI).
3. Validar `docker compose up` en dev.
4. Ejecutar Épica 2 (esquema + migraciones + seed).
5. Continuar por orden de épicas, marcando issues completados.
6. Registrar decisiones nuevas en `decisions.md`.

**Regla para OpenCode**: ante ambigüedad, consultar este documento. Si la ambigüedad persiste, preguntar antes de implementar. Nunca hardcodear secretos ni saltarse los criterios de aceptación.

---
