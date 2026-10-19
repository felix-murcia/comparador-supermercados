Ahora sí estamos hablando de la pieza que te faltaba. Y lo que describes **es exactamente el patrón que necesita tu comparador**, pero con matices importantes que conviene aterrizar.

## El patrón en una frase

**Enjambre de agentes que producen + capa de verificación determinista/barata que valida + reintento hasta converger.**

Eso es lo que el chaval chino (y mucha gente ya) está aplicando. La clave no es "300 agentes", es **separar producción de verificación**.

## Cómo se traduce a tu app de precios

Tu problema tiene una ventaja enorme frente al suyo: **el precio es un dato objetivo y comprobable**. No es una opinión ni un resumen; es un número que está o no está en una URL. Eso hace la verificación mucho más fácil y barata que verificar "perfiles de empresa".

Arquitectura concreta:

```
┌─────────────────────────────────────────────┐
│  CAPA 1: PRODUCTORES (agentes con búsqueda) │
│  - N agentes en paralelo, uno por producto  │
│  - Devuelven JSON: precio, formato, €/L,    │
│    url_fuente, fecha, confianza             │
└──────────────────┬──────────────────────────┘
                   ▼
┌─────────────────────────────────────────────┐
│  CAPA 2: VERIFICADORES (baratos, rápidos)   │
│  - GET a url_fuente (sin scraping complejo) │
│  - ¿La URL responde 200?                    │
│  - ¿El número aparece en el HTML/texto?     │
│  - ¿€/L cuadra con formato?                 │
│  - ¿Desviación < X% vs. último guardado?    │
└──────────────────┬──────────────────────────┘
                   ▼
        ┌──────────┴──────────┐
        │                     │
     PASA                  FALLA
        │                     │
        ▼                     ▼
  Guardar en vault      Reintentar con
  (Obsidian/.md)        otro agente/prompt
                        (máx. 2-3 pasadas)
```

## Lo que tú puedes copiar tal cual

1. **Paralelización**: lanzas N consultas a la vez (no 300, empieza con 10-20). Cada una es independiente.
2. **Verificación barata**: no uses un LLM caro para verificar. Un `fetch` + regex + reglas es suficiente para el 90% de casos. Solo si falla, pasa a un LLM pequeño como juez.
3. **Reintento acotado**: máximo 2-3 pasadas. Si tras 3 no converge, marcas el producto como "no verificado" y lo excluyes de la UI (o lo muestras con etiqueta).
4. **Vault como output**: guardar en `.md` planos (como el hilo anterior) te da trazabilidad, diff-ability y cero dependencia de base de datos al inicio.
5. **Cero errores como métrica**: igual que él terminó con 0 errores en 100 perfiles, tú puedes medir "0 precios falsos en el top 100 productos". Eso es tu KPI de calidad.

## Lo que NO debes copiar ciegamente

- **300 agentes desde el día 1**: es caro y no aporta si tu cuello de botella es la verificación. Empieza con 10 y escala cuando la tasa de acierto sea >95%.
- **Verificación con LLM para todo**: para precios, el `fetch` + regex es más fiable y 100x más barato. Reserva el LLM-juez para casos ambiguos (producto sin URL clara, precio con descuento, etc.).
- **Confiar en "cero errores" sin auditoría**: guarda siempre la URL y la fecha. Si mañana un usuario reporta un precio mal, necesitas poder reproducir qué pasó.

## Coste realista (para que no te lleve a engaño)

Para 500 productos × 3 cadenas = 1.500 consultas:

- **Producción** (agente con búsqueda): ~1.500 llamadas. A precio típico de LLM con búsqueda, puede ser **decenas de euros por actualización completa**. Si actualizas 2×/día, son cientos de €/mes.
- **Verificación** (fetch + reglas): prácticamente **gratis** (solo ancho de banda).
- **Reintentos**: +10-20% sobre producción.

Por eso el cache-first es crítico: solo relanzas producción para productos cuyo precio **puede haber cambiado** (o cada X días), y verificas el resto con el `fetch` barato.

## Siguiente paso concreto

Si quieres, te escribo:

1. El **prompt exacto** del agente productor (JSON estricto con `url_fuente` obligatoria).
2. El **validador en pseudocódigo** (fetch + reglas + umbral de desviación).
3. El **esquema del vault** (`.md` por producto + `INDEX.md`) para que sea legible por agente y por humano.
4. El **scheduler** mínimo (cron diario + cola de reintentos).

¿Empezamos por el prompt y el validador, que son el núcleo del patrón?

Tienes razón, me he adelantado. Volvamos al orden correcto: **arquitectura primero, backlog después**. Y ojo con un riesgo que veo venir: meter Kubernetes, balanceador y Nginx en un MVP de comparador de precios es la forma más rápida de no lanzar nunca. Vamos a definirlo con criterio.

## 1. Preguntas que condicionan toda la arquitectura

Antes de elegir componentes, necesito que fijemos esto (te doy mi recomendación por defecto entre paréntesis):

1. **¿Cuántos productos y cadenas en el MVP?** (ej: 200 productos × 3 cadenas)
2. **¿Frecuencia de actualización?** (ej: 1×/día)
3. **¿Usuarios concurrentes esperados al inicio?** (ej: <1.000/día)
4. **¿Presupuesto mensual de infra?** (ej: 20–50 €)
5. **¿Equipo?** (ej: tú solo)
6. **¿Hay app móvil o solo web?** (ej: web responsive primero)
7. **¿Necesitas histórico de precios desde el día 1?** (recomiendo sí, es tu diferencial)
8. **¿Monetización?** (afiliación, ads, freemium) → afecta a ToS y a si necesitas API pública

Sin estas respuestas, cualquier arquitectura es humo.

## 2. Arquitectura propuesta para MVP (monolito modular, no microservicios)

Mi recomendación firme: **empezar con un monolito modular desplegado en un solo VPS o en un PaaS**, y solo añadir piezas cuando el dolor sea real.

