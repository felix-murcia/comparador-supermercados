# BACKLOG.md

**Propósito**: Lista ejecutable de tareas del proyecto, organizada por épicas y ordenada por dependencias. OpenCode debe consultar este archivo antes de empezar cualquier tarea y marcarla como completada al terminarla.

**Fuente de verdad de requisitos**: `docs/PLAN.md`
**Reglas de ejecución**: `AGENTS.md`
**Convenciones**: `docs/CONVENTIONS.md`
**Decisiones**: `docs/decisions.md`

**Última actualización**: 2026-10-19
**Estado global**: 🟡 En desarrollo (Épica 0 en curso — 6/8)

---

## Leyenda

| Símbolo | Significado |
|---------|-------------|
| `[ ]` | Pendiente |
| `[~]` | En progreso |
| `[x]` | Completada |
| `[!]` | Bloqueada |
| 🔴 | Crítica (bloquea otras tareas) |
| 🟡 | Alta |
| 🟢 | Media |
| ⚪ | Baja |

**Estimación**: `d` = días de desarrollo a tiempo completo (1d ≈ 6h efectivas).

**Regla de dependencias**: una tarea no se empieza hasta que todas sus dependencias estén `[x]`. Si una dependencia está `[!]`, la tarea también pasa a `[!]`.

---

## Resumen por épica

| Épica | Tareas | Estimación | Estado |
|-------|--------|-----------|--------|
| 0 — Fundación | 8 | 8d | 🟡 En curso (6/8) |
| 1 — Autenticación | 5 | 6d | ⚪ Pendiente |
| 2 — Modelo de datos | 6 | 7d | ⚪ Pendiente |
| 3 — Ingesta | 8 | 12d | ⚪ Pendiente |
| 4 — API búsqueda/comparativa | 6 | 8d | ⚪ Pendiente |
| 5 — Frontend flujo principal | 8 | 13d | ⚪ Pendiente |
| 6 — Perfil y listas | 6 | 11d | ⚪ Pendiente |
| 7 — Calidad y operación | 6 | 7d | ⚪ Pendiente |
| 8 — Escala (post-MVP) | 4 | — | ⚪ Futuro |
| **Total MVP** | **53** | **~72d** | |

> ~72 días de desarrollo efectivo ≈ 3,5 meses a tiempo completo, ~7 meses a medio tiempo.

---

## Épica 0 — Fundación

**Objetivo**: repo reproducible, entorno dev funcional con `docker compose up`, CI verde, deploy inicial en VPS.

**Criterio de salida de la épica**: `docker compose -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml up` levanta Postgres primario + réplica + Redis + API + web + Caddy sin errores, y CI pasa en `main`.

---

### [x] T0.1 — Crear estructura del monorepo 🔴

- **Depende de**: —
- **Estimación**: 0.5d
- **Descripción**: Crear carpetas `api/`, `web/`, `infra/`, `docs/` con `.gitkeep` donde haga falta, según `CONVENTIONS.md` sección 2.
- **Aceptación**:
  - [x] Estructura coincide con `CONVENTIONS.md` §2.1 y §2.2.
  - [x] `README.md` raíz con descripción y enlaces a `docs/`.
  - [x] `.gitignore` con `.env*`, `node_modules/`, `__pycache__/`, `.venv/`, `*.pyc`, `.next/`, `dist/`, `*.pem`, `*.key`, `secrets/`.
- **Notas**: no crear archivos vacíos innecesarios. `.gitkeep` solo en carpetas que deban existir sin contenido.

---

### [x] T0.2 — `.env.example` completo 🔴

- **Depende de**: T0.1
- **Estimación**: 0.5d
- **Descripción**: Crear `.env.example` con todas las variables definidas en `PLAN.md` §2.2, con valores vacíos y comentarios.
- **Aceptación**:
  - [x] Incluye: `APP_ENV`, `APP_SECRET_KEY`, `POSTGRES_*`, `DATABASE_URL_RW`, `DATABASE_URL_RO`, `REDIS_URL`, `CACHE_TTL_SEGUNDOS`, `GOOGLE_*`, `MICROSOFT_*`, `LLM_*`, `SENTRY_DSN`, `LOG_LEVEL`, `RATE_LIMIT_*`.
  - [x] Comentarios explican cómo generar secretos (`openssl rand -hex 32`).
  - [x] No hay ningún valor real, solo placeholders vacíos.
- **Notas**: este archivo es la fuente de verdad de variables. Cualquier variable nueva debe añadirse aquí en el mismo PR.

---

### [x] T0.3 — `docker-compose.base.yml` + dev + prod 🔴

- **Depende de**: T0.1, T0.2
- **Estimación**: 2d
- **Descripción**: Crear tres archivos compose según `PLAN.md` §2.3.
- **Aceptación**:
  - [x] `base.yml`: servicios `postgres-primary`, `postgres-replica`, `redis`, `api`, `worker`, `scheduler`, `web`, `caddy`. Volúmenes nombrados. Healthchecks en `postgres-primary` y `api`.
  - [x] `dev.yml`: hot-reload (volúmenes montados), `APP_ENV=dev`, sin TLS, logs verbose, puerto de Postgres expuesto para debugging.
  - [x] `prod.yml`: imágenes build, `APP_ENV=prod`, TLS en Caddy, logs JSON, sin puertos de BD expuestos.
  - [x] `docker compose -f base -f dev config` valida sin errores.
- **Notas**: `postgres-replica` requiere script de inicialización (`infra/postgres/init-replica.sh`) con `pg_basebackup` desde primario.

---

### [x] T0.4 — Dockerfiles de api, worker, scheduler, web 🔴

