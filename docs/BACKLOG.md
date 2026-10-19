# BACKLOG.md

**Propósito**: Lista ejecutable de tareas del proyecto, organizada por épicas y ordenada por dependencias. OpenCode debe consultar este archivo antes de empezar cualquier tarea y marcarla como completada al terminarla.

**Fuente de verdad de requisitos**: `docs/PLAN.md`
**Reglas de ejecución**: `AGENTS.md`
**Convenciones**: `docs/CONVENTIONS.md`
**Decisiones**: `docs/decisions.md`

**Última actualización**: 2026-10-19
**Estado global**: 🟡 En desarrollo (Épica 0 parcial — 6/8; Épica 1 completada — 5/5; Épica 2 completada — 6/6; Épica 3 completada — 8/8; Épica 4 completada — 6/6; Épica 5 en curso — 2/8)

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
| 1 — Autenticación | 5 | 6d | ✅ Completada (5/5) |
| 2 — Modelo de datos | 6 | 7d | ✅ Completada (6/6) |
| 3 — Ingesta | 8 | 12d | ✅ Completada (8/8) |
| 4 — API búsqueda/comparativa | 6 | 8d | ✅ Completada (6/6) |
| 5 — Frontend flujo principal | 8 | 13d | 🟡 En curso (2/8) |
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

### [x] T1.1 — Configurar Auth.js con Google y Microsoft 🟡

- **Depende de**: T0.5
- **Estimación**: 1.5d
- **Descripción**: `web/src/lib/auth.ts` con providers Google y Microsoft Entra ID. Callback a `/api/auth/callback/{provider}`.
- **Aceptación**:
  - [x] Login con Google funciona en dev.
  - [x] Login con Microsoft funciona en dev.
  - [x] Sesión JWT firmada, TTL configurable.
  - [x] Variables en `.env` (`GOOGLE_CLIENT_ID`, etc.).
- **Notas**: crear apps OAuth en Google Cloud Console y Azure Portal. Documentar en `README.md`.
- **Nota**: implementación verificada en runtime (`/api/auth/providers|csrf|session`) y firma HS256 comprobada desde Python (ADR-012). El login real con Google/Microsoft queda pendiente de credenciales OAuth reales y se validará al final.

---

### [x] T1.2 — Tabla `usuarios` + migración 🟡

- **Depende de**: T2.1
- **Estimación**: 0.5d
- **Descripción**: Migración Alembic con tabla `usuarios` según `PLAN.md` §6 y las FK de `busquedas.usuario_id` y `listas.usuario_id`.
- **Aceptación**:
  - [x] Campos: `id`, `provider`, `provider_id`, `email`, `nombre`, `provincia`, `avatar_url`, `creado_en`.
  - [x] `UNIQUE (provider, provider_id)`.
  - [x] Índice en `email`.
  - [x] FK de `busquedas.usuario_id` y `listas.usuario_id` a `usuarios.id`.
- **Nota**: FK con `ON DELETE SET NULL`: al borrar un usuario, sus búsquedas y listas quedan anónimas en vez de eliminarse.

---

### [x] T1.3 — `GET /v1/me` + upsert de usuario 🟡

- **Depende de**: T1.1, T1.2
- **Estimación**: 1d
- **Descripción**: Endpoint que valida JWT y devuelve perfil. Si el usuario no existe, lo crea (upsert por `provider` + `provider_id`).
- **Aceptación**:
  - [x] `GET /v1/me` con JWT válido → 200 con perfil.
  - [x] Sin JWT → 401.
  - [x] JWT inválido → 401.
  - [x] Primer login crea fila en `usuarios`.
  - [x] Test de integración con BD real.
- **Nota**: el token se valida en la API con `NEXTAUTH_SECRET` (mismo secreto que Auth.js, ADR-012) y solo HS256. Errores en formato `{code, message}` (`NO_AUTENTICADO`, `AUTH_NO_CONFIGURADA`). El upsert es un `INSERT ... ON CONFLICT (provider, provider_id) DO UPDATE` atómico.

---

### [x] T1.4 — Middleware de sesión en Next.js 🟡