```
┌──────────────────────────────────────────────────────┐
│                    CLIENTE (web)                     │
│         Next.js (SSR) o Astro + React                │
└───────────────────────┬──────────────────────────────┘
                        │ HTTPS
┌───────────────────────▼──────────────────────────────┐
│              REVERSE PROXY (Caddy o Nginx)           │
│         TLS automático, compresión, rate limit       │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│                  API (FastAPI / Node)                │
│  - /productos, /precios, /comparar, /historial       │
│  - Auth simple (si hay usuarios)                     │
└───────┬───────────────────────────────┬──────────────┘
        │                               │
┌───────▼────────┐              ┌───────▼──────────────┐
│  PostgreSQL    │              │  Redis (opcional)    │
│  - productos   │              │  - cache respuestas  │
│  - precios     │              │  - colas de trabajos │
│  - fuentes     │              │  - rate limit        │
│  - histórico   │              └──────────────────────┘
└───────▲────────┘
        │
┌───────┴──────────────────────────────────────────────┐
│           WORKER DE INGESTA (proceso aparte)         │
│  - Scheduler (cron interno o APScheduler)            │
│  - Cola de tareas (Redis + RQ/Celery, o simple)      │
│  - Productores (LLM con búsqueda)                    │
│  - Verificadores (fetch + reglas)                    │
│  - Escritura en BD + vault .md (opcional)            │
└──────────────────────────────────────────────────────┘
```

### Decisiones clave y por qué

| Componente | Elección MVP | Por qué |
|-----------|--------------|---------|
| **Lenguaje backend** | Python (FastAPI) | Ecosistema scraping/LLM inmejorable, async nativo, tipado |
| **Frontend** | Next.js (App Router) | SSR para SEO (crítico en comparadores), React |
| **BD** | PostgreSQL | Histórico relacional, consultas de comparación, JSONB para flexibilidad |
| **Cache/Cola** | Redis | Sí, pero **opcional al inicio**. Sin él, usa la propia BD como cola (SKIP LOCKED) |
| **Reverse proxy** | Caddy | TLS automático, config de 5 líneas. Nginx solo si necesitas algo muy específico |
| **Contenedores** | Docker + docker-compose | Sí, desde el día 1. Reproducibilidad |
| **Orquestación** | **Ninguna** | Kubernetes **NO** en MVP. Ni Swarm. Un VPS con compose |
| **Balanceador** | El propio Caddy | No necesitas ALB/HAProxy hasta tener >1 instancia |
| **Hosting** | Hetzner CX22 (~5 €/mes) o Fly.io/Railway | Barato, suficiente para miles de requests/día |
| **Observabilidad** | Logs a archivo + Sentry free + UptimeRobot | No montes Prometheus/Grafana aún |
| **CI/CD** | GitHub Actions → deploy por SSH o imagen Docker | Simple y gratis |

### Lo que **explicitamente NO** metemos en el MVP

- Kubernetes, Helm, ArgoCD → sobredimensionado para 1 dev y <1k usuarios/día
- Kafka/RabbitMQ → Redis o la BD bastan para colas de cientos de tareas/día
- Microservicios → un monolito modular con carpetas claras (`api/`, `ingesta/`, `dominio/`)
- Nginx + balanceador + múltiples réplicas → Caddy + 1 instancia hasta que duela
- Elasticsearch → Postgres con `tsvector` cubre búsqueda de productos de sobra
- Vault Obsidian como fuente de verdad → **solo como export/backup legible**, la BD manda

## 3. Módulos del monolito (para que no se convierta en bola de barro)

```
/app
  /api            # endpoints FastAPI
  /dominio        # entidades: Producto, Precio, Fuente, Cadena
  /ingesta
    /productores  # llamadas a LLM con búsqueda
    /verificadores# fetch + reglas
    /scheduler    # cron
  /persistencia   # repositorios SQLAlchemy
  /vault          # export .md (opcional)
  /web            # Next.js (repo separado o monorepo)
```

Regla: **la ingesta nunca llama directo a la BD sin pasar por `dominio`**. Así puedes testear y cambiar la fuente (LLM → scraping → API oficial) sin tocar la API pública.

## 4. Backlog inicial (épicas → tareas)

Te lo doy como épicas con tareas concretas. Priorizadas para que la primera iteración sea **end-to-end con 1 producto y 1 cadena**.

### Épica 0 — Fundación (semana 1)
- [ ] Definir respuestas a las 8 preguntas de arriba
- [ ] Crear repo monorepo (`/api`, `/web`, `/infra`)
- [ ] `docker-compose.yml` con Postgres + Redis + API + worker
- [ ] Esqueleto FastAPI con `/health`
- [ ] Esqueleto Next.js con página "Hola"
- [ ] CI: lint + tests + build en GitHub Actions
- [ ] Deploy inicial a VPS con Caddy + compose

### Épica 1 — Modelo de datos (semana 1–2)
- [ ] Esquema `cadenas`, `productos`, `fuentes`, `precios` (con `estado`, `url_fuente`, `fecha`)
- [ ] Migraciones con Alembic
- [ ] Repositorios básicos + tests
- [ ] Seed con 10 productos reales

### Épica 2 — Ingesta end-to-end (semana 2–3)
- [ ] Interfaz `Productor` (contrato del prompt JSON)
- [ ] Implementación `ProductorLLM` (1 proveedor)
- [ ] Implementación `Verificador` (fetch + reglas del validador)
- [ ] Bucle de reintento acotado
- [ ] Worker que procesa una cola simple (BD `SKIP LOCKED`)
- [ ] Scheduler diario
- [ ] Test end-to-end: 1 producto × 1 cadena → BD con estado `verificado`

### Épica 3 — API pública (semana 3)
- [ ] `GET /productos`
- [ ] `GET /productos/{id}/precios`
- [ ] `GET /comparar?producto=...`
- [ ] `GET /historial/{producto_id}`
- [ ] Cache de respuestas (Redis o HTTP cache)
- [ ] Rate limit básico en Caddy

### Épica 4 — Frontend MVP (semana 3–4)
- [ ] Listado de productos con buscador
- [ ] Ficha de producto con comparativa de cadenas
- [ ] Gráfica de histórico (Recharts)
- [ ] Etiqueta "verificado / estimado / última actualización"
- [ ] Páginas SEO (SSR) por producto

### Épica 5 — Calidad y operación (transversal, desde semana 2)
- [ ] Métricas de ingesta: % verificado, % rechazado, motivos
- [ ] Alertas: Sentry + UptimeRobot
- [ ] Backups diarios de Postgres
- [ ] Export a vault `.md` (opcional, para auditoría humana)
- [ ] Documento `decisions.md` (ADR ligero)