- **Depende de**: T0.1
- **Estimación**: 1d
- **Descripción**: Multi-stage builds. `api`, `worker`, `scheduler` comparten imagen base (mismo código, distinto `CMD`). `web` imagen propia.
- **Aceptación**:
  - [x] `api/Dockerfile` multi-stage: builder (deps) + runtime (slim). Usuario no-root.
  - [x] `worker` y `scheduler` reutilizan la imagen de `api` con distinto `command`.
  - [x] `web/Dockerfile` multi-stage para Next.js (standalone output).
  - [x] Imágenes < 500 MB.
  - [x] `HEALTHCHECK` en `api`.
- **Notas**: no instalar dependencias de desarrollo en runtime.

---

### [x] T0.5 — Esqueleto FastAPI + Next.js 🔴

- **Depende de**: T0.4
- **Estimación**: 1d
- **Descripción**: `api/src/main.py` con `/health/live` y `/health/ready`. `web/src/app/page.tsx` con "Hola". `config.py` con `pydantic-settings` leyendo `.env`.
- **Aceptación**:
  - [x] `GET /health/live` → `{"status": "ok"}`.
  - [x] `GET /health/ready` comprueba RW, RO y Redis; devuelve 503 si alguno falla.
  - [x] `web` responde en `:3000` con página mínima.
  - [x] `settings` carga todas las variables de `.env.example` sin error.
- **Notas**: `health/ready` es lo que K8s usará como readiness probe. No lo dejes para después.

---

### [x] T0.6 — Caddyfile 🔴

- **Depende de**: T0.5
- **Estimación**: 0.5d
- **Descripción**: Configurar Caddy como reverse proxy a `api:8000` y `web:3000`, con TLS automático en prod y HTTP en dev.
- **Aceptación**:
  - [x] En dev: `http://localhost` → web; `http://localhost/api/*` → api.
  - [x] En prod: TLS automático con dominio configurado en `.env`.
  - [x] Rate limit básico en `/api/v1/busquedas` (`RATE_LIMIT_BUSQUEDAS_POR_MINUTO`).
  - [x] Compresión gzip/zstd activa.
- **Notas**: La imagen oficial de Caddy no incluye rate limit; se compila una propia con `mholt/caddy-ratelimit` (ADR-011). `/api/auth/*` se enruta a Next.js para no romper Auth.js.

---

### [ ] T0.7 — CI en GitHub Actions 🔴

- **Depende de**: T0.5
- **Estimación**: 1d
- **Descripción**: Workflow que en cada PR ejecute lint, tests, build, gitleaks y trivy.
- **Aceptación**:
  - [ ] Job `api-lint`: `ruff check`, `ruff format --check`, `mypy`.
  - [ ] Job `api-test`: `pytest` con cobertura (falla si dominio < 80%).
  - [ ] Job `web-lint`: `eslint`, `tsc --noEmit`.
  - [ ] Job `web-test`: `npm test`.
  - [ ] Job `security`: `gitleaks` + `trivy` sobre imágenes build.
  - [ ] Job `compose-validate`: `docker compose config` de base+dev.
  - [ ] CI verde en `main`.

---

### [ ] T0.8 — Deploy inicial en VPS 🟡

- **Depende de**: T0.3, T0.6, T0.7
- **Estimación**: 1.5d
- **Descripción**: VPS con Docker, repo clonado, `docker compose -f base -f prod up -d`. Documentar en `README.md`.
- **Aceptación**:
  - [ ] VPS accesible por HTTPS con dominio real.
  - [ ] `/health/ready` responde OK desde fuera.
  - [ ] `README.md` con pasos de deploy reproducibles.
  - [ ] Backup diario de Postgres configurado (cron en VPS o script).
- **Notas**: no commitear `.env` de prod. Usar `docker secret` o `.env` con permisos `600`.

---

## Épica 1 — Autenticación

**Objetivo**: login con Google y Microsoft, sesión validada en backend.

**Criterio de salida**: un usuario puede entrar con Google y con Microsoft, `GET /v1/me` devuelve su perfil, y el frontend muestra/oculta UI según sesión.

---

### [ ] T1.1 — Configurar Auth.js con Google y Microsoft 🟡

- **Depende de**: T0.5
- **Estimación**: 1.5d
- **Descripción**: `web/src/lib/auth.ts` con providers Google y Microsoft Entra ID. Callback a `/api/auth/callback/{provider}`.
- **Aceptación**:
  - [ ] Login con Google funciona en dev.
  - [ ] Login con Microsoft funciona en dev.
  - [ ] Sesión JWT firmada, TTL configurable.
  - [ ] Variables en `.env` (`GOOGLE_CLIENT_ID`, etc.).
- **Notas**: crear apps OAuth en Google Cloud Console y Azure Portal. Documentar en `README.md`.

---

### [ ] T1.2 — Tabla `usuarios` + migración 🟡

- **Depende de**: T2.1
- **Estimación**: 0.5d
- **Descripción**: Migración Alembic con tabla `usuarios` según `PLAN.md` §6.
- **Aceptación**:
  - [ ] Campos: `id`, `provider`, `provider_id`, `email`, `nombre`, `provincia`, `avatar_url`, `creado_en`.
  - [ ] `UNIQUE (provider, provider_id)`.
  - [ ] Índice en `email`.

---

### [ ] T1.3 — `GET /v1/me` + upsert de usuario 🟡

- **Depende de**: T1.1, T1.2
- **Estimación**: 1d
- **Descripción**: Endpoint que valida JWT y devuelve perfil. Si el usuario no existe, lo crea (upsert por `provider` + `provider_id`).
- **Aceptación**:
  - [ ] `GET /v1/me` con JWT válido → 200 con perfil.
  - [ ] Sin JWT → 401.
  - [ ] JWT inválido → 401.
  - [ ] Primer login crea fila en `usuarios`.
  - [ ] Test de integración con BD real.

---

### [ ] T1.4 — Middleware de sesión en Next.js 🟡