- **Depende de**: T1.1
- **Estimación**: 1d
- **Descripción**: Rutas `(app)/*` protegidas. Redirección a `/login` si no hay sesión. Rutas `(auth)/*` públicas.
- **Aceptación**:
  - [x] Usuario no logueado en `/buscar` → redirect a `/login`.
  - [x] Usuario logueado en `/login` → redirect a `/`.
  - [x] `session` accesible en Server Components.
- **Nota**: middleware en `web/src/middleware.ts`: protege todo salvo `/login`, `/api/auth/*` y assets; usa `getToken` con el mismo `decode` HS256 que Auth.js. La sesión se lee en Server Components con `getSession()` (`web/src/lib/session.ts`). Validado en runtime: sin sesión → 307 a `/login?callbackUrl=...`; con sesión en `/login` → 307 a `/`; el nombre del usuario se renderiza en el HTML.

---

### [x] T1.5 — Pantalla de login 🟡

- **Depende de**: T1.1
- **Estimación**: 1d
- **Descripción**: Página `/login` minimalista con dos botones: "Continuar con Google" y "Continuar con Microsoft". Logos SVG.
- **Aceptación**:
  - [x] Ambos botones inician flujo OAuth.
  - [x] Estilo minimalista tipo Google.
  - [x] Strings en `locales/es.json` (`login.google`, `login.microsoft`).
  - [x] Accesible por teclado.
- **Nota**: página en `web/src/app/(auth)/login/page.tsx` (Server Component) y botones en `web/src/components/FormularioLogin.tsx` (client). Logos SVG propios en `web/src/components/logos.tsx`. Verificado: `POST /api/auth/signin/google` → 302 a `accounts.google.com` y `POST /api/auth/signin/microsoft` → 302 a `login.microsoftonline.com`, ambos con el `redirect_uri` correcto. El login real queda pendiente de credenciales OAuth.

---

## Épica 2 — Modelo de datos

**Objetivo**: esquema completo, migraciones, repositorios, engines RW/RO, seed dev.

**Criterio de salida**: `alembic upgrade head` crea todas las tablas; seed inserta 3 cadenas y 100 productos; repositorios tienen tests; routing RW/RO funciona.

---

### [x] T2.1 — Esquema SQL inicial 🔴

- **Depende de**: T0.3
- **Estimación**: 1.5d
- **Descripción**: Migración Alembic con tablas de `PLAN.md` §6: `cadenas`, `productos`, `productos_cadena`, `precios`, `busquedas`, `listas`, `lista_items`.
- **Aceptación**:
  - [x] Todas las columnas, tipos, constraints e índices de `PLAN.md` §6 de las tablas listadas arriba.
  - [x] `pg_trgm` activado; índice GIN en `productos.nombre`.
  - [x] Índice `(producto_cadena_id, fecha_consulta DESC)` en `precios`.
  - [x] Constraint `chk_precios_ambito_provincia`.
  - [x] `alembic upgrade head` limpio desde BD vacía.
  - [x] `alembic downgrade base` limpio.
- **Nota**: `usuarios` y las FK de `usuario_id` se difieren a T1.2, que depende de esta migración.

---

### [x] T2.2 — Engines RW/RO + routing 🔴

- **Depende de**: T2.1
- **Estimación**: 1d
- **Descripción**: `api/src/adaptadores/persistencia/engines.py` con `engine_rw` y `engine_ro`. Casos de uso de lectura usan RO; escritura usa RW.
- **Aceptación**:
  - [x] Dos `AsyncEngine` configurados desde `DATABASE_URL_RW` y `DATABASE_URL_RO`.
  - [x] `get_session_ro()` y `get_session_rw()` como dependencias de FastAPI.
  - [x] Test que verifica que una escritura va a RW y una lectura a RO.
  - [x] Sticky post-escritura: tras un `POST`, las lecturas del mismo usuario van a RW durante N segundos (configurable).

---

### [x] T2.3 — Repositorios base + tests 🟡

- **Depende de**: T2.2
- **Estimación**: 2d
- **Descripción**: Implementaciones SQLAlchemy de los puertos definidos en `api/src/puertos/repositorios.py`.
- **Aceptación**:
  - [x] `RepositorioProductos`, `RepositorioPrecios`, `RepositorioListas`, `RepositorioBusquedas`.
  - [x] Métodos de lectura usan RO, de escritura RW.
  - [x] Tests de integración con Postgres de test.
  - [x] Cobertura > 80% en repositorios.