### Épica 6 — Escala (solo cuando duela)
- [ ] Más cadenas
- [ ] Más productos
- [ ] Separar worker en su propio contenedor/VPS
- [ ] Evaluar cola real (RQ/Celery)
- [ ] Evaluar réplicas + balanceo (aquí sí entra el debate Nginx/K8s)

## 5. Lo que necesito de ti para cerrar la arquitectura

Responde a las 8 preguntas del punto 1, aunque sea con valores por defecto. Con eso te devuelvo:

1. El `docker-compose.yml` concreto
2. El diagrama final ajustado a tus números
3. El backlog convertido en issues de GitHub con estimaciones

¿Empezamos por las 8 preguntas o prefieres que fije yo los valores por defecto y tú corriges lo que no te cuadre?

Perfecto, ahora tengo la visión funcional. Esto cambia algunas cosas respecto a mi propuesta anterior, sobre todo en **autenticación** y en **cómo se sirven los resultados de búsqueda**. Te resumo los ajustes arquitectónicos y luego te devuelvo las preguntas ya respondidas con valores por defecto, para que solo corrijas lo que no te cuadre.

## Ajustes a la arquitectura por tu visión funcional

### 1. Autenticación (punto 1) — Google + Microsoft
- **No** montes auth propia con contraseñas. Usa **OAuth 2.0 / OIDC**.
- Opciones: **Auth.js (NextAuth)** si el frontend Next.js maneja sesión, o **Authlib + FastAPI** si prefieres que el backend sea el dueño de la sesión.
- Recomendación: **Auth.js en Next.js** con sesión JWT firmada y el backend validando el token. Menos código, menos superficie de ataque.
- Proveedores: Google Identity + Microsoft Entra ID (Azure AD). Ambos gratuitos para este uso.
- **Consecuencia en BD**: tabla `usuarios` con `provider`, `provider_id`, `email`, `nombre`, `ubicacion`, `avatar_url`. Nada de passwords.

### 2. Búsqueda con barra de progreso (punto 4)
Esto es lo más delicado. "Mientras busca sale una barra de progreso" implica que la búsqueda **no es instantánea** (porque consulta IA/búsqueda web en vivo). Tienes dos patrones:

| Patrón | Cuándo usarlo | Complejidad |
|--------|---------------|-------------|
| **Síncrono** (request → espera → respuesta) | Si la búsqueda tarda <10 s y no bloqueas el hilo | Baja |
| **Asíncrono con job** (request → `job_id` → polling/SSE → resultado) | Si tarda 10–60 s o quieres barra de progreso real | Media |

**Recomendación**: **asíncrono con SSE (Server-Sent Events)** o polling cada 1–2 s contra `GET /busquedas/{job_id}`. La barra de progreso se alimenta de eventos (`productor_iniciado`, `verificado`, `rechazado`, etc.). Esto encaja perfecto con el patrón productor/verificador que definimos: cada producto genera un evento.

- **No** metas WebSockets para esto: SSE es más simple y suficiente (unidireccional servidor→cliente).
- La cola de búsquedas puede vivir en **Redis** o en **Postgres con `SKIP LOCKED`** (mi recomendación para MVP, menos piezas).

### 3. Filtros, orden y comparativa (puntos 2 y 3)
- El **orden por precio unitario / precio kilo-litro** y los filtros son **consulta a BD**, no IA. Determinista y cacheable.
- Los **logos SVG** de supermercados: guárdalos como assets estáticos en el frontend (`/public/logos/`), no en BD. La BD solo guarda el `slug` de la cadena (`dia`, `carrefour`, `mercadona`).
- La **selección de supermercados** es estado de UI + parámetro de la búsqueda (`?cadenas=dia,carrefour`). No necesita persistencia salvo que quieras recordarla por usuario (entonces, tabla `preferencias_usuario`).

### 4. UI minimalista tipo Google (punto 5)
- **Next.js App Router** con dos "vistas" de la misma página: estado inicial (hero con buscador centrado) y estado resultados (buscador arriba + cards). Se resuelve con estado de cliente + URL (`/buscar?q=...`).
- La flecha "volver" = navegación a `/` o reset de query params.
- **SSR para SEO** en `/producto/{slug}` y `/comparar/{slug}` (páginas compartibles e indexables). La búsqueda en vivo puede ser CSR.

### 5. Menú colapsable + perfil + listas (puntos 6, 7, 8)
- Menú lateral: componente de UI, sin lógica de negocio.
- **Listas de la compra**: entidades `listas` y `lista_items`. Cada item referencia un `producto` y opcionalmente un `precio` snapshot (para calcular coste y ahorro con el precio del momento en que se añadió).
- **Coste total y % de ahorro**: cálculo determinista en backend (`GET /listas/{id}/resumen`) o en frontend si los datos ya vienen. Recomiendo backend para poder cachear y testear.
- **% de ahorro** requiere definir contra qué se compara: ¿precio más barato entre cadenas seleccionadas? ¿precio medio? ¿precio de una cadena "base"? Eso es una **decisión de producto** que hay que fijar antes de implementar.

### 6. Modularidad y SOLID (tu requisito explícito)
Esto refuerza el monolito modular que propuse, con capas claras:

```
/dominio          # entidades puras + reglas de negocio (sin frameworks)
  /productos
  /precios
  /listas
  /usuarios
/aplicacion       # casos de uso (orquestan dominio + puertos)
  /buscar_producto
  /crear_lista
  /calcular_ahorro
/puertos          # interfaces (repos, productor, verificador, auth)
/adaptadores      # implementaciones concretas (SQLAlchemy, LLM, OAuth)
  /persistencia
  /ingesta
  /auth
/api              # capa HTTP (FastAPI) — solo traduce, no decide
/web              # Next.js
```

Regla SOLID aplicada:
- **S**RP: `Productor` solo produce, `Verificador` solo verifica, `CalculadoraAhorro` solo calcula.
- **O**CP: añadir una cadena nueva = nueva implementación de `Productor`, sin tocar el resto.
- **L**SP: cualquier `Productor` (LLM, scraping, API oficial) cumple el mismo contrato.
- **I**SP: puertos pequeños (`BuscadorPrecios`, `ValidadorPrecio`) en vez de uno gigante.
- **D**IP: la capa `api` depende de `puertos`, no de `adaptadores`.