- **Depende de**: T1.1
- **Estimación**: 1d
- **Descripción**: Rutas `(app)/*` protegidas. Redirección a `/login` si no hay sesión. Rutas `(auth)/*` públicas.
- **Aceptación**:
  - [ ] Usuario no logueado en `/buscar` → redirect a `/login`.
  - [ ] Usuario logueado en `/login` → redirect a `/`.
  - [ ] `session` accesible en Server Components.

---

### [ ] T1.5 — Pantalla de login 🟡

- **Depende de**: T1.1
- **Estimación**: 1d
- **Descripción**: Página `/login` minimalista con dos botones: "Continuar con Google" y "Continuar con Microsoft". Logos SVG.
- **Aceptación**:
  - [ ] Ambos botones inician flujo OAuth.
  - [ ] Estilo minimalista tipo Google.
  - [ ] Strings en `locales/es.json` (`login.google`, `login.microsoft`).
  - [ ] Accesible por teclado.

---

## Épica 2 — Modelo de datos

**Objetivo**: esquema completo, migraciones, repositorios, engines RW/RO, seed dev.

**Criterio de salida**: `alembic upgrade head` crea todas las tablas; seed inserta 3 cadenas y 100 productos; repositorios tienen tests; routing RW/RO funciona.

---

### [ ] T2.1 — Esquema SQL inicial 🔴

- **Depende de**: T0.3
- **Estimación**: 1.5d
- **Descripción**: Migración Alembic con tablas de `PLAN.md` §6: `cadenas`, `productos`, `productos_cadena`, `precios`, `busquedas`, `listas`, `lista_items`.
- **Aceptación**:
  - [ ] Todas las columnas, tipos, constraints e índices de `PLAN.md` §6.
  - [ ] `pg_trgm` activado; índice GIN en `productos.nombre`.
  - [ ] Índice `(producto_cadena_id, fecha_consulta DESC)` en `precios`.
  - [ ] Constraint `chk_precios_ambito_provincia`.
  - [ ] `alembic upgrade head` limpio desde BD vacía.
  - [ ] `alembic downgrade base` limpio.

---

### [ ] T2.2 — Engines RW/RO + routing 🔴

- **Depende de**: T2.1
- **Estimación**: 1d
- **Descripción**: `api/src/adaptadores/persistencia/engines.py` con `engine_rw` y `engine_ro`. Casos de uso de lectura usan RO; escritura usa RW.
- **Aceptación**:
  - [ ] Dos `AsyncEngine` configurados desde `DATABASE_URL_RW` y `DATABASE_URL_RO`.
  - [ ] `get_session_ro()` y `get_session_rw()` como dependencias de FastAPI.
  - [ ] Test que verifica que una escritura va a RW y una lectura a RO.
  - [ ] Sticky post-escritura: tras un `POST`, las lecturas del mismo usuario van a RW durante N segundos (configurable).

---

### [ ] T2.3 — Repositorios base + tests 🟡

- **Depende de**: T2.2
- **Estimación**: 2d
- **Descripción**: Implementaciones SQLAlchemy de los puertos definidos en `api/src/puertos/repositorios.py`.
- **Aceptación**:
  - [ ] `RepositorioProductos`, `RepositorioPrecios`, `RepositorioListas`, `RepositorioBusquedas`.
  - [ ] Métodos de lectura usan RO, de escritura RW.
  - [ ] Tests de integración con Postgres de test.
  - [ ] Cobertura > 80% en repositorios.

---

### [ ] T2.4 — Seed dev con datos de prueba 🟡

- **Depende de**: T2.1
- **Estimación**: 1d
- **Descripción**: Script `api/scripts/seed.py` que inserta 3 cadenas (DIA, Carrefour, Mercadona) y 100 productos de muestra.
- **Aceptación**:
  - [ ] 3 cadenas con slug y logo SVG path.
  - [ ] 100 productos con nombre, marca, categoría, formato, litros_o_kg.
  - [ ] `productos_cadena` con URL de producto.
  - [ ] `precios` con al menos 1 precio por producto/cadena, estado `verificado`, ámbito `nacional`.
  - [ ] Idempotente.

---

### [ ] T2.5 — Puertos de ingesta (Productor, Verificador, Cache) 🟡

- **Depende de**: T0.5
- **Estimación**: 1d
- **Descripción**: `Protocol` de Python en `api/src/puertos/` con contratos de productor, verificador y cache.
- **Aceptación**:
  - [ ] `Productor.producir(query, cadena) -> dict`.
  - [ ] `Verificador.verificar(candidato) -> (estado, motivos)`.
  - [ ] `Cache.get(key)`, `Cache.set(key, value, ttl)`, `Cache.invalidar_prefijo(prefijo)`.
  - [ ] Tests de contrato con implementaciones fake.

---

### [ ] T2.6 — Value Objects y reglas de dominio 🟢

- **Depende de**: T0.5
- **Estimación**: 0.5d
- **Descripción**: `Formato`, `Precio`, `Provincia` como `@dataclass(frozen=True)`. Función `calcular_precio_por_litro`.
- **Aceptación**:
  - [ ] `Formato.a_litros_o_kg()` maneja L, ml, kg, g.
  - [ ] `calcular_precio_por_litro` devuelve `None` si litros <= 0.
  - [ ] Redondeo a 4 decimales.
  - [ ] Cobertura 100% en estos módulos.

---

## Épica 3 — Ingesta

**Objetivo**: pipeline productor → verificador → BD, con worker, scheduler y caché.

**Criterio de salida**: un job de búsqueda end-to-end inserta precios verificados en BD; scheduler diario invalida caché; caché hit/miss medido.

---

### [ ] T3.1 — Implementación `LLMProductor` 🔴