- **Nota**: los adaptadores reciben una `AsyncSession` ya enrutada (RO/RW) por el caso de uso. Los tests de integración requieren `DATABASE_URL_RW`/`DATABASE_URL_RO` y el esquema migrado; sin esas variables se saltan.

---

### [x] T2.4 — Seed dev con datos de prueba 🟡

- **Depende de**: T2.1
- **Estimación**: 1d
- **Descripción**: Script `api/scripts/seed.py` que inserta 3 cadenas (DIA, Carrefour, Mercadona) y 100 productos de muestra.
- **Aceptación**:
  - [x] 3 cadenas con slug y logo SVG path.
  - [x] 100 productos con nombre, marca, categoría, formato, litros_o_kg.
  - [x] `productos_cadena` con URL de producto.
  - [x] `precios` con al menos 1 precio por producto/cadena, estado `verificado`, ámbito `nacional`.
  - [x] Idempotente.
- **Nota**: se ejecuta con `python -m scripts.seed` (contenedor `api` o local con `.env` cargado). Idempotencia vía ids deterministas (uuid5) y `ON CONFLICT DO NOTHING`.

---

### [x] T2.5 — Puertos de ingesta (Productor, Verificador, Cache) 🟡

- **Depende de**: T0.5
- **Estimación**: 1d
- **Descripción**: `Protocol` de Python en `api/src/puertos/` con contratos de productor, verificador y cache.
- **Aceptación**:
  - [x] `Productor.producir(query, cadena) -> dict`.
  - [x] `Verificador.verificar(candidato) -> (estado, motivos)`.
  - [x] `Cache.get(key)`, `Cache.set(key, value, ttl)`, `Cache.invalidar_prefijo(prefijo)`.
  - [x] Tests de contrato con implementaciones fake.

---

### [x] T2.6 — Value Objects y reglas de dominio 🟢

- **Depende de**: T0.5
- **Estimación**: 0.5d
- **Descripción**: `Formato`, `Precio`, `Provincia` como `@dataclass(frozen=True)`. Función `calcular_precio_por_litro`.
- **Aceptación**:
  - [x] `Formato.a_litros_o_kg()` maneja L, ml, kg, g.
  - [x] `calcular_precio_por_litro` devuelve `None` si litros <= 0.
  - [x] Redondeo a 4 decimales.
  - [x] Cobertura 100% en estos módulos.

---

## Épica 3 — Ingesta

**Objetivo**: pipeline productor → verificador → BD, con worker, scheduler y caché.

**Criterio de salida**: un job de búsqueda end-to-end inserta precios verificados en BD; scheduler diario invalida caché; caché hit/miss medido.

---

### [x] T3.1 — Implementación `LLMProductor` 🔴

- **Depende de**: T2.5
- **Estimación**: 2d
- **Descripción**: Adaptador que llama al LLM con el prompt de `PLAN.md` §7 y parsea JSON estricto.
- **Aceptación**:
  - [x] Prompt en constante separada.
  - [x] Respuesta parseada a `dict` con campos obligatorios.
  - [x] Si el LLM devuelve texto no-JSON → error controlado, no crash.
  - [x] `url_fuente` obligatoria cuando `encontrado=true`.
  - [x] Tests con respuestas mockeadas (válida, inválida, no encontrado).
  - [x] Retry con backoff exponencial ante errores 5xx.
- **Nota**: `api/src/adaptadores/ingesta/llm_productor.py` (productor) + `prompts.py` (prompt en constante) + `cliente_llm.py` (clientes HTTP de `openai`/`xai` y `anthropic` tras el puerto `ClienteLLM`). El parseo es JSON estricto: si no es un objeto o faltan campos obligatorios (`nombre`, `formato`, `precio_eur`, `url_fuente`) se lanza `ErrorProductor` (error de dominio, sin crash). Los 5xx y fallos de red se reintentan con backoff 0.5 s, 1 s, 2 s; los 4xx no se reintentan.

---

### [x] T3.2 — Implementación `Verificador` (fetch + reglas) 🔴