**Complejidad ciclomática baja**: funciones cortas, sin `if` anidados profundos, usar early returns y diccionarios de dispatch en lugar de cadenas de `elif`.

## Preguntas respondidas con valores por defecto

| # | Pregunta | Valor por defecto propuesto | ¿Te vale? |
|---|----------|------------------------------|-----------|
| 1 | Productos × cadenas MVP | 100 productos × 3 cadenas (DIA, Carrefour, Mercadona) | |
| 2 | Frecuencia de actualización | 1×/día (madrugada) + bajo demanda al buscar | |
| 3 | Usuarios concurrentes | <500/día, <50 simultáneos | |
| 4 | Presupuesto infra | 20–40 €/mes (VPS + dominio + Sentry free) | |
| 5 | Equipo | Tú solo | |
| 6 | App móvil | No; web responsive primero | |
| 7 | Histórico desde día 1 | Sí (tabla `precios` con `fecha` y `estado`) | |
| 8 | Monetización | No en MVP; diseñar API pública después | |

## Backlog ajustado a tu visión funcional

Reordeno las épicas para que la primera iteración ya sea **"login → buscar → ver cards"**, que es el corazón de la app.

### Épica 0 — Fundación
- [ ] Monorepo (`/api`, `/web`, `/infra`) + docker-compose (Postgres + Redis + API + worker)
- [ ] Esqueleto FastAPI + Next.js + CI (lint, tests, build)
- [ ] Deploy a VPS con Caddy + compose

### Épica 1 — Autenticación
- [ ] Configurar OAuth Google + Microsoft en Auth.js
- [ ] Tabla `usuarios` + endpoint `GET /me`
- [ ] Middleware de sesión en Next.js y validación de token en FastAPI
- [ ] Pantalla login/signup con botones Google/Microsoft

### Épica 2 — Modelo de datos
- [ ] Esquema: `cadenas`, `productos`, `fuentes`, `precios`, `usuarios`, `listas`, `lista_items`
- [ ] Migraciones Alembic + seed de 3 cadenas y 100 productos
- [ ] Repositorios + tests de dominio

### Épica 3 — Ingesta (productor + verificador)
- [ ] Puerto `Productor` + implementación LLM con búsqueda
- [ ] Puerto `Verificador` + implementación fetch+reglas
- [ ] Caso de uso `BuscarProducto` con reintento acotado
- [ ] Cola en Postgres (`SKIP LOCKED`) + worker
- [ ] Scheduler diario (APScheduler en el worker)

### Épica 4 — Búsqueda y comparativa (API)
- [ ] `POST /busquedas` → devuelve `job_id`
- [ ] `GET /busquedas/{job_id}` → estado + eventos (para barra de progreso)
- [ ] SSE `GET /busquedas/{job_id}/stream` (opcional, si polling no basta)
- [ ] `GET /comparar?q=...&cadenas=...&orden=...&filtros=...`
- [ ] Cálculo determinista de €/L y ranking
- [ ] Cache de resultados (Redis, TTL corto)

### Épica 5 — Frontend: flujo principal
- [ ] Layout minimalista + menú lateral colapsable
- [ ] Pantalla inicial: hero con buscador + selector SVG de cadenas
- [ ] Botón "Comparar" + barra de progreso (polling o SSE)
- [ ] Cards de producto: logo, ranking, imagen clicable, nombre, € unitario, €/kg-L
- [ ] Transición hero → resultados (buscador arriba, flecha volver)
- [ ] Re-búsqueda con filtros persistidos en URL

### Épica 6 — Perfil y listas
- [ ] Página perfil (nombre, email, ubicación) + `PATCH /me`
- [ ] CRUD listas (`/listas`, `/listas/{id}`)
- [ ] Añadir producto a lista desde card
- [ ] Vista lista: items, coste total, % ahorro
- [ ] Definir fórmula de % ahorro (decisión de producto pendiente)

### Épica 7 — Calidad y operación
- [ ] Métricas de ingesta (% verificado, motivos de rechazo)
- [ ] Sentry + UptimeRobot + backups Postgres
- [ ] ADRs en `decisions.md`
- [ ] Tests de dominio (pytest) y de componentes (Vitest)

### Épica 8 — Escala (post-MVP)
- [ ] Más cadenas y productos
- [ ] Separar worker a otro contenedor
- [ ] Evaluar RQ/Celery, réplicas, balanceo

## Lo que necesito que confirmes antes de escribir código

1. **¿Te valen los valores por defecto** de la tabla (100 productos, 3 cadenas, 1×/día, VPS único, tú solo, web responsive)?
2. **% de ahorro**: ¿contra qué se compara? (opciones: precio más barato entre cadenas seleccionadas / precio medio / precio de una cadena base elegida por el usuario)
3. **Barra de progreso**: ¿te vale **polling cada 1–2 s** contra `GET /busquedas/{job_id}` o quieres SSE desde el inicio? (polling = más simple, SSE = más fluido)
4. **Histórico de precios**: ¿lo mostramos ya en la ficha de producto del MVP o lo dejamos para post-MVP? (afecta a la Épica 5)

Con esas 4 respuestas te escribo el `docker-compose.yml`, el esquema SQL inicial y convierto el backlog en issues de GitHub con estimaciones. ¿Vamos?

Perfecto, con estas precisiones la arquitectura se cierra bastante. Te resumo los ajustes que introducen tus nuevos requisitos, porque algunos chocan frontalmente con el "VPS único con docker-compose" que propuse y hay que resolverlos con honestidad.

## 1. Ajustes por tus nuevos requisitos

### 1.1 Caché de búsquedas con TTL 24 h
- **Clave de caché**: hash de `(query_normalizada, cadenas_seleccionadas, orden, filtros)`. Si el usuario busca "aceite oliva" en DIA+Carrefour, y otro busca "Aceite Oliva" en las mismas cadenas con el mismo orden, comparten caché.
- **Dónde**: Redis (con `EXPIRE 86400`) o Postgres (`tabla busquedas_cache` con `expira_en`). Recomiendo **Redis** porque ya lo tienes para colas y el TTL es nativo.
- **Flujo**:
  ```
  POST /busquedas
    → ¿hay cache para la clave?
       → SÍ: devuelve { job_id, cache_hit: true, resultados } (sin barra de progreso)
       → NO: encola job, devuelve { job_id, cache_hit: false }
  ```