- **Depende de**: T2.5
- **Estimación**: 2d
- **Descripción**: Adaptador que llama al LLM con el prompt de `PLAN.md` §7 y parsea JSON estricto.
- **Aceptación**:
  - [ ] Prompt en constante separada.
  - [ ] Respuesta parseada a `dict` con campos obligatorios.
  - [ ] Si el LLM devuelve texto no-JSON → error controlado, no crash.
  - [ ] `url_fuente` obligatoria cuando `encontrado=true`.
  - [ ] Tests con respuestas mockeadas (válida, inválida, no encontrado).
  - [ ] Retry con backoff exponencial ante errores 5xx.

---

### [ ] T3.2 — Implementación `Verificador` (fetch + reglas) 🔴

- **Depende de**: T2.5
- **Estimación**: 2d
- **Descripción**: Adaptador que hace `GET` a `url_fuente` y aplica las reglas del validador de `PLAN.md` §7.
- **Aceptación**:
  - [ ] Fetch con timeout 10 s y User-Agent de navegador.
  - [ ] Comprueba precio en HTML (tolerante a `,` y `.`).
  - [ ] Comprueba coherencia €/L vs. formato (±5%).
  - [ ] Comprueba desviación vs. último precio conocido (>30% → `sospechoso`).
  - [ ] Devuelve `(estado, motivos)` con estados `verificado | sospechoso | rechazado`.
  - [ ] Tests con HTML real cacheado en `tests/fixtures/`.

---

### [ ] T3.3 — Caso de uso `BuscarProducto` 🔴

- **Depende de**: T3.1, T3.2, T2.3
- **Estimación**: 1.5d
- **Descripción**: Orquesta productor → verificador → repositorio con reintento acotado (máx. 3).
- **Aceptación**:
  - [ ] Máximo 3 pasadas.
  - [ ] Si `verificado` → guarda en BD y devuelve éxito.
  - [ ] Si `rechazado` con motivo `agente_no_encontro` → no reintenta, devuelve fallo.
  - [ ] Si `sospechoso` tras 3 pasadas → guarda con estado `sospechoso`.
  - [ ] Tests con productor/verificador/repo mockeados.

---

### [ ] T3.4 — Cola de jobs en Postgres + worker 🔴

- **Depende de**: T3.3
- **Estimación**: 2d
- **Descripción**: Worker que hace polling a `busquedas` con `SKIP LOCKED` y ejecuta `BuscarProducto`.
- **Aceptación**:
  - [ ] `SELECT ... FOR UPDATE SKIP LOCKED` sobre `busquedas WHERE estado='pendiente'`.
  - [ ] Actualiza `estado` (`en_progreso` → `completada`/`fallida`) y `progreso` (0–100).
  - [ ] Si el worker cae, el job vuelve a `pendiente` tras timeout.
  - [ ] `api/src/worker.py` como punto de entrada (`python -m src.worker`).
  - [ ] Tests de concurrencia: 2 workers no procesan el mismo job.

---

### [ ] T3.5 — Scheduler diario 🟡

- **Depende de**: T3.4
- **Estimación**: 1d
- **Descripción**: Proceso `api/src/scheduler.py` que lanza ingesta diaria e invalida caché tras completarla.
- **Aceptación**:
  - [ ] Cron interno (APScheduler) a las 03:00 Europe/Madrid.
  - [ ] Encola jobs de ingesta para productos activos.
  - [ ] Al terminar, `Cache.invalidar_prefijo("v1:")`.
  - [ ] Logs de inicio/fin con duración.
  - [ ] Proceso separado, no dentro de la API.

---

### [ ] T3.6 — Implementación `RedisCache` 🟡

- **Depende de**: T2.5
- **Estimación**: 1d
- **Descripción**: Adaptador de caché con TTL, clave versionada (`v1:` + hash).
- **Aceptación**:
  - [ ] `get`, `set` con TTL, `invalidar_prefijo` (por versión, sin `SCAN`).
  - [ ] Serialización JSON.
  - [ ] Si Redis cae, `get` devuelve `None` (no rompe la app).
  - [ ] Tests con Redis de test.

---

### [ ] T3.7 — Cálculo de `cache_key` 🟡

- **Depende de**: T3.6
- **Estimación**: 0.5d
- **Descripción**: Función que genera hash SHA-256 de `(query_normalizada, cadenas_ordenadas, orden, filtros, provincia)`.
- **Aceptación**:
  - [ ] Normalización de query: lowercase, sin tildes, sin espacios múltiples.
  - [ ] Cadenas ordenadas alfabéticamente.
  - [ ] Filtros serializados de forma canónica.
  - [ ] Tests: misma búsqueda → mismo hash; distinta provincia → distinto hash.

---

### [ ] T3.8 — Métricas de ingesta 🟢

- **Depende de**: T3.4
- **Estimación**: 1d
- **Descripción**: Contadores en logs/BD: `% verificado`, `% sospechoso`, `% rechazado`, motivos más frecuentes.
- **Aceptación**:
  - [ ] Tabla `ingesta_metricas` o logs estructurados consultables.
  - [ ] Endpoint interno `GET /v1/_metrics/ingesta` (protegido).
  - [ ] Documentado en `README.md` cómo consultarlas.

---

## Épica 4 — API búsqueda y comparativa

**Objetivo**: endpoints que el frontend consume para buscar y comparar.

**Criterio de salida**: `POST /v1/busquedas` devuelve cache hit o job_id; `GET /v1/busquedas/{id}` devuelve progreso; `GET /v1/comparar` devuelve resultados con orden y filtros.

---

### [ ] T4.1 — `POST /v1/busquedas` 🔴