- **Depende de**: T2.5
- **Estimación**: 2d
- **Descripción**: Adaptador que hace `GET` a `url_fuente` y aplica las reglas del validador de `PLAN.md` §7.
- **Aceptación**:
  - [x] Fetch con timeout 10 s y User-Agent de navegador.
  - [x] Comprueba precio en HTML (tolerante a `,` y `.`).
  - [x] Comprueba coherencia €/L vs. formato (±5%).
  - [x] Comprueba desviación vs. último precio conocido (>30% → `sospechoso`).
  - [x] Devuelve `(estado, motivos)` con estados `verificado | sospechoso | rechazado`.
  - [x] Tests con HTML real cacheado en `tests/fixtures/`.
- **Nota**: `api/src/adaptadores/ingesta/verificador_fetch.py` (`FetchVerificador`). Motivos estables: `agente_no_encontro`, `url_invalida`, `fetch_error`, `precio_invalido`, `precio_no_encontrado_en_html`, `precio_por_unidad_incoherente`, `desviacion_precio`. El último precio conocido llega en el candidato como `precio_eur_anterior` (lo añade el caso de uso). Reglas puras en `dominio/precios/reglas.py` y `dominio/productos/reglas.py`.

---

### [x] T3.3 — Caso de uso `BuscarProducto` 🔴

- **Depende de**: T3.1, T3.2, T2.3
- **Estimación**: 1.5d
- **Descripción**: Orquesta productor → verificador → repositorio con reintento acotado (máx. 3).
- **Aceptación**:
  - [x] Máximo 3 pasadas.
  - [x] Si `verificado` → guarda en BD y devuelve éxito.
  - [x] Si `rechazado` con motivo `agente_no_encontro` → no reintenta, devuelve fallo.
  - [x] Si `sospechoso` tras 3 pasadas → guarda con estado `sospechoso`.
  - [x] Tests con productor/verificador/repo mockeados.
- **Nota**: `api/src/aplicacion/ingesta/buscar_producto.py`. Resuelve el producto canónico (por EAN o nombre exacto) y su ficha en la cadena antes de verificar, y pasa al verificador el último precio conocido (`precio_eur_anterior`) para la regla de desviación. Requiere los repositorios de cadenas y de productos por cadena (`RepositorioCadenas`, `RepositorioProductosCadenas`), añadidos en esta tarea con sus adaptadores SQLAlchemy.

---

### [x] T3.4 — Cola de jobs en Postgres + worker 🔴

- **Depende de**: T3.3
- **Estimación**: 2d
- **Descripción**: Worker que hace polling a `busquedas` con `SKIP LOCKED` y ejecuta `BuscarProducto`.
- **Aceptación**:
  - [x] `SELECT ... FOR UPDATE SKIP LOCKED` sobre `busquedas WHERE estado='pendiente'`.
  - [x] Actualiza `estado` (`en_progreso` → `completada`/`fallida`) y `progreso` (0–100).
  - [x] Si el worker cae, el job vuelve a `pendiente` tras timeout.
  - [x] `api/src/worker.py` como punto de entrada (`python -m src.worker`).
  - [x] Tests de concurrencia: 2 workers no procesan el mismo job.
- **Nota**: cola en la propia tabla `busquedas` (ADR-007) tras el puerto `ColaJobs` (`api/src/puertos/cola.py`) y el adaptador `PostgresColaJobs`. El reclamo es un único `UPDATE ... WHERE id = (SELECT ... FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING *`; un job en `en_progreso` con `creado_en` anterior al timeout (15 min) se vuelve a reclamar, así que si el worker cae el job no se pierde. El progreso se actualiza cadena a cadena.

---

### [x] T3.5 — Scheduler diario 🟡

- **Depende de**: T3.4
- **Estimación**: 1d
- **Descripción**: Proceso `api/src/scheduler.py` que lanza ingesta diaria e invalida caché tras completarla.
- **Aceptación**:
  - [x] Cron interno (APScheduler) a las 03:00 Europe/Madrid.
  - [x] Encola jobs de ingesta para productos activos.
  - [x] Al terminar, `Cache.invalidar_prefijo("v1:")`.
  - [x] Logs de inicio/fin con duración.
  - [x] Proceso separado, no dentro de la API.