- **Detalle importante**: la caché debe guardar **resultados ya verificados**, no crudos. Si guardas un precio "sospechoso", lo sirves a otro usuario. Filtra antes de cachear.
- **Invalidación**: TTL 24 h + invalidación manual cuando tú relanzas ingesta diaria (puedes hacer `DEL` por patrón o usar versión en la clave: `v2:hash`).

### 1.2 Entornos dev y prod
- **`docker-compose.dev.yml`** y **`docker-compose.prod.yml`** (o `.env.dev` / `.env.prod` + un compose base). Diferencias:
  - dev: hot-reload, datos seed, Postgres local, sin TLS, logs verbose.
  - prod: imágenes build, TLS en Caddy, réplica de lectura, logs JSON, Sentry activo.
- **Nunca** el mismo `.env`. Variables separadas y secretos distintos.
- En dev, datos de prueba: seed con 100 productos ficticios o reales de muestra.

### 1.3 Contenedor + Kubernetes/OpenShift
Aquí hay que ser claro: **tu requisito de "replicarse horizontalmente en K8s/OpenShift" es incompatible con "VPS único con docker-compose" como despliegue final**. No es contradictorio, es **evolutivo**:

| Fase | Despliegue | Cuándo |
|------|-----------|--------|
| MVP / dev | docker-compose en VPS | Ahora |
| Prod inicial | docker-compose en VPS + réplica lectura | Al lanzar |
| Escala | **Manifiestos K8s/OpenShift** (Deployment + Service + Ingress + HPA + ConfigMap + Secret) | Cuando el tráfico lo justifique |

Lo importante para que sea **portable a K8s desde el día 1**:
- **Stateless**: la API no guarda estado en disco. Sesiones en JWT o Redis. Uploads a S3/MinIO.
- **Config por entorno**: todo por variables de entorno (`pydantic-settings` en Python). Cero hardcode.
- **Healthchecks**: `/health/live` y `/health/ready` en la API. K8s los necesita.
- **12-factor**: logs a stdout, sin archivos locales, sin cron interno (el scheduler debe ser un proceso separado o un `CronJob` de K8s).
- **Migraciones**: job separado (`alembic upgrade head`) antes del deploy, no en el arranque de la API.
- **Un solo contenedor por proceso**: `api`, `worker`, `scheduler` como imágenes/Deployments distintos. Así escalas el worker sin tocar la API.

**Recomendación firme**: no montes K8s ahora. Pero **escribe los Dockerfiles y la configuración como si fueras a hacerlo** (stateless, env vars, healthchecks, procesos separados). Así el salto a OpenShift es escribir manifiestos, no refactorizar.

### 1.4 Cero secretos en código (penalización grave)
Bien. Reglas concretas:
- **`.env.example`** en el repo con claves vacías y comentarios. El `.env` real va en `.gitignore`.
- **`.gitignore`** con `.env*`, `*.pem`, `secrets/`, `*.key`.
- **Pre-commit hook** con `gitleaks` o `detect-secrets` que bloquee el commit si detecta un patrón de API key, password o token.
- **GitHub Actions**: secretos en `Settings → Secrets`, nunca en el YAML.
- **Producción**: secretos en **Docker secrets**, **K8s Secrets** (o mejor, **External Secrets Operator** con Vault/AWS Secrets Manager), o **SOPS** si es pequeño. Para MVP en VPS: `.env` con permisos `600` fuera del repo, o `docker secret`.
- **Rotación**: documenta cómo rotar cada secreto (Google OAuth, Microsoft OAuth, LLM API key, Postgres password).
- **Nunca** loguees secretos. Configura el logger para redactar `authorization`, `api_key`, `password`.
- **Variables sensibles en CI**: marca los secrets como "masked" en GitHub Actions.

Esto no es opcional: si un revisor encuentra una API key en un commit, es exactamente la "penalización grave" que mencionas.

### 1.5 BBDD replicada lectura/escritura
- **Primario (RW)** + **réplica (RO)** con streaming replication de Postgres.
- **En la app**: dos engines SQLAlchemy (`engine_rw`, `engine_ro`) y un patrón **CQRS ligero**:
  - Escrituras (`POST/PATCH/DELETE`, ingesta, jobs) → `engine_rw`.
  - Lecturas de API pública (`GET /comparar`, `GET /productos`, `GET /listas`) → `engine_ro`.
- **Cuidado con la latencia de replicación**: si un usuario crea una lista y la lee inmediatamente, la réplica puede no tenerla aún. Soluciones:
  - Lecturas "post-escritura" del mismo usuario → forzar `engine_rw` durante N segundos (sticky).
  - O usar `synchronous_commit` y monitorizar `pg_stat_replication`.
- **En docker-compose**: puedes simular con dos servicios Postgres + configuración de replica. En K8s/OpenShift: **operador de Postgres** (Crunchy, Zalando, CloudNativePG) que gestiona primario + réplicas + failover.
- **Migraciones**: solo contra el primario.

## 2. Correcciones al backlog

Añado/ajusto tareas:

### Épica 0 — Fundación (ajustada)
- [ ] Monorepo + `docker-compose.base.yml` + `.dev.yml` + `.prod.yml`
- [ ] `.env.example` + `.gitignore` + `gitleaks` en pre-commit
- [ ] Dockerfiles separados: `api`, `worker`, `scheduler`, `web`
- [ ] Healthchecks `/health/live` y `/health/ready`
- [ ] Configuración por entorno con `pydantic-settings` (cero hardcode)
- [ ] CI: lint + tests + build + `gitleaks` + `trivy` (escaneo de imagen)

### Épica 1 — Autenticación (sin cambios)

### Épica 2 — Modelo de datos (ajustada)
- [ ] Esquema + migraciones Alembic
- [ ] Dos engines SQLAlchemy (RW/RO) + política de routing
- [ ] Seed dev con datos de prueba

### Épica 3 — Ingesta (ajustada)
- [ ] Worker como proceso separado (no dentro de la API)
- [ ] Scheduler como proceso separado (no cron interno de la API)
- [ ] Productor + Verificador + reintento acotado
- [ ] **Cache de búsquedas en Redis con TTL 24 h** (nueva)
- [ ] Invalidación de caché al completar ingesta diaria (nueva)