- **Depende de**: T3.3, T3.6, T3.7
- **Estimación**: 1d
- **Descripción**: Endpoint que calcula `cache_key`, consulta Redis, y si no hay hit, encola job.
- **Aceptación**:
  - [ ] Body: `{ query, cadenas, orden, filtros, provincia? }`.
  - [ ] Cache hit → `{ job_id: null, cache_hit: true, resultados }`.
  - [ ] Cache miss → `{ job_id, cache_hit: false }`.
  - [ ] Sin JWT → 401.
  - [ ] Rate limit aplicado.
  - [ ] Tests: hit, miss, sin auth, rate limit.

---

### [ ] T4.2 — `GET /v1/busquedas/{id}` 🔴

- **Depende de**: T3.4
- **Estimación**: 1d
- **Descripción**: Endpoint de polling que devuelve estado + progreso + resultados parciales.
- **Aceptación**:
  - [ ] `{ estado, progreso, resultados_parciales, completado_en? }`.
  - [ ] Estados: `pendiente | en_progreso | completada | fallida`.
  - [ ] Solo el dueño del job puede consultarlo (o admin).
  - [ ] Tests de transición de estados.

---

### [ ] T4.3 — `GET /v1/comparar` 🔴

- **Depende de**: T2.3, T2.6
- **Estimación**: 2d
- **Descripción**: Endpoint que devuelve resultados con orden y filtros aplicados en SQL (desde RO).
- **Aceptación**:
  - [ ] Query params: `q`, `cadenas`, `orden` (`precio_unitario|precio_kg_l|relevancia`), `precio_min`, `precio_max`, `marca`, `categoria`, `solo_con_stock`, `provincia`.
  - [ ] Orden por defecto: `precio_unitario`.
  - [ ] Resolución de precio por provincia (ADR-009).
  - [ ] Paginación `limit`/`offset`.
  - [ ] Tests: cada filtro, cada orden, fallback provincia→nacional.

---

### [ ] T4.4 — Cálculo determinista €/L y ranking 🟡

- **Depende de**: T2.6
- **Estimación**: 1d
- **Descripción**: Función de dominio que calcula €/L y posición en ranking.
- **Aceptación**:
  - [ ] Redondeo a 4 decimales en BD, 2 en UI.
  - [ ] Ranking estable (desempate por nombre).
  - [ ] Tests con casos límite (formato desconocido, precio 0, etc.).

---

### [ ] T4.5 — Cache de respuestas de comparación 🟢

- **Depende de**: T4.3, T3.6
- **Estimación**: 0.5d
- **Descripción**: Cachear `GET /v1/comparar` con TTL corto (5 min) en Redis.
- **Aceptación**:
  - [ ] Clave incluye todos los query params + provincia.
  - [ ] TTL 300 s.
  - [ ] Invalidación tras ingesta.

---

### [ ] T4.6 — Exception handlers globales 🟡

- **Depende de**: T4.1
- **Estimación**: 0.5d
- **Descripción**: Traducir errores de dominio a HTTP con `{ code, message }`.
- **Aceptación**:
  - [ ] `ProductoNoEncontradoError` → 404.
  - [ ] `UsuarioNoAutorizadoError` → 403.
  - [ ] `RateLimitError` → 429.
  - [ ] Errores inesperados → 500 con Sentry, sin stack trace al cliente.

---

## Épica 5 — Frontend flujo principal

**Objetivo**: hero → resultados, cards, ficha producto, histórico, i18n.

**Criterio de salida**: usuario busca, ve barra de progreso (solo miss), ve cards con todos los campos, cambia orden/filtros, abre ficha con histórico.

---

### [ ] T5.1 — Layout minimalista + menú lateral 🔴

- **Depende de**: T1.4
- **Estimación**: 2d
- **Descripción**: Layout base con header, menú lateral colapsable, área de contenido. Estilo tipo Google.
- **Aceptación**:
  - [ ] Menú colapsable con enlaces: Buscar, Listas, Perfil.
  - [ ] Responsive (móvil: menú overlay).
  - [ ] Accesible por teclado.
  - [ ] Tailwind con tokens en `tailwind.config.ts`.

---

### [ ] T5.2 — Hero buscador + selector SVG cadenas 🔴

- **Depende de**: T5.1
- **Estimación**: 2d
- **Descripción**: Página `/` con buscador centrado, selector de cadenas con logos SVG, botón "Comparar".
- **Aceptación**:
  - [ ] Logos SVG en `public/logos/` (DIA, Carrefour, Mercadona).
  - [ ] Selección múltiple con estado visual.
  - [ ] Botón "Comparar" deshabilitado si no hay query o cadenas.
  - [ ] Enter en el input lanza búsqueda.

---

### [ ] T5.3 — Flujo hero → resultados + barra de progreso 🔴

- **Depende de**: T5.2, T4.1, T4.2
- **Estimación**: 2d
- **Descripción**: Al comparar, si cache hit → resultados instantáneos. Si miss → barra de progreso con polling cada 1–2 s.
- **Aceptación**:
  - [ ] Cache hit: transición directa, sin barra.
  - [ ] Cache miss: barra animada con % real del job.
  - [ ] Al completar, transición a vista resultados (buscador arriba, flecha volver).
  - [ ] Flecha volver resetea a hero.
  - [ ] Re-búsqueda desde resultados mantiene filtros en URL.

---

### [ ] T5.4 — Cards de producto 🔴

- **Depende de**: T5.3
- **Estimación**: 2d
- **Descripción**: Componente `CardProducto` con logo, ranking, imagen clicable, nombre, €, €/kg-L.
- **Aceptación**:
  - [ ] Imagen clicable → `url_producto` en nueva pestaña (`rel="noopener"`).
  - [ ] Ranking visible (posición).
  - [ ] € formateado con `Intl.NumberFormat("es-ES")`.
  - [ ] €/kg-L con 2 decimales.
  - [ ] Botón "Añadir a lista" (placeholder hasta Épica 6).
  - [ ] Accesible: `alt` en imagen, foco visible.