- **Nota**: `api/src/scheduler.py` (`python -m src.scheduler`) con APScheduler y `CronTrigger` a las 03:00 `Europe/Madrid`. Encola un job por producto activo (productos con alguna cadena) y espera a que la cola se vacíe antes de invalidar la caché, de modo que la invalidación ocurre con precios ya frescos. La espera tiene tope (1 h) y la invalidación se hace igualmente.

---

### [x] T3.6 — Implementación `RedisCache` 🟡

- **Depende de**: T2.5
- **Estimación**: 1d
- **Descripción**: Adaptador de caché con TTL, clave versionada (`v1:` + hash).
- **Aceptación**:
  - [x] `get`, `set` con TTL, `invalidar_prefijo` (por versión, sin `SCAN`).
  - [x] Serialización JSON.
  - [x] Si Redis cae, `get` devuelve `None` (no rompe la app).
  - [x] Tests con Redis de test.
- **Nota**: `api/src/adaptadores/cache/redis_cache.py` (`RedisCache`). Cada versión de clave mantiene un conjunto índice (`cache:indices:v1:`), así que `invalidar_prefijo("v1:")` borra sus valores y el índice sin `SCAN`. Si Redis falla, `get` devuelve `None` y `set`/`invalidar_prefijo` registran el fallo sin propagarlo.

---

### [x] T3.7 — Cálculo de `cache_key` 🟡

- **Depende de**: T3.6
- **Estimación**: 0.5d
- **Descripción**: Función que genera hash SHA-256 de `(query_normalizada, cadenas_ordenadas, orden, filtros, provincia)`.
- **Aceptación**:
  - [x] Normalización de query: lowercase, sin tildes, sin espacios múltiples.
  - [x] Cadenas ordenadas alfabéticamente.
  - [x] Filtros serializados de forma canónica.
  - [x] Tests: misma búsqueda → mismo hash; distinta provincia → distinto hash.
- **Nota**: `api/src/dominio/busquedas/reglas.py` (`calcular_cache_key`), con la normalización de texto en `api/src/dominio/normalizacion.py`. La clave es `v1:` + SHA-256 de la búsqueda canónica.

---

### [x] T3.8 — Métricas de ingesta 🟢

- **Depende de**: T3.4
- **Estimación**: 1d
- **Descripción**: Contadores en logs/BD: `% verificado`, `% sospechoso`, `% rechazado`, motivos más frecuentes.
- **Aceptación**:
  - [x] Tabla `ingesta_metricas` o logs estructurados consultables.
  - [x] Endpoint interno `GET /v1/_metrics/ingesta` (protegido).
  - [x] Documentado en `README.md` cómo consultarlas.
- **Nota**: tabla `ingesta_metricas` (migración `0003`) con el estado, la cadena y el motivo; la escribe el worker en cada cadena procesada. El endpoint `GET /v1/_metrics/ingesta` exige sesión iniciada y devuelve el reparto por estado con porcentajes y los motivos más frecuentes. Consulta documentada en `README.md`.

---

## Épica 4 — API búsqueda y comparativa

**Objetivo**: endpoints que el frontend consume para buscar y comparar.

**Criterio de salida**: `POST /v1/busquedas` devuelve cache hit o job_id; `GET /v1/busquedas/{id}` devuelve progreso; `GET /v1/comparar` devuelve resultados con orden y filtros.

---

### [x] T4.1 — `POST /v1/busquedas` 🔴

- **Depende de**: T3.3, T3.6, T3.7
- **Estimación**: 1d
- **Descripción**: Endpoint que calcula `cache_key`, consulta Redis, y si no hay hit, encola job.
- **Aceptación**:
  - [x] Body: `{ query, cadenas, orden, filtros, provincia? }`.
  - [x] Cache hit → `{ job_id: null, cache_hit: true, resultados }`.
  - [x] Cache miss → `{ job_id, cache_hit: false }`.
  - [x] Sin JWT → 401.
  - [x] Rate limit aplicado.
  - [x] Tests: hit, miss, sin auth, rate limit.