### Épica 4 — Búsqueda y comparativa (ajustada)
- [ ] `POST /busquedas` → detecta cache hit/miss
- [ ] `GET /busquedas/{job_id}` → polling (estado + progreso)
- [ ] `GET /comparar` con orden y filtros (lectura desde réplica RO)
- [ ] Cálculo determinista €/L y ranking
- [ ] Cache de respuestas de comparación (Redis, TTL corto)

### Épica 5 — Frontend (ajustada)
- [ ] Flujo hero → resultados (sin barra si cache hit)
- [ ] Barra de progreso solo en cache miss (polling)
- [ ] Ficha producto con **histórico de precios** (MVP, ya confirmado)

### Épica 6 — Listas y % de ahorro (ajustada)
- [ ] CRUD listas + items
- [ ] **Caso de uso `CompararListaEntreCadenas`**: dado una lista mixta, calcular la misma cesta en cada cadena
- [ ] Cálculo de coste total por cadena + % de ahorro vs. la más cara / vs. media
- [ ] Definir fórmula exacta (ver pregunta abajo)

### Épica 7 — Operación (ajustada)
- [ ] Postgres primario + réplica en compose (dev) y operador en K8s (prod futuro)
- [ ] Backups del primario
- [ ] Rotación de secretos documentada
- [ ] Manifiestos K8s/OpenShift **como plantilla** (no desplegar aún)
- [ ] ADRs en `decisions.md`

## 3. Una decisión de producto pendiente: fórmula del % de ahorro

Dices: "se comparará con listas de los mismos productos en diferentes supermercados". Necesito concretar:

**Opción A** — Ahorro vs. la cadena más cara de la cesta:
```
ahorro = (coste_cadena_mas_cara - coste_cadena_actual) / coste_cadena_mas_cara
```

**Opción B** — Ahorro vs. la media de las cadenas:
```
ahorro = (coste_medio - coste_cadena_actual) / coste_medio
```

**Opción C** — Ahorro vs. la cesta "óptima" (mezclando lo más barato de cada cadena):
```
ahorro = (coste_cesta_mixta_real - coste_cesta_optima) / coste_cesta_mixta_real
```

**Mi recomendación**: mostrar **A y C juntos**.
- **A** responde "¿cuánto ahorro comprando todo en Mercadona vs. todo en Carrefour?"
- **C** responde "¿cuánto pierdo por no ir a 3 supermercados?" (el coste real de la comodidad).
- **B** es la menos intuitiva para el usuario.

¿Confirmas A+C, o prefieres otra?

## 4. Lo que necesito para cerrar y escribir código

1. **Fórmula del % de ahorro**: ¿A+C, solo A, u otra?
2. **Orden por defecto**: precio unitario (€) o precio por kg/L? (Dijiste "menor a mayor por defecto" pero no la métrica base).
3. **Filtros del MVP**: ¿qué filtros concretos? (ej: solo con stock, rango de precio, marca, categoría). Necesito la lista para el esquema de `GET /comparar`.
4. **Ubicación del usuario**: ¿afecta a precios (algunas cadenas varían por provincia)? Si sí, hay que modelar `precios` con `provincia` o `tienda_id`.
5. **Idioma**: ¿solo español en MVP? (afecta a i18n desde el día 1 o después).

Con esas 5 respuestas te entrego:
- `docker-compose.base.yml` + `.dev.yml` + `.prod.yml`
- `.env.example` completo
- Esquema SQL inicial (con RW/RO y caché)
- Dockerfiles de `api`, `worker`, `scheduler`, `web`
- Backlog convertido en issues con estimaciones

¿Respondes a las 5 y arrancamos?

Perfecto, con esto ya puedo cerrar la arquitectura. Te respondo a las 5 con las decisiones tomadas y sus consecuencias técnicas, y luego te entrego el paquete inicial.

## 1. Decisiones cerradas y sus consecuencias

### 1.1 % de ahorro = A + C
- **A**: `coste_cadena_mas_cara - coste_cadena_actual` / `coste_cadena_mas_cara`
- **C**: `coste_cesta_mixta_real - coste_cesta_optima` / `coste_cesta_mixta_real`
- **Consecuencia**: necesitas un caso de uso `CalcularAhorroLista` que recibe `lista_id` + `cadenas_seleccionadas` y devuelve, por cada cadena, el coste de la cesta completa + el % A, y además el coste de la cesta óptima + el % C.
- **Complejidad**: media. El cálculo de "cesta óptima" es un `min(precio)` por producto entre cadenas seleccionadas. La "cesta mixta real" es el coste de la lista tal cual la compró el usuario (producto → cadena donde lo compró). Si un producto no existe en una cadena, se marca como `no_disponible` y se excluye del cálculo de esa cadena (con aviso en UI).

### 1.2 Orden por defecto: precio unitario (€), con cambio a €/kg-L
- **Consecuencia**: `GET /comparar` acepta `?orden=precio_unitario|precio_kg_l|relevancia`. Por defecto `precio_unitario`.
- En frontend, un selector visible para cambiar el orden sin relanzar búsqueda (los datos ya están en cliente).

### 1.3 Filtros MVP: todos los del ejemplo
- **Stock** (`solo_con_stock`), **rango de precio** (`precio_min`, `precio_max`), **marca** (`marca`), **categoría** (`categoria`).
- **Consecuencia**: la tabla `productos` necesita `marca` y `categoria` (nullable). La tabla `precios` necesita `disponible` (bool). El endpoint `GET /comparar` los acepta como query params y los aplica en SQL (no en memoria, para que escale).
- Si no hay stock fiable, `disponible` se marca `null` y el filtro `solo_con_stock=true` excluye los `null` (documentado en UI).

### 1.4 Ubicación del usuario afecta a precios
- **Consecuencia en modelo**: `precios` necesita `ambito` (`nacional` | `provincia`) y `provincia` (nullable). Si `ambito=nacional`, `provincia=null`. Si `ambito=provincia`, `provincia` obligatoria.
- **Resolución de precio para un usuario**:
  ```
  1. ¿Usuario tiene provincia? → buscar precio con ambito=provincia y provincia=X
  2. Si no existe → fallback a ambito=nacional
  3. Si no existe nacional → producto no disponible
  ```