---

### [ ] T5.5 — Selector de orden y filtros 🟡

- **Depende de**: T5.3
- **Estimación**: 1.5d
- **Descripción**: Panel de filtros (stock, rango precio, marca, categoría) y selector de orden. Cambios no relanzan búsqueda (datos ya en cliente).
- **Aceptación**:
  - [ ] Filtros aplicados en cliente sobre resultados ya cargados.
  - [ ] Estado reflejado en URL (`?orden=precio_kg_l&marca=...`).
  - [ ] "Limpiar filtros" restaura estado inicial.
  - [ ] Contador de resultados visibles.

---

### [ ] T5.6 — Ficha de producto + histórico 🟡

- **Depende de**: T5.4, T4.3
- **Estimación**: 2d
- **Descripción**: Página `/producto/[slug]` con detalle y gráfica de histórico de precios.
- **Aceptación**:
  - [ ] SSR para SEO.
  - [ ] Gráfica de histórico (Recharts) con precios por cadena.
  - [ ] Selector de rango temporal (1M, 3M, 6M, 1A).
  - [ ] Tabla de precios actuales por cadena.
  - [ ] Botón "Añadir a lista".

---

Aquí tienes la continuación exacta desde T5.7 hasta el final.

---

### [ ] T5.7 — i18n base 🟢

- **Depende de**: T5.1
- **Estimación**: 1d
- **Descripción**: `locales/es.json` con todos los strings. Función `t(key)` en `lib/i18n.ts`.
- **Aceptación**:
  - [ ] Todos los strings visibles en `locales/es.json`.
  - [ ] `t("clave")` funciona en Server y Client Components.
  - [ ] Sin strings hardcodeados en JSX (revisión manual + lint rule).
  - [ ] Estructura preparada para añadir `en.json` sin refactor.

---

### [ ] T5.8 — Accesibilidad y pulido visual 🟢

- **Depende de**: T5.4, T5.5, T5.6
- **Estimación**: 1.5d
- **Descripción**: Auditoría de accesibilidad (WCAG AA) y pulido del estilo minimalista.
- **Aceptación**:
  - [ ] Contraste mínimo 4.5:1 en texto normal.
  - [ ] Navegación completa por teclado con foco visible.
  - [ ] `alt` descriptivo en todas las imágenes.
  - [ ] `label` asociado a cada input.
  - [ ] Lighthouse Accessibility ≥ 95.
  - [ ] Sin sombras ni gradientes innecesarios (estilo Google).

---

## Épica 6 — Perfil y listas

**Objetivo**: perfil editable, CRUD de listas, añadir productos, cálculo de ahorro A + C.

**Criterio de salida**: usuario edita perfil y provincia; crea lista; añade productos; ve coste total, % A y % C; los precios se ajustan a su provincia.

---

### [ ] T6.1 — `PATCH /v1/me` + página de perfil 🟡

- **Depende de**: T1.3
- **Estimación**: 1.5d
- **Descripción**: Endpoint para actualizar nombre, email y provincia. Página `/perfil` con formulario.
- **Aceptación**:
  - [ ] `PATCH /v1/me` acepta `nombre`, `provincia`.
  - [ ] Validación de provincia contra lista de provincias españolas.
  - [ ] Página `/perfil` con formulario y guardado.
  - [ ] Al guardar provincia, se invalida caché del usuario.
  - [ ] Tests: actualización válida, provincia inválida, sin auth.

---

### [ ] T6.2 — CRUD listas (`/v1/listas`) 🟡

- **Depende de**: T2.3, T1.3
- **Estimación**: 2d
- **Descripción**: Endpoints para crear, listar, obtener, renombrar y borrar listas.
- **Aceptación**:
  - [ ] `POST /v1/listas` → crea lista.
  - [ ] `GET /v1/listas` → lista del usuario autenticado.
  - [ ] `GET /v1/listas/{id}` → detalle con items.
  - [ ] `PATCH /v1/listas/{id}` → renombrar.
  - [ ] `DELETE /v1/listas/{id}` → borrar (cascade en items).
  - [ ] Solo el dueño puede acceder (403 si no).
  - [ ] Tests: CRUD completo + autorización.

---

### [ ] T6.3 — Añadir/quitar items de lista 🟡

- **Depende de**: T6.2
- **Estimación**: 1.5d
- **Descripción**: Endpoints para añadir producto a lista (con cadena de compra y cantidad) y quitarlo.
- **Aceptación**:
  - [ ] `POST /v1/listas/{id}/items` con `{ producto_id, cadena_compra_id, cantidad }`.
  - [ ] `DELETE /v1/listas/{id}/items/{item_id}`.
  - [ ] `PATCH /v1/listas/{id}/items/{item_id}` para cambiar cantidad.
  - [ ] `precio_snapshot` guardado al añadir (precio del momento).
  - [ ] Tests: añadir, quitar, cambiar cantidad, producto inexistente.

---

### [ ] T6.4 — Caso de uso `CalcularAhorroLista` (A + C) 🔴

- **Depende de**: T6.3, T4.4
- **Estimación**: 3d
- **Descripción**: Cálculo de coste total por cadena, % A y % C según ADR-008.
- **Aceptación**:
  - [ ] `coste_cadena` por cada cadena seleccionada (solo productos disponibles).
  - [ ] `% A = (coste_mas_cara - coste_cadena) / coste_mas_cara`.
  - [ ] `coste_optimo = sum(min(precio entre cadenas))`.
  - [ ] `coste_mixta_real = sum(precio donde el usuario compró)`.
  - [ ] `% C = (coste_mixta_real - coste_optimo) / coste_mixta_real`.
  - [ ] Productos no disponibles se excluyen con aviso.
  - [ ] Si solo 1 cadena seleccionada, % A = `null` (UI muestra "—").
  - [ ] Si `coste_mixta_real == 0`, % C = `null`.
  - [ ] Tests con casos: todos disponibles, alguno no disponible, una sola cadena, lista vacía.