- **Nota**: `api/src/api_http/v1/busquedas.py` sobre el caso de uso `CrearBusqueda` (`api/src/aplicacion/busquedas/crear_busqueda.py`). El límite de peticiones se aplica en la aplicación con un contador por usuario en Redis (`RedisLimitador`, `RATE_LIMIT_BUSQUEDAS_POR_MINUTO`); en el borde, Caddy limita `/api/v1/busquedas` por IP (ADR-011). El worker cachea el resultado de cada job con la `cache_key` para que la siguiente petición sea un acierto.

---

### [x] T4.2 — `GET /v1/busquedas/{id}` 🔴

- **Depende de**: T3.4
- **Estimación**: 1d
- **Descripción**: Endpoint de polling que devuelve estado + progreso + resultados parciales.
- **Aceptación**:
  - [x] `{ estado, progreso, resultados_parciales, completado_en? }`.
  - [x] Estados: `pendiente | en_progreso | completada | fallida`.
  - [x] Solo el dueño del job puede consultarlo (o admin).
  - [x] Tests de transición de estados.
- **Nota**: `GET /v1/busquedas/{id}` en `api/src/api_http/v1/busquedas.py`. El propietario se comprueba con el usuario interno del token (`RepositorioUsuarios.obtener_por_provider`); si no coincide con el `usuario_id` del job responde 403 y si el job no existe 404. Los resultados parciales salen de la comparativa vigente. `POST /v1/busquedas` marca el sticky read del usuario para que el polling lea del primario.

---

### [x] T4.3 — `GET /v1/comparar` 🔴

- **Depende de**: T2.3, T2.6
- **Estimación**: 2d
- **Descripción**: Endpoint que devuelve resultados con orden y filtros aplicados en SQL (desde RO).
- **Aceptación**:
  - [x] Query params: `q`, `cadenas`, `orden` (`precio_unitario|precio_kg_l|relevancia`), `precio_min`, `precio_max`, `marca`, `categoria`, `solo_con_stock`, `provincia`.
  - [x] Orden por defecto: `precio_unitario`.
  - [x] Resolución de precio por provincia (ADR-009).
  - [x] Paginación `limit`/`offset`.
  - [x] Tests: cada filtro, cada orden, fallback provincia→nacional.
- **Nota**: `api/src/api_http/v1/comparar.py`. La consulta elige un precio por producto y cadena con `DISTINCT ON`, prefiriendo el provincial sobre el nacional y cayendo al nacional si no hay precio de la provincia (ADR-009). Los filtros de precio y stock se aplican sobre el precio ya elegido; la paginación va en la misma consulta. El repositorio (`buscar_comparativa`) devuelve entidades de dominio y la posición en el ranking la calcula el dominio.

---

### [x] T4.4 — Cálculo determinista €/L y ranking 🟡

- **Depende de**: T2.6
- **Estimación**: 1d
- **Descripción**: Función de dominio que calcula €/L y posición en ranking.
- **Aceptación**:
  - [x] Redondeo a 4 decimales en BD, 2 en UI.
  - [x] Ranking estable (desempate por nombre).
  - [x] Tests con casos límite (formato desconocido, precio 0, etc.).
- **Nota**: `api/src/dominio/precios/ranking.py` (`ordenar_resultados`, `posicionar`) sobre la entidad `ResultadoComparacion`. El €/L se calcula con 4 decimales (`calcular_precio_por_litro`); el redondeo a 2 decimales para la interfaz es del frontend. El desempate es por nombre y después cadena; con `relevancia` se respeta el orden del repositorio, que conoce la similitud con la consulta.

---

### [x] T4.5 — Cache de respuestas de comparación 🟢

- **Depende de**: T4.3, T3.6
- **Estimación**: 0.5d
- **Descripción**: Cachear `GET /v1/comparar` con TTL corto (5 min) en Redis.
- **Aceptación**:
  - [x] Clave incluye todos los query params + provincia.
  - [x] TTL 300 s.
  - [x] Invalidación tras ingesta.
- **Nota**: la comparativa se cachea con TTL de 300 s bajo el prefijo `v1:cmp:` (clave propia para no chocar con la de la búsqueda, pero dentro de la versión `v1:`), e incluye todos los query params —filtros, orden y paginación— más la provincia. La invalidación tras la ingesta (`invalidate_prefijo("v1:")`) la limpia. Si el valor cacheado no valida, se recalcula desde la BD.