- **Aviso en UI**: si el usuario no tiene ubicación, banner "Mostrando precios genéricos. Añade tu ubicación para precios de tu provincia."
- **Consecuencia en caché**: la clave de caché debe incluir `provincia` (o `nacional`). Dos usuarios de provincias distintas no comparten caché.
- **Consecuencia en ingesta**: el productor debe intentar precio provincial primero; si no, nacional. El verificador registra el ámbito.

### 1.5 Idioma: español en MVP, i18n preparado
- **Consecuencia**: no montes i18n completo ahora, pero **no hardcodees strings en componentes**. Usa un archivo `locales/es.json` desde el día 1 y una función `t(key)`. Añadir `en.json` después es trivial.
- Backend: mensajes de error en códigos (`PRODUCTO_NO_ENCONTRADO`), no en texto. El frontend traduce.
- BD: campos de texto libre (nombres de producto) se guardan tal cual vienen; no traduces datos.

## 2. Paquete inicial (lo que te entrego ahora)

### 2.1 Estructura del monorepo

```
/app
  /api
    /src
      /dominio
        /productos
        /precios
        /listas
        /usuarios
        /busquedas
      /aplicacion
        /buscar_producto
        /comparar_lista
        /calcular_ahorro
        /gestionar_listas
      /puertos
        repositorios.py
        productor.py
        verificador.py
        cache.py
        auth.py
      /adaptadores
        /persistencia
        /ingesta
        /cache
        /auth
      /api_http
        /v1
          busquedas.py
          comparar.py
          listas.py
          usuarios.py
      config.py          # pydantic-settings
      main.py
    Dockerfile
    pyproject.toml
  /web
    /src
      /app
      /components
      /lib
      /locales
        es.json
    Dockerfile
    package.json
  /infra
    docker-compose.base.yml
    docker-compose.dev.yml
    docker-compose.prod.yml
    /caddy
      Caddyfile
    /postgres
      init-replica.sh
    /k8s                  # plantillas, no desplegar aún
      api-deployment.yaml
      worker-deployment.yaml
      scheduler-cronjob.yaml
      web-deployment.yaml
      postgres-cluster.yaml
  .env.example
  .gitignore
  .pre-commit-config.yaml
  README.md
  decisions.md
```

### 2.2 `.env.example`

```env
# ===== Entorno =====
APP_ENV=dev                      # dev | prod
APP_SECRET_KEY=                  # genera con: openssl rand -hex 32
APP_BASE_URL=http://localhost:8000
WEB_BASE_URL=http://localhost:3000

# ===== Base de datos =====
POSTGRES_USER=app
POSTGRES_PASSWORD=
POSTGRES_DB=precios
DATABASE_URL_RW=postgresql+asyncpg://app:${POSTGRES_PASSWORD}@postgres-primary:5432/precios
DATABASE_URL_RO=postgresql+asyncpg://app:${POSTGRES_PASSWORD}@postgres-replica:5432/precios

# ===== Redis =====
REDIS_URL=redis://redis:6379/0
CACHE_TTL_SEGUNDOS=86400

# ===== Auth (Google) =====
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:3000/api/auth/callback/google

# ===== Auth (Microsoft) =====
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
MICROSOFT_TENANT_ID=common
MICROSOFT_REDIRECT_URI=http://localhost:3000/api/auth/callback/microsoft

# ===== LLM (productor de precios) =====
LLM_PROVIDER=                    # ej: openai | anthropic | xai
LLM_API_KEY=
LLM_MODEL=
LLM_MAX_REINTENTOS=3

# ===== Observabilidad =====
SENTRY_DSN=
LOG_LEVEL=INFO

# ===== Rate limit =====
RATE_LIMIT_BUSQUEDAS_POR_MINUTO=10
```

### 2.3 `docker-compose.base.yml` (extracto clave)

```yaml
services:
  postgres-primary:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pg_primary:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      retries: 10

  postgres-replica:
    image: postgres:16
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
      PRIMARY_HOST: postgres-primary
    volumes:
      - pg_replica:/var/lib/postgresql/data
    depends_on:
      postgres-primary:
        condition: service_healthy

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  api:
    build: ./api
    env_file: .env
    depends_on:
      postgres-primary:
        condition: service_healthy
      redis:
        condition: service_started
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/live"]
      interval: 10s

  worker:
    build: ./api
    command: ["python", "-m", "src.worker"]
    env_file: .env
    depends_on:
      postgres-primary:
        condition: service_healthy
      redis:
        condition: service_started

  scheduler:
    build: ./api
    command: ["python", "-m", "src.scheduler"]
    env_file: .env
    depends_on:
      redis:
        condition: service_started

  web:
    build: ./web
    env_file: .env
    ports:
      - "3000:3000"
    depends_on:
      - api

  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes:
      - ./infra/caddy/Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    depends_on:
      - api
      - web

volumes:
  pg_primary:
  pg_replica:
  redis_data:
  caddy_data:
```

`docker-compose.dev.yml` añade hot-reload y seed. `docker-compose.prod.yml` usa imágenes build, TLS y logs JSON.

### 2.4 Esquema SQL inicial (resumen)