---

### [ ] T6.5 — Endpoint `GET /v1/listas/{id}/resumen` 🟡

- **Depende de**: T6.4
- **Estimación**: 1d
- **Descripción**: Endpoint que devuelve coste total, % A por cadena, % C y avisos.
- **Aceptación**:
  - [ ] Respuesta: `{ coste_total, por_cadena: [{ cadena, coste, porcentaje_a }], porcentaje_c, avisos }`.
  - [ ] Lectura desde RO.
  - [ ] Cache TTL corto (60 s).
  - [ ] Tests de contrato.

---

### [ ] T6.6 — Vista de lista en frontend 🟡

- **Depende de**: T6.2, T6.3, T6.5
- **Estimación**: 2d
- **Descripción**: Página `/listas/[id]` con items, coste total, % A y % C.
- **Aceptación**:
  - [ ] Lista de items con imagen, nombre, cadena, cantidad, precio.
  - [ ] Coste total destacado.
  - [ ] Tabla de % A por cadena.
  - [ ] % C con tooltip explicativo.
  - [ ] Botón "Añadir producto" (abre buscador en modal).
  - [ ] Edición de cantidad inline.
  - [ ] Eliminar item con confirmación.
  - [ ] Avisos visibles si hay productos no disponibles.

---

## Épica 7 — Calidad y operación

**Objetivo**: observabilidad, backups, plantillas K8s, ADRs, tests de integración.

**Criterio de salida**: Sentry y UptimeRobot activos; backups diarios verificados; plantillas K8s listas; ADRs actualizados; cobertura global ≥ 70%.

---

### [ ] T7.1 — Postgres primario + réplica en compose dev 🟡

- **Depende de**: T0.3, T2.2
- **Estimación**: 1d
- **Descripción**: Script `infra/postgres/init-replica.sh` con `pg_basebackup` y configuración de streaming replication.
- **Aceptación**:
  - [ ] Réplica arranca y sincroniza desde primario.
  - [ ] `pg_stat_replication` muestra la réplica en estado `streaming`.
  - [ ] Test: escritura en primario visible en réplica tras lag < 1 s.
  - [ ] Documentado en `README.md` cómo verificar.

---

### [ ] T7.2 — Backups + Sentry + UptimeRobot 🟡

- **Depende de**: T0.8
- **Estimación**: 1d
- **Descripción**: Backup diario de Postgres, Sentry en api y web, UptimeRobot monitorizando `/health/ready`.
- **Aceptación**:
  - [ ] Cron diario con `pg_dump` comprimido, retención 7 días.
  - [ ] Script de restauración documentado y probado.
  - [ ] Sentry captura errores 500 en api y errores de cliente en web.
  - [ ] UptimeRobot alerta si `/health/ready` falla 2 veces seguidas.
  - [ ] `SENTRY_DSN` en `.env.example`.

---

### [ ] T7.3 — Métricas de ingesta y dashboard interno 🟢

- **Depende de**: T3.8
- **Estimación**: 1d
- **Descripción**: Vista interna `/admin/metricas` (protegida) con % verificado, motivos de rechazo y duración de ingesta.
- **Aceptación**:
  - [ ] Solo accesible para usuario admin (lista blanca en `.env`).
  - [ ] Gráficas de últimos 7 días.
  - [ ] Tabla de motivos de rechazo más frecuentes.
  - [ ] Sin datos personales en métricas.

---

### [ ] T7.4 — Plantillas K8s/OpenShift 🟢

- **Depende de**: T0.4, T0.5
- **Estimación**: 2d
- **Descripción**: Manifiestos en `infra/k8s/` para Deployment, Service, Ingress, HPA, ConfigMap y Secret. **No desplegar aún.**
- **Aceptación**:
  - [ ] `api-deployment.yaml`, `worker-deployment.yaml`, `scheduler-cronjob.yaml`, `web-deployment.yaml`.
  - [ ] `postgres-cluster.yaml` (referencia a operador CloudNativePG).
  - [ ] `ingress.yaml` con TLS.
  - [ ] `hpa.yaml` para api y web.
  - [ ] `configmap.yaml` + `secret.example.yaml` (sin valores reales).
  - [ ] `kubectl apply --dry-run=client -f infra/k8s/` pasa sin errores.
  - [ ] Documentado en `README.md` como "futuro", no como despliegue activo.

---

### [ ] T7.5 — Tests de integración end-to-end 🟢

- **Depende de**: T4.1, T4.2, T4.3, T6.5
- **Estimación**: 1.5d
- **Descripción**: Suite de tests que cubre el flujo completo: login → búsqueda → comparar → añadir a lista → resumen.
- **Aceptación**:
  - [ ] Test E2E con `httpx` + BD de test + Redis de test.
  - [ ] Cubre cache hit y cache miss.
  - [ ] Cubre cálculo de % A y % C.
  - [ ] Cubre fallback provincia → nacional.
  - [ ] Ejecutado en CI.

---

### [ ] T7.6 — ADRs pendientes y revisión de documentación 🟢

- **Depende de**: —
- **Estimación**: 0.5d
- **Descripción**: Revisar y actualizar `docs/decisions.md` con decisiones tomadas durante el desarrollo. Actualizar `docs/PLAN.md` si cambió algo.
- **Aceptación**:
  - [ ] ADRs nuevos registrados (ej: elección de Recharts, estrategia de polling vs. SSE si cambió).
  - [ ] ADRs obsoletos marcados como `obsoleto` con referencia al nuevo.
  - [ ] `docs/PLAN.md` coherente con el estado real.
  - [ ] `README.md` actualizado con estado del proyecto.