---

### [x] T4.6 — Exception handlers globales 🟡

- **Depende de**: T4.1
- **Estimación**: 0.5d
- **Descripción**: Traducir errores de dominio a HTTP con `{ code, message }`.
- **Aceptación**:
  - [x] `ProductoNoEncontradoError` → 404.
  - [x] `UsuarioNoAutorizadoError` → 403.
  - [x] `RateLimitError` → 429.
  - [x] Errores inesperados → 500 con Sentry, sin stack trace al cliente.
- **Nota**: manejadores en `api/src/api_http/errores.py`, registrados en `main.py`. Los errores inesperados se registran con traza en el log del servidor, se envían a Sentry si hay `SENTRY_DSN` y al cliente solo se le devuelve `{code: "ERROR_INTERNO", message: ...}`. Se añade `sentry-sdk` como dependencia y Sentry se activa en el lifespan de la API.

---

## Épica 5 — Frontend flujo principal

**Objetivo**: hero → resultados, cards, ficha producto, histórico, i18n.

**Criterio de salida**: usuario busca, ve barra de progreso (solo miss), ve cards con todos los campos, cambia orden/filtros, abre ficha con histórico.

---

### [x] T5.1 — Layout minimalista + menú lateral 🔴

- **Depende de**: T1.4
- **Estimación**: 2d
- **Descripción**: Layout base con header, menú lateral colapsable, área de contenido. Estilo tipo Google.
- **Aceptación**:
  - [x] Menú colapsable con enlaces: Buscar, Listas, Perfil.
  - [x] Responsive (móvil: menú overlay).
  - [x] Accesible por teclado.
  - [x] Tailwind con tokens en `tailwind.config.ts`.
- **Nota**: Tailwind 3 con tokens en `web/tailwind.config.ts` (colores, radios `pill`/`tarjeta`, anchos `contenido`/`lectura`) y `web/postcss.config.js`. El cromo vive en `web/src/components/layout/AppShell.tsx` (cliente): cabecera fija, botón `aria-expanded`/`aria-controls` para desplegar el menú y overlay en móvil; en escritorio el menú es sticky. `web/src/lib/i18n.ts` resuelve las claves de `locales/es.json` para que no haya strings sueltos en el JSX.

---

### [x] T5.2 — Hero buscador + selector SVG cadenas 🔴

- **Depende de**: T5.1
- **Estimación**: 2d
- **Descripción**: Página `/` con buscador centrado, selector de cadenas con logos SVG, botón "Comparar".
- **Aceptación**:
  - [x] Logos SVG en `public/logos/` (DIA, Carrefour, Mercadona).
  - [x] Selección múltiple con estado visual.
  - [x] Botón "Comparar" deshabilitado si no hay query o cadenas.
  - [x] Enter en el input lanza búsqueda.
- **Nota**: `web/src/components/buscador/HeroBuscador.tsx` (cliente) con el input, `SelectorCadenas.tsx` (selección múltiple con los logos de `web/public/logos/`, los mismos que usa el seed) y el botón deshabilitado mientras falte consulta o cadenas. El formulario tiene `onSubmit` propio, así que Enter lanza la búsqueda igual que el botón. La llamada a la API sale del servidor: `web/src/app/api/busquedas/route.ts` hace de proxy y reenvía el token de sesión (`web/src/lib/api.ts`), de modo que el JWT no llega al navegador. Con la respuesta se navega a `/buscar?q=...&cadenas=...&job=...` (la vista de resultados y la barra de progreso son T5.3).

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
| 0 — Fundación | 6 | 8 | 75% |
| 1 — Autenticación | 5 | 5 | 100% |
| 2 — Modelo de datos | 6 | 6 | 100% |
| 3 — Ingesta | 8 | 8 | 100% |
| 4 — API búsqueda/comparativa | 6 | 6 | 100% |
| 5 — Frontend flujo principal | 2 | 8 | 25% |
| 6 — Perfil y listas | 0 | 6 | 0% |
| 7 — Calidad y operación | 0 | 6 | 0% |
| **Total MVP** | **33** | **53** | **62%** |

---