```sql
-- Usuarios
CREATE TABLE usuarios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,              -- google | microsoft
  provider_id TEXT NOT NULL,
  email TEXT NOT NULL,
  nombre TEXT,
  provincia TEXT,                      -- nullable
  avatar_url TEXT,
  creado_en TIMESTAMPTZ DEFAULT now(),
  UNIQUE (provider, provider_id)
);

-- Cadenas
CREATE TABLE cadenas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,           -- dia | carrefour | mercadona
  nombre TEXT NOT NULL,
  logo_svg TEXT NOT NULL               -- ruta en /public/logos
);

-- Productos (canónicos, normalizados)
CREATE TABLE productos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  nombre TEXT NOT NULL,
  marca TEXT,
  categoria TEXT,
  formato TEXT,                        -- "1L", "750ml"
  litros_o_kg NUMERIC,                 -- para €/L o €/kg
  ean TEXT,                            -- si disponible
  creado_en TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_productos_nombre_trgm ON productos USING gin (nombre gin_trgm_ops);

-- Mapeo producto canónico ↔ producto en cada cadena
CREATE TABLE productos_cadena (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  producto_id UUID REFERENCES productos(id),
  cadena_id UUID REFERENCES cadenas(id),
  url_producto TEXT NOT NULL,
  nombre_en_cadena TEXT,
  UNIQUE (producto_id, cadena_id)
);

-- Precios (histórico)
CREATE TABLE precios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  producto_cadena_id UUID REFERENCES productos_cadena(id),
  precio_eur NUMERIC(10,2) NOT NULL,
  precio_por_litro_kg NUMERIC(10,4),
  disponible BOOLEAN,                  -- null = desconocido
  promocion TEXT,
  ambito TEXT NOT NULL DEFAULT 'nacional',   -- nacional | provincia
  provincia TEXT,
  estado TEXT NOT NULL,                -- verificado | sospechoso | rechazado
  url_fuente TEXT NOT NULL,
  fecha_consulta TIMESTAMPTZ NOT NULL,
  creado_en TIMESTAMPTZ DEFAULT now(),
  CHECK (ambito = 'nacional' OR provincia IS NOT NULL)
);
CREATE INDEX idx_precios_pc_fecha ON precios (producto_cadena_id, fecha_consulta DESC);

-- Búsquedas (jobs)
CREATE TABLE busquedas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  usuario_id UUID REFERENCES usuarios(id),
  query TEXT NOT NULL,
  cadenas TEXT[] NOT NULL,
  provincia TEXT,
  estado TEXT NOT NULL DEFAULT 'pendiente',  -- pendiente | en_progreso | completada | fallida
  progreso INT DEFAULT 0,
  cache_key TEXT NOT NULL,
  creado_en TIMESTAMPTZ DEFAULT now(),
  completado_en TIMESTAMPTZ
);

-- Listas
CREATE TABLE listas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  usuario_id UUID REFERENCES usuarios(id),
  nombre TEXT NOT NULL,
  creado_en TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE lista_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lista_id UUID REFERENCES listas(id) ON DELETE CASCADE,
  producto_id UUID REFERENCES productos(id),
  cadena_compra_id UUID REFERENCES cadenas(id),  -- dónde lo compró el usuario
  cantidad INT DEFAULT 1,
  precio_snapshot NUMERIC(10,2),                -- precio al añadir
  creado_en TIMESTAMPTZ DEFAULT now()
);
```

Notas:
- `pg_trgm` para búsqueda difusa de productos (sin Elasticsearch).
- `precios` es append-only (histórico). La "última foto" se obtiene con `DISTINCT ON` o una vista materializada.
- La réplica RO sirve todas las lecturas de `GET /comparar`, `GET /productos`, `GET /listas`. Las escrituras y migraciones van al primario.

### 2.5 Healthchecks y arranque

```python
# src/main.py (extracto)
from fastapi import FastAPI
from src.config import settings

app = FastAPI()

@app.get("/health/live")
def live():
    return {"status": "ok"}

@app.get("/health/ready")
async def ready():
    # comprueba RW, RO y Redis
    await check_db_rw()
    await check_db_ro()
    await check_redis()
    return {"status": "ready"}
```

## 3. Backlog final (issues con estimación)

| # | Issue | Épica | Est. |
|---|-------|-------|------|
| 1 | Monorepo + compose base/dev/prod | 0 | 2d |
| 2 | `.env.example` + gitleaks + CI | 0 | 1d |
| 3 | Dockerfiles api/worker/scheduler/web | 0 | 1d |
| 4 | Deploy VPS con Caddy | 0 | 1d |
| 5 | OAuth Google + Microsoft (Auth.js) | 1 | 2d |
| 6 | Middleware sesión + `GET /me` | 1 | 1d |
| 7 | Esquema SQL + Alembic + seed | 2 | 2d |
| 8 | Engines RW/RO + routing | 2 | 1d |
| 9 | Puerto `Productor` + impl LLM | 3 | 2d |
| 10 | Puerto `Verificador` + impl fetch+reglas | 3 | 2d |
| 11 | Caso de uso `BuscarProducto` + reintento | 3 | 2d |
| 12 | Cola Postgres `SKIP LOCKED` + worker | 3 | 2d |
| 13 | Scheduler diario (proceso aparte) | 3 | 1d |
| 14 | Caché Redis TTL 24h + invalidación | 3 | 1d |
| 15 | `POST /busquedas` (cache hit/miss) | 4 | 1d |
| 16 | `GET /busquedas/{id}` polling | 4 | 1d |
| 17 | `GET /comparar` con orden/filtros | 4 | 2d |
| 18 | Cálculo €/L + ranking (dominio) | 4 | 1d |
| 19 | Layout minimalista + menú lateral | 5 | 2d |
| 20 | Hero buscador + selector SVG cadenas | 5 | 2d |
| 21 | Flujo hero→resultados + barra progreso | 5 | 2d |
| 22 | Cards producto + imagen clicable | 5 | 2d |
| 23 | Ficha producto + histórico | 5 | 2d |
| 24 | CRUD listas + items | 6 | 2d |
| 25 | `CalcularAhorroLista` (A+C) | 6 | 3d |
| 26 | Vista lista: coste, % A, % C | 6 | 2d |
| 27 | Postgres primario + réplica (compose) | 7 | 1d |
| 28 | Backups + Sentry + UptimeRobot | 7 | 1d |
| 29 | Manifiestos K8s plantilla | 7 | 2d |
| 30 | ADRs en `decisions.md` | 7 | 1d |
| 31 | i18n base (`locales/es.json` + `t()`) | 5 | 1d |

**Total aproximado**: ~50 días de desarrollo a tiempo completo, o ~3 meses a medio tiempo.

## 4. Siguiente paso concreto

Te propongo este orden de ejecución:

1. **Yo escribo**: `docker-compose.base/dev/prod`, `.env.example`, `.gitignore`, `.pre-commit-config.yaml`, `Dockerfiles` y `Caddyfile`. Es la Épica 0 completa y desbloquea todo lo demás.
2. **Tú validas** que `docker compose -f docker-compose.base.yml -f docker-compose.dev.yml up` levanta Postgres primario + réplica + Redis + API + web sin errores.
3. **Después**: esquema SQL + migraciones + seed (Épica 2), y ya podemos probar el primer endpoint real.

----