---

## Épica 8 — Escala (post-MVP)

**Objetivo**: preparar el crecimiento más allá del MVP. **No se ejecuta hasta cerrar Épica 7.**

**Criterio de salida**: la app soporta 10× el tráfico del MVP sin cambios arquitectónicos mayores.

---

### [ ] T8.1 — Añadir cadenas (Alcampo, Eroski, Lidl, Aldi) ⚪

- **Depende de**: Épica 7 completa
- **Estimación**: 2d por cadena
- **Descripción**: Nuevos adaptadores `Productor` para cada cadena. Logos SVG. Seed actualizado.
- **Aceptación**:
  - [ ] Cada cadena tiene su `slug`, logo y adaptador.
  - [ ] Ingesta funciona end-to-end para la nueva cadena.
  - [ ] Caché y comparativa incluyen la nueva cadena.
  - [ ] Tests de integración por cadena.

---

### [ ] T8.2 — Migrar cola a RQ/Celery ⚪

- **Depende de**: cuello de botella medido en T3.4
- **Estimación**: 3d
- **Descripción**: Si el throughput de la cola Postgres es insuficiente, migrar a RQ (Redis) o Celery.
- **Aceptación**:
  - [ ] Nuevo adaptador `ColaJobs` con RQ o Celery.
  - [ ] Casos de uso sin cambios (gracias al puerto).
  - [ ] Migración de jobs pendientes sin pérdida.
  - [ ] Métricas comparativas antes/después.

---

### [ ] T8.3 — Desplegar en Kubernetes/OpenShift ⚪

- **Depende de**: T7.4, tráfico que lo justifique
- **Estimación**: 5d
- **Descripción**: Aplicar manifiestos de `infra/k8s/` en cluster real. Configurar operador de Postgres, External Secrets, HPA.
- **Aceptación**:
  - [ ] Cluster operativo con api, worker, scheduler, web.
  - [ ] Postgres con operador (primario + réplica + failover).
  - [ ] Secrets vía External Secrets Operator o SOPS.
  - [ ] HPA escala api y web según CPU.
  - [ ] Ingress con TLS.
  - [ ] Monitorización con Prometheus + Grafana (opcional).
  - [ ] Runbook de operación documentado.

---

### [ ] T8.4 — i18n completo + multi-país ⚪

- **Depende de**: T5.7
- **Estimación**: 5d
- **Descripción**: Añadir inglés y preparar la app para otros países (moneda, provincias, cadenas locales).
- **Aceptación**:
  - [ ] `locales/en.json` completo.
  - [ ] Selector de idioma en perfil.
  - [ ] Modelo de datos soporta `pais` en cadenas y provincias.
  - [ ] Formateo de moneda por país.
  - [ ] Tests de i18n.

---

## Anexo A — Orden de ejecución recomendado

Para evitar bloqueos, el orden sugerido es:

```
Épica 0 (completa)
  ↓
T2.1 → T2.2 → T2.5 → T2.6 → T2.3 → T2.4
  ↓
T1.1 → T1.2 → T1.3 → T1.4 → T1.5
  ↓
T3.1 → T3.2 → T3.6 → T3.7 → T3.3 → T3.4 → T3.5 → T3.8
  ↓
T4.4 → T4.3 → T4.1 → T4.2 → T4.5 → T4.6
  ↓
T5.1 → T5.7 → T5.2 → T5.3 → T5.4 → T5.5 → T5.6 → T5.8
  ↓
T6.1 → T6.2 → T6.3 → T6.4 → T6.5 → T6.6
  ↓
T7.1 → T7.2 → T7.5 → T7.3 → T7.4 → T7.6
  ↓
Épica 8 (solo si el tráfico lo justifica)
```

**Regla**: no empieces una tarea si sus dependencias no están `[x]`. Si una dependencia se bloquea (`[!]`), propaga el bloqueo.

---

## Anexo B — Criterios de aceptación del MVP

El MVP se considera completado cuando **todos** estos puntos se cumplen:

- [ ] Un usuario puede autenticarse con Google o Microsoft.
- [ ] Puede buscar un producto, seleccionar cadenas y ver resultados en cards con logo, ranking, imagen clicable, nombre, € y €/kg-L.
- [ ] La barra de progreso aparece solo en cache miss.
- [ ] Puede cambiar orden y filtros sin relanzar búsqueda.
- [ ] Puede ver el histórico de precios de un producto.
- [ ] Puede crear una lista, añadir productos y ver coste total + % A + % C.
- [ ] Puede editar su perfil y provincia; los precios se ajustan a su ubicación.
- [ ] Todo funciona en dev con datos de prueba y en prod con datos reales.
- [ ] No hay secretos en el repo (`gitleaks` pasa en CI).
- [ ] La API responde en `/health/ready` con RW, RO y Redis OK.
- [ ] Sentry y UptimeRobot activos en prod.
- [ ] Backups diarios verificados.
- [ ] Cobertura global ≥ 70% (dominio ≥ 80%).
- [ ] CI verde en `main`.

---

## Anexo C — Métricas de progreso

Actualizar al cerrar cada tarea:

| Épica | Completadas | Total | % |
|-------|-------------|-------|---|
| 0 — Fundación | 4 | 8 | 50% |
| 1 — Autenticación | 0 | 5 | 0% |
| 2 — Modelo de datos | 0 | 6 | 0% |
| 3 — Ingesta | 0 | 8 | 0% |
| 4 — API búsqueda/comparativa | 0 | 6 | 0% |
| 5 — Frontend flujo principal | 0 | 8 | 0% |
| 6 — Perfil y listas | 0 | 6 | 0% |
| 7 — Calidad y operación | 0 | 6 | 0% |
| **Total MVP** | **4** | **53** | **8%** |

---
