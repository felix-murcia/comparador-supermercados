# decisions.md

**Propósito**: Registro de decisiones arquitectónicas (ADRs ligeros). Append-only. Cada decisión relevante que afecte a la arquitectura, el modelo de datos o el comportamiento del producto debe quedar registrada aquí antes de implementarse.

**Formato**: ver `AGENTS.md` sección 9.
**Última actualización**: 2026-10-19

---

## Índice

- [ADR-001](#adr-001-elección-de-stack-tecnológico)
- [ADR-002](#adr-002-tailwind-css-para-estilos)
- [ADR-003](#adr-003-autenticación-con-authjs-oauth-google--microsoft)
- [ADR-004](#adr-004-estrategia-de-ingesta-productor-llm--verificador-determinista)
- [ADR-005](#adr-005-caché-de-búsquedas-en-redis-con-ttl-24-h)
- [ADR-006](#adr-006-postgres-primario--réplica-cqrs-ligero)
- [ADR-007](#adr-007-cola-de-jobs-en-postgres-con-skip-locked-mvp)
- [ADR-008](#adr-008-fórmula-de--de-ahorro-a--c)
- [ADR-009](#adr-009-resolución-de-precios-por-provincia-con-fallback-nacional)
- [ADR-010](#adr-010-portabilidad-a-kubernetesopenshift-sin-desplegar-aún)

---

## ADR-001: Elección de stack tecnológico

**Fecha**: 2026-10-19
**Estado**: aceptado
**Contexto**: Necesitamos un stack para un comparador de precios con backend, frontend SSR, ingesta asíncrona con LLM, BD relacional con histórico y caché. El equipo es una sola persona, el MVP debe estar en ~3 meses y la app debe ser portable a K8s/OpenShift en el futuro.

**Decisión**:
- **Backend**: Python 3.12 + FastAPI.
- **Frontend**: Next.js 14 (App Router) + React + TypeScript.
- **BD**: PostgreSQL 16.
- **Caché/Cola**: Redis 7.
- **Reverse proxy**: Caddy 2.
- **Contenedores**: Docker + docker-compose.
- **CI/CD**: GitHub Actions.
- **Observabilidad**: Sentry + UptimeRobot.

**Consecuencias**:
- ✅ Ecosistema Python inmejorable para LLM, scraping y async.
- ✅ Next.js da SSR (crítico para SEO de un comparador) y React maduro.
- ✅ Postgres cubre histórico, JSONB y búsqueda difusa (`pg_trgm`) sin Elasticsearch.
- ✅ Caddy elimina la configuración manual de TLS.
- ⚠️ Dos lenguajes (Python + TS) aumentan el contexto mental, pero es estándar en el sector.
- ⚠️ FastAPI + async requiere disciplina para no bloquear el event loop.

**Alternativas consideradas**:
- **Node/Express + Next.js**: un solo lenguaje, pero peor ecosistema LLM/scraping y menos maduro para data pipelines.
- **Django + DRF**: más baterías incluidas, pero más pesado y menos flexible para async.
- **Go + templ**: rendimiento excelente, pero desarrollo más lento para MVP y ecosistema LLM más pobre.
- **Astro + React**: buen SSR, pero menos ecosistema de auth y estado que Next.js.

---

## ADR-002: Tailwind CSS para estilos

**Fecha**: 2026-10-19
**Estado**: aceptado
**Contexto**: Necesitamos un sistema de estilos para una UI minimalista tipo Google, con un solo desarrollador y sin diseñador dedicado. Debe ser rápido de iterar y consistente.

**Decisión**: Tailwind CSS con configuración por defecto y tokens de diseño en `tailwind.config.ts`.

**Consecuencias**:
- ✅ Iteración rápida sin cambiar de archivo.
- ✅ Consistencia por defecto (espaciado, colores, tipografía).
- ✅ Purga automática en build → CSS mínimo.
- ✅ Fácil de auditar accesibilidad (contraste, foco).
- ⚠️ JSX con muchas clases puede volverse ruidoso. Mitigación: extraer primitivos a `components/ui/`.
- ⚠️ Curva de aprendizaje inicial para quien no lo haya usado.

**Alternativas consideradas**:
- **CSS Modules**: más explícito, pero más lento de iterar y sin sistema de tokens.
- **Styled Components / Emotion**: CSS-in-JS, runtime cost y peor integración con Server Components.
- **Vanilla CSS + variables**: control total, pero requiere construir el sistema desde cero.

---

## ADR-003: Autenticación con Auth.js (OAuth Google + Microsoft)

**Fecha**: 2026-10-19
**Estado**: aceptado
**Contexto**: El requisito es login con Google y Microsoft. No hay login con contraseña propia. Necesitamos sesión persistente, validación en backend y mínima superficie de ataque.

**Decisión**: **Auth.js (NextAuth)** en Next.js con proveedores Google y Microsoft Entra ID. Sesión en JWT firmado. El backend FastAPI valida el token en cada request.

**Consecuencias**:
- ✅ OAuth out-of-the-box para ambos proveedores.
- ✅ Sesión gestionada en el frontend, sin tabla de sesiones en BD.
- ✅ Backend solo valida JWT (sin estado).
- ✅ Stateless → portable a K8s sin cambios.
- ⚠️ JWT no se puede revocar individualmente sin lista negra. Mitigación: TTL corto + refresh token.
- ⚠️ Dependencia de Auth.js para cambios de API entre versiones mayores.

**Alternativas consideradas**:
- **Authlib + FastAPI**: control total, pero más código y más superficie de ataque.
- **Supabase Auth / Clerk**: rápidos, pero acoplamiento a un proveedor externo y coste futuro.
- **Keycloak**: potente, pero sobredimensionado para MVP y complica el despliegue.

---

## ADR-004: Estrategia de ingesta (productor LLM + verificador determinista)

**Fecha**: 2026-10-19
**Estado**: aceptado
**Contexto**: El scraping directo de DIA, Carrefour y Mercadona es inviable por anti-bot, renderizado JS y mantenimiento. La alternativa elegida es usar un LLM con búsqueda web como productor de precios, pero un LLM puede alucinar. Necesitamos un mecanismo de verificación fiable y barato.

**Decisión**: Patrón **productor + verificador**:
1. **Productor** (LLM con búsqueda): devuelve JSON estricto con `precio_eur`, `url_fuente` obligatoria, `formato`, `confianza` y `motivo_si_no_encontrado`.
2. **Verificador** (determinista, sin LLM): hace `GET` a `url_fuente`, comprueba que el precio aparece en el HTML, valida coherencia €/L vs. formato, y compara con el último precio conocido (umbral de desviación 30%).
3. **Reintento acotado**: máximo 3 pasadas. Si no converge, se marca como `no_verificado` y se excluye de la UI principal.
4. **Estados**: `verificado`, `sospechoso`, `rechazado`. Solo `verificado` se cachea y se muestra.

**Consecuencias**:
- ✅ El LLM nunca es la fuente de verdad: solo propone.
- ✅ Verificación reproducible y barata (un `GET` + reglas).
- ✅ Cada precio guardado tiene URL + fecha + estado → auditable.
- ✅ Coste controlado: el 90% de verificaciones son gratis.
- ⚠️ Dependencia de un proveedor de LLM con búsqueda. Mitigación: puerto `Productor` permite cambiar de proveedor sin tocar el resto.
- ⚠️ Latencia de ingesta alta (segundos por producto). Mitigación: worker asíncrono + caché.

**Alternativas consideradas**:
- **Scraping directo**: descartado tras meses de intentos fallidos por anti-bot.
- **APIs oficiales**: no existen para estas cadenas.
- **Solo LLM sin verificación**: inaceptable por alucinaciones.
- **Solo verificador humano**: no escala.

---

## ADR-005: Caché de búsquedas en Redis con TTL 24 h

**Fecha**: 2026-10-19
**Estado**: aceptado
**Contexto**: Muchos usuarios harán búsquedas similares. Sin caché, cada búsqueda consume LLM (caro) y tarda segundos. Con caché, la mayoría de búsquedas son instantáneas y gratis.

**Decisión**:
- **Backend de caché**: Redis 7.
- **TTL**: 24 horas.
- **Clave**: hash SHA-256 de `(query_normalizada, cadenas_ordenadas, orden, filtros, provincia)`.
- **Contenido**: solo resultados `verificado`. Los `sospechoso` y `rechazado` no se cachean.
- **Invalidación**: TTL natural + invalidación manual (por prefijo de versión) al completar la ingesta diaria.
- **Versionado**: prefijo `v1:` en la clave para permitir invalidación masiva sin `SCAN`.

**Consecuencias**:
- ✅ Búsquedas repetidas instantáneas y gratis.
- ✅ Reduce drásticamente el coste de LLM.
- ✅ El indicador de carga solo aparece en cache miss (requisito de UX).
- ⚠️ Un precio puede estar hasta 24 h desactualizado. Mitigación: invalidación tras ingesta diaria + fecha visible en UI.
- ⚠️ Redis es un punto único de fallo. Mitigación: si Redis cae, la app sigue funcionando (cache miss → ingesta). Redis es optimización, no dependencia crítica.

**Alternativas consideradas**:
- **Caché en Postgres**: más simple (una tabla), pero peor TTL nativo y peor rendimiento en lecturas calientes.
- **Caché en memoria del proceso**: no sirve con múltiples réplicas (stateless).
- **CDN**: no aplica a resultados dinámicos por usuario/provincia.

---

## ADR-006: Postgres primario + réplica (CQRS ligero)

**Fecha**: 2026-10-19
**Estado**: aceptado
**Contexto**: Requisito explícito de BBDD replicada y sincronizada, una para lectura y otra para escritura/actualización. La ingesta y las escrituras de usuario compiten con las lecturas de la API pública.

**Decisión**:
- **Primario (RW)**: escrituras, migraciones, ingesta.
- **Réplica (RO)**: lecturas de API pública (`GET /comparar`, `GET /productos`, `GET /listas`).
- **Routing**: dos engines SQLAlchemy (`engine_rw`, `engine_ro`). Casos de uso de lectura usan `engine_ro`; escritura usa `engine_rw`.
- **Migraciones**: solo contra primario, como job separado (no en arranque de API).
- **Sticky post-escritura**: si un usuario crea una lista y la lee inmediatamente, forzar `engine_rw` durante N segundos (evita lag de replicación).
- **Infra dev**: dos servicios Postgres en compose con streaming replication.
- **Infra prod futuro**: operador de Postgres en K8s (CloudNativePG o Crunchy).

**Consecuencias**:
- ✅ Lecturas escalan horizontalmente añadiendo réplicas.
- ✅ Escrituras de ingesta no bloquean lecturas.
- ✅ Cumple el requisito de replicación.
- ⚠️ Lag de replicación puede causar lecturas obsoletas. Mitigación: sticky post-escritura + monitorización de `pg_stat_replication`.
- ⚠️ Más complejidad operativa que una sola BD. Mitigación: compose para dev, operador para prod.

**Alternativas consideradas**:
- **Una sola BD**: más simple, pero incumple el requisito y no escala lecturas.
- **Sharding**: sobredimensionado para MVP.
- **BD externa gestionada** (RDS, Neon): válida, pero añade coste y dependencia de proveedor.

---

## ADR-007: Cola de jobs en Postgres con SKIP LOCKED (MVP)

**Fecha**: 2026-10-19
**Estado**: aceptado
**Contexto**: La ingesta es asíncrona (búsquedas con LLM tardan segundos). Necesitamos una cola fiable para que el worker procese jobs. Opciones: Redis queue (RQ/Celery) o Postgres con `SKIP LOCKED`.

**Decisión**: Para el MVP, **cola en Postgres** usando `SELECT ... FOR UPDATE SKIP LOCKED` sobre la tabla `busquedas` (y futura `ingesta_jobs`). Redis se reserva para caché.

**Consecuencias**:
- ✅ Una pieza menos en infra (no hace falta RQ/Celery).
- ✅ Jobs persistentes: si el worker cae, el job no se pierde.
- ✅ Transaccionalidad con la BD (el job y su resultado viven en la misma BD).
- ✅ Métricas de cola con SQL estándar.
- ⚠️ Throughput menor que Redis queue. Suficiente para cientos de jobs/día.
- ⚠️ Requiere worker con polling (cada 1–2 s). Aceptable.
- 🔄 **Evolución**: si el throughput se vuelve cuello de botella, migrar a RQ/Celery con Redis. El puerto `ColaJobs` permite el cambio sin tocar casos de uso.

**Alternativas consideradas**:
- **RQ (Redis Queue)**: simple, pero añade Redis como dependencia crítica (si cae, se pierden jobs).
- **Celery**: potente, pero pesado y con más configuración.
- **Kafka/RabbitMQ**: sobredimensionado para MVP.

---

## ADR-008: Fórmula de % de ahorro (A + C)

**Fecha**: 2026-10-19
**Estado**: aceptado
**Contexto**: El usuario quiere saber cuánto ahorra con su cesta. Hay varias formas de definir "ahorro". La decisión afecta al caso de uso `CalcularAhorroLista` y a la UI.

**Decisión**: Mostrar dos métricas complementarias:

**A) Ahorro vs. cadena más cara**:
```
coste_cadena = sum(precio_producto_en_cadena)  # solo productos disponibles en esa cadena
coste_mas_cara = max(coste_cadena para cada cadena seleccionada)
% A = (coste_mas_cara - coste_cadena) / coste_mas_cara
```
Responde: "¿cuánto ahorro comprando todo en esta cadena vs. la más cara?"

**C) Ahorro vs. cesta óptima**:
```
coste_optimo = sum(min(precio_producto entre cadenas seleccionadas))
coste_mixta_real = sum(precio donde el usuario compró cada producto)
% C = (coste_mixta_real - coste_optimo) / coste_mixta_real
```
Responde: "¿cuánto pierdo por no ir a 3 supermercados?" (coste de la comodidad).

**Reglas**:
- Productos no disponibles en una cadena se excluyen de esa cadena con aviso en UI.
- Si un producto no está en ninguna cadena, se excluye de todos los cálculos con aviso.
- Si solo hay una cadena seleccionada, % A no aplica (mostrar "—").
- Si `coste_mixta_real == 0`, % C no aplica.

**Consecuencias**:
- ✅ Cubre las dos preguntas que se hace el usuario.
- ✅ Transparente: el usuario ve el coste absoluto y el porcentaje.
- ⚠️ Más lógica de cálculo. Mitigación: caso de uso puro, testeable sin BD.
- ⚠️ UI con dos métricas puede confundir. Mitigación: tooltips explicativos.

**Alternativas consideradas**:
- **Solo A**: simple, pero no responde "¿cuánto pierdo por comodidad?".
- **Solo B (vs. media)**: menos intuitiva.
- **Solo C**: no responde "¿cuánto ahorro comprando todo en un sitio?".

---

## ADR-009: Resolución de precios por provincia con fallback nacional

**Fecha**: 2026-10-19
**Estado**: aceptado
**Contexto**: Algunas cadenas varían precios por provincia. El usuario puede o no tener provincia configurada. Necesitamos una política clara y consistente.

**Decisión**:
- `precios` tiene `ambito` (`nacional` | `provincia`) y `provincia` (nullable).
- **Resolución para un usuario**:
  1. Si `usuario.provincia` existe → buscar precio `ambito=provincia AND provincia=X`.
  2. Si no existe → fallback a `ambito=nacional`.
  3. Si no existe → producto no disponible.
- **Si el usuario no tiene provincia** → usar `ambito=nacional` directamente.
- **UI**: banner "Mostrando precios genéricos. Añade tu ubicación para precios de tu provincia." cuando no hay provincia.
- **Caché**: la clave incluye `provincia` (o `nacional`). Dos usuarios de provincias distintas no comparten caché.
- **Ingesta**: el productor intenta precio provincial primero; si no, nacional. El verificador registra el ámbito.

**Consecuencias**:
- ✅ Precios relevantes para el usuario cuando hay datos provinciales.
- ✅ Fallback claro y predecible.
- ✅ Caché correcta por provincia.
- ⚠️ Más filas en `precios` (una por provincia + nacional). Mitigación: solo se ingesta provincia si la cadena la expone.
- ⚠️ Cobertura provincial desigual. Mitigación: aviso en UI cuando se usa nacional.

**Alternativas consideradas**:
- **Solo nacional**: simple, pero ignora variación provincial real.
- **Solo provincia**: rompe para usuarios sin provincia.
- **Provincia sin fallback**: producto no disponible aunque exista nacional. Mala UX.

---

## ADR-010: Portabilidad a Kubernetes/OpenShift sin desplegar aún

**Fecha**: 2026-10-19
**Estado**: aceptado
**Contexto**: El requisito es que la app pueda replicarse horizontalmente en K8s/OpenShift. Pero montar K8s en MVP es sobredimensionado para un solo desarrollador y bajo tráfico. Necesitamos un camino evolutivo sin refactor.

**Decisión**: Diseñar **como si** fuéramos a K8s desde el día 1, pero desplegar en docker-compose en VPS hasta que el tráfico lo justifique.

**Reglas de diseño obligatorias**:
- **Stateless**: la API no guarda estado en disco. Sesiones en JWT. Uploads a S3/MinIO (futuro).
- **Config por env vars**: `pydantic-settings`, cero hardcode.
- **Healthchecks**: `/health/live` y `/health/ready` en la API.
- **12-factor**: logs a stdout (JSON en prod), sin archivos locales, sin cron interno.
- **Procesos separados**: `api`, `worker`, `scheduler` como contenedores/imágenes distintas.
- **Migraciones**: job separado (`alembic upgrade head`), no en arranque de API.
- **Manifiestos K8s**: plantillas en `infra/k8s/` (Deployment, Service, Ingress, HPA, ConfigMap, Secret). No se despliegan aún.

**Consecuencias**:
- ✅ Salto a K8s = escribir manifiestos, no refactorizar.
- ✅ MVP simple y barato (VPS + compose).
- ✅ Escalado horizontal trivial cuando llegue el momento.
- ⚠️ Disciplina constante para no romper las reglas (ej: no meter estado en la API). Mitigación: revisión en PR + checklist en `AGENTS.md`.

**Alternativas consideradas**:
- **K8s desde el día 1**: sobredimensionado, ralentiza MVP, más superficie de error.
- **Solo VPS sin pensar en K8s**: deuda técnica que obliga a refactor.
- **Serverless (Lambda/Cloud Run)**: válido, pero cambia el modelo de worker/scheduler y complica el desarrollo local.

---

## ADR-011: Imagen propia de Caddy con plugin de rate limit

**Fecha**: 2026-10-19
**Estado**: aceptado
**Contexto**: El rate limit en el borde es requisito para `/api/v1/busquedas` (endpoint costoso). Caddy no incluye `rate_limit` en su distribución estándar; es un módulo externo (`github.com/mholt/caddy-ratelimit`). La imagen oficial `caddy:2-alpine` no puede cargarlo.

**Decisión**: Compilar una imagen propia de Caddy en `infra/caddy/Dockerfile` con Caddy `2.11.7` y `mholt/caddy-ratelimit@v0.1.0`. El Caddyfile aplica una zona por IP (`{remote_host}`) a `/api/v1/busquedas*`, con `RATE_LIMIT_BUSQUEDAS_POR_MINUTO` (10 por defecto) y ventana de 1 minuto. En dev sirve HTTP en `:80`; en prod usa `DOMAIN` para TLS automático.

**Consecuencias**:
- ✅ Rate limit antes de llegar a la API, sin lógica adicional en FastAPI.
- ✅ Una sola imagen reproducible con versiones fijadas.
- ⚠️ El build requiere red para descargar módulos Go y tarda más que usar la imagen oficial. Mitigación: caché de capas en CI/VPS.
- ⚠️ El contador es en memoria y por instancia. Suficiente para un único VPS; si se escala Caddy horizontalmente, habrá que usar almacenamiento compartido.

**Alternativas consideradas**:
- **Rate limit en FastAPI**: más código y la petición ya consume recursos de la API antes de limitarse.
- **Nginx**: válido, pero contradice ADR-001 y añade otra configuración.
- **Caddy oficial sin rate limit**: no cumple la aceptación de T0.6.
- **Plugin con build en cada arranque**: descartado por tiempo de arranque y reproducibilidad.

---

## ADR-012: Token de sesión HS256 compartido entre Auth.js y FastAPI

**Fecha**: 2026-10-19
**Estado**: aceptado
**Contexto**: Auth.js (NextAuth v4) cifra la sesión por defecto con un JWE (A256GCM + HKDF) que FastAPI no puede verificar sin reimplementar ese esquema. La Épica 1 exige validar el token en la API de forma stateless (RNF-02) con el mínimo código posible.

**Decisión**: Sobrescribir `jwt.encode`/`jwt.decode` de Auth.js para firmar la sesión como JWS HS256 con `NEXTAUTH_SECRET` (`jose` en web; `PyJWT` en FastAPI, T1.3). El token lleva los claims estándar (`sub`, `email`, `name`, `picture`, `iat`, `exp`) más `provider` y `provider_id` del proveedor OAuth. FastAPI valida firma, `exp` y algoritmo sin consultar la base de datos para autenticar cada petición.

**Consecuencias**:
- ✅ Verificación stateless en ambos servicios con una sola pieza de secret management (`NEXTAUTH_SECRET`).
- ✅ Rotar el secreto invalida todas las sesiones (aceptable en MVP; documentado).
- ⚠️ Los claims son legibles (JWS, no JWE). No incluir datos sensibles en el token.
- ⚠️ FastAPI debe rechazar explícitamente algoritmos distintos de HS256 (confusión de algoritmos).

**Alternativas consideradas**:
- **JWE por defecto de Auth.js**: la API necesitaría descifrar A256GCM+HKDF o consultar a Next.js en cada petición; más complejidad y acoplamiento.
- **Validar llamando a `/api/auth/session` desde FastAPI**: una petición extra por request; rompe el modelo stateless.
- **Sesiones en Redis**: descartado en MVP; añade estado y otro servicio que mantener.

---

## ADR-013: Gráfica del histórico con Recharts

**Fecha**: 2026-10-20
**Estado**: aceptado
**Contexto**: La ficha de producto (T5.6) necesita una gráfica de la evolución del precio por cadena. La web no tiene graphing library y el bundle manda: Next.js ya incluye React 18.

**Decisión**: Usar **Recharts** como librería de gráficas, con una serie por cadena y el rango temporal (1M/3M/6M/1A) como parámetro de la consulta. Se descarta Chart.js (no mantiene el estilo declarativo de React) y las gráficas SVG a mano (mantenimiento y ejes a coste de la vista).

**Consecuencias**:
- ✅ La gráfica encaja con el modelo de datos de React y no necesita canvas.
- ✅ Sin dependencias de pago ni de licence server-side.
- ⚠️ ~100 kB extra en el bundle de la ficha. Se aceptable: la ficha es una ruta secundaria y Recharts se carga solo allí (import dinámico cuando se implemente el refinamiento).

**Alternativas consideradas**:
- **Chart.js**: más ligero, pero obliga a imperar el DOM con refs y complica el SSR.
- **SVG propio**: sin dependencias, pero axes, tooltips y responsive son trabajo a medida.

---

## ADR-014: Progreso de la búsqueda con polling

**Fecha**: 2026-10-20
**Estado**: aceptado
**Contexto**: Al lanzar una búsqueda, la web necesita saber cuándo termina el job (T5.3) para pasar del indicador de carga a los resultados.

**Decisión**: La web **hace polling** a `GET /v1/busquedas/{id}` cada 1,5 s desde el navegador (vía el proxy de Next). El estado del job vive en la tabla `busquedas` y lo escribe el worker; no hay canales push.

**Consecuencias**:
- ✅ Sin WebSockets ni SSE: el estado ya está en la base de datos y el worker es un proceso aparte.
- ✅ Funciona igual detrás de proxies y balanceadores (no hay conexiones largas).
- ⚠️ Hasta 1,5 s de retraso entre el fin real del job y el cambio de vista. Se asume: el trabajo de ingesta tarda segundos o minutos.
- ⚠️ El indicador de carga es indeterminado (spinner): el job solo expone un progreso por cadenas completadas, que con una sola cadena salta de 0 a 100 y no aporta información.
- ⚠️ Una petición por usuario y cada 1,5 s mientras espera. El endpoint es de solo lectura y está cacheado por el borde.

**Alternativas consideradas**:
- **SSE**: menor latencia, pero obliga a mantener conexiones abiertas en el servidor de Next y en el proxy.
- **WebSocket**: más complejo y sin ventaja para un flujo de un solo sentido.

---

## ADR-015: Límite de peticiones en la aplicación y en el borde

**Fecha**: 2026-10-20
**Estado**: aceptado
**Contexto**: `POST /v1/busquedas` es el endpoint caro: lanza jobs de ingesta con LLM. El borde (Caddy) ya limita por IP (`ADR-011`).

**Decisión**: Mantener **los dos límites**: el del borde por IP (Caddy, 10 req/min) y uno **en la aplicación por usuario** (`RedisLimitador`, contador por minuto, `RATE_LIMIT_BUSQUEDAS_POR_MINUTO`). Si se supera, la API responde 429 `RATE_LIMIT`.

**Consecuencias**:
- ✅ El borde protege la infraestructura; la aplicación protege el presupuesto de LLM por cuenta (varias personas detrás de la misma IP siguen teniendo su propio límite).
- ✅ El límite por usuario es el que se puede facturar o afinar por plan.
- ⚠️ Redis pasa a ser dependencia del camino de escritura: si cae, el limitador deja pasar (fail-open) para no tumbar la app.

**Alternativas consideradas**:
- **Solo el borde**: un móvil detrás de CGNAT comparte cuota con toda la compañía.
- **Solo la aplicación**: el LLM se gastaría antes de que el borde filtre el ruido.

---

## ADR-016: El navegador nunca ve el token de la API

**Fecha**: 2026-10-20
**Estado**: aceptado
**Contexto**: La API valida el JWT de sesión que emite Auth.js (`ADR-012`). La web necesita llamar a la API (búsquedas, comparativa, listas) desde el navegador.

**Decisión**: Toda llamada a la API pasa por **un proxy en el servidor de Next.js** (`web/src/app/api/**`), que lee la cookie de sesión, extrae el token y reenvía la petición a FastAPI con la cabecera `Authorization`. El token **no viaja al navegador**.

**Consecuencias**:
- ✅ El JWT no está expuesto a JavaScript: un XSS no lo puede leer.
- ✅ No hace falta CORS: el navegador solo habla con su propio origen.
- ✅ Un único punto donde se auditan y registran las llamadas.
- ⚠️ Un salto extra (web → API) en cada llamada. Se compensa con la caché de Redis en la propia API (comparativa y resumen).

**Alternativas consideradas**:
- **Llamar a la API desde el navegador con el token**: requiere exponer el token en `useSession` y configurar CORS con credenciales.

---

## ADR-017: Sticky reads para los datos propios del usuario

**Fecha**: 2026-10-20
**Estado**: aceptado
**Contexto**: La API escribe en el primario y lee en la réplica. Tras escribir, el usuario quiere ver su cambio (su lista, su job), pero la réplica va retrasada.

**Decisión**: Cuando una petición escribe, se marca al usuario en Redis con el TTL `STICKY_READS_SEGUNDOS` (5 s). Durante ese tiempo sus lecturas van al primario en lugar de a la réplica. Las lecturas de datos **privados y recién escritos** (listas, items, resumen) usan además directamente el primario.

**Consecuencias**:
- ✅ El usuario ve de inmediato lo que acaba de hacer, sin esperas ni mensajes de error.
- ✅ La réplica sigue absorbiendo el tráfico de lectura pública (comparativa, catálogo).
- ⚠️ Un pico de lecturas al primario tras cada escritura de un usuario. Acotado por el TTL de 5 s.

**Alternativas consideradas**:
- **Esperar a la réplica**: deja al usuario viendo datos obsoletos.
- **Leer siempre del primario**: waste el motivo de tener una réplica.

---

## ADR-019: Reparto de rutas `/api/*` entre Next.js y FastAPI en Caddy

**Fecha**: 2026-10-20
**Estado**: aceptado
**Contexto**: El navegador nunca ve el token de sesión (ADR-012 y ADR-016), así que todo lo autenticado pasa por proxies de Next.js (`/api/comparar`, `/api/busquedas`, `/api/me`, `/api/listas`). Pero Caddy enviaba **todo** `/api/*` a FastAPI quitando el prefijo, así que esos proxies nunca se ejecutaban en el despliegue y la UI devolvía `404` (comparativa, búsqueda, perfil y listas). Además, la web resolvía la API con `NEXT_PUBLIC_API_URL`, que en producción valía el dominio público: el proxy pedía `https://<dominio>/v1/comparar` (sin `/api`) y recibía `{}`.

**Decisión**:
- Caddy enruta a `web:3000` las rutas que Next.js proxya (`/api/auth/*`, `/api/comparar*`, `/api/busquedas*`, `/api/me*`, `/api/listas*`) y reserva el comodín `handle_path /api/*` → `api:8000` para la API pública (`/api/v1/*`, `/api/health/*`).
- La web llama a FastAPI por la red interna con la variable `API_INTERNAL_URL` (por defecto `http://api:8000`), no con el dominio público.
- El middleware de Next.js deja de proteger `/api/*`: los proxies devuelven el `401` JSON de la API en lugar de una redirección HTML al login.

**Consecuencias**:
- ✅ La UI funciona en el despliegue real: comparativa, búsqueda con progreso, perfil y listas.
- ✅ El token JWS sigue sin salir del servidor.
- ⚠️ Cada ruta nueva que proxya Next.js debe añadirse al Caddyfile; si se olvida, Caddy la manda a FastAPI y devuelve 404. Conviene recordarlo en el `README`.
- ⚠️ El límite de peticiones de Caddy tiene que cubrir las dos rutas (`/api/v1/busquedas*` y `/api/busquedas*`).

**Alternativas consideradas**:
- **Que el navegador llame a la API con la cookie de sesión**: FastAPI no valida esa cookie, obligaría a duplicar la validación de sesión en la API y expondría el dominio de la API al cliente.
- **Mover los proxies a FastAPI**: FastAPI no conoce la cookie de Auth.js; obligaría a reimplementar la sesión en la API.
- **Publicar la API en otra ruta (`/api-public/*`)**: cambia la convención de URLs documentada y rompe los enlaces existentes.

---

## ADR-020: El límite de peticiones separa creación de polling y usa la IP real

**Fecha**: 2026-10-20
**Estado**: aceptado
**Contexto**: Al usar la app en producción, la consulta del estado de un job (`GET /v1/busquedas/{id}`) devolvía 429 de forma intercalada con respuestas correctas, y la barra de progreso se quedaba congelada. Dos causas, ambas en el rate limit de Caddy (ADR-015):

1. La zona `busquedas` usaba el patrón `path /api/busquedas*`, que captura **tanto** la creación (POST) como la consulta del estado (GET). La web consulta el estado cada 1,5 s (ADR-014), así que el polling consumía el cupo de 10/min meant para el endpoint caro: bastaban 15 s de espera para agotarlo, y a partir de ahí las peticiones alternaban entre 429 y respuestas correctas según la ventana deslizante.
2. La clave de la zona era `{remote_host}`, que en este despliegue es la IP del proxy (`192.168.16.1`): **todos los usuarios compartían el mismo cupo**, y el que lo agotara bloqueaba a los demás.

**Decisión**:
- Dos zonas en el `Caddyfile`: `busquedas` (método `POST`, ruta exacta) con 10/min, y `polling` (método `GET`, ruta con id) con 120/min. La web no debe agotar nunca el cupo del endpoint caro.
- La clave pasa a ser la IP real del cliente: `CF-Connecting-IP` cuando llega (Cloudflare la sobrescribe con la del cliente real) y `{remote_host}` como respaldo cuando no hay cabecera (dev, o acceso directo).
- La web deja de martillear ante un 429: respeta el `Retry-After` y reintenta con esa espera, en vez de insistir cada 1,5 s.

**Consecuencias**:
- ✅ El polling (40 peticiones/min con el intervalo de 1,5 s) entra de sobra en su cupo de 120/min y la barra de progreso avanza.
- ✅ El endpoint caro sigue protegido: 10 creaciones/min por IP.
- ✅ Cada usuario tiene su propio cupo: el de uno no bloquea al de otro.
- ⚠️ El límite de polling se fija en el borde; si hubiera que ajustarlo, `RATE_LIMIT_POLLING_POR_MINUTO` en el `.env`.
- ⚠️ `CF-Connecting-IP` solo es fiable si Caddy no es accesible sin pasar por Cloudflare. Aquí el puerto 8088 solo se publica en la red interna, así que lo es.

**Alternativas consideradas**:
- **Subir el límite único a 60/min**: habría que subirlo más cada vez que se acortase el intervalo de polling, y seguiría sin separar el tráfico barato del caro.
- **Bajar el intervalo de polling a 4 s**: alarga la espera hasta que el usuario ve los resultados; no arregla que dos usuarios compartan cupo.
- **Quitar el límite del borde y dejarlo solo en la aplicación**: el límite por IP del borde es lo que frena el ruido antes de que llegue a la API (ADR-015).

---

## ADR-021: La caché de búsquedas se escribe con el resultado del job y el nombre del producto se normaliza

**Fecha**: 2026-10-20
**Estado**: aceptado
**Contexto**: Al repetir la misma búsqueda en producción, la web volvía a lanzar el job al LLM en vez de responder con la caché (ADR-005). Tres defectos encadenados, ninguno cubierto por los tests:

1. **La caché nunca se escribía.** En el worker, `_resultado_json` es `async` pero se invocaba sin `await` dentro de la comprehension, así que la lista contenía coroutines y `json.dumps` fallaba con `TypeError`. El error se silenciaba en el `except` de `RedisCache.set` (un `WARNING` que, además, el worker no mostraba porque nunca configuraba el logging). Resultado: ni una clave de búsqueda en Redis, siempre `cache_hit: false`.
2. **El índice de invalidación caducaba antes que sus claves.** `RedisCache.set` renewaba el TTL del índice con el de cada valor: guardar la comparativa (5 min) acortaba el índice de la búsqueda (24 h), y al expirar el índice sus claves quedaban huérfanas, fuera del alcance de `invalidar_prefijo`.
3. **El nombre del producto no se normalizaba por completo.** "1 L" y "1L" son el mismo artículo, pero `normalizar_nombre` los trataba como distintos, así que la ingesta creaba dos productos y el precio se quedaba en uno. Además, la comparativa buscaba con `icontains` literal, de modo que "leche entera Pascual 1L" no encontraba "Leche entera Pascual 1 L".

**Decisión**:
- El worker cachea el resultado del job con la `cache_key` que se calculó al crear la búsqueda, serializando cada resultado con `await`.
- El índice de invalidación solo renueva su TTL cuando el nuevo TTL es mayor: así vive al menos lo que la clave más longeva.
- `normalizar_nombre` quita el espacio entre la cantidad y la unidad ("1 L" = "1L") y unifica el multiplicador ("4x125 g" = "4 x 125 g"), para que la ingesta reutilice el producto existente.
- La comparativa acepta además del `icontains` literal la similitud de trigramas (umbral 0,5 y mínimo 6 caracteres), apoyándose en el índice GIN que ya existe sobre `productos.nombre`.
- `api/scripts/reparar_duplicados.py` fusiona los duplicados que ya había en la base de datos. **No toca la tabla `precios`**: hay un trigger `trg_precios_append_only` que la hace inmutable; lo que se mueve es la ficha (`productos_cadena`).
- El worker y el scheduler configuran el logging (`api/src/logging_config.py`), que hasta ahora solo hacía uvicorn para la API.

**Consecuencias**:
- ✅ Repetir una búsqueda responde `cache_hit: true` y no consume LLM (verificado en producción).
- ✅ La invalidación por prefijo vuelve a encontrar todas las claves.
- ✅ "1L" y "1 L" encuentran el mismo producto y la comparativa no lo duplica.
- ⚠️ La similitud de trigramas puede devolver productos parecidos al que se busca; con el umbral de 0,5 y el mínimo de 6 caracteres, los falsos positivos medidos ("leche entera" vs "Leche desnatada", 0,26) quedan fuera.
- ⚠️ El script de reparación es manual: en un despliegue nuevo no hay duplicados que reparar.

**Alternativas consideradas**:
- **Bajar el TTL de la caché de búsquedas**: no arreglaba que la caché no se escribiera.
- **No cachear y confiar en el límite por usuario**: el límite protege el presupuesto de LLM, pero cada repetición repetía el coste.
- **Borrar los precios duplicados para fusionar productos**: la tabla `precios` es append-only por diseño (ADR-005 y el trigger de la base de datos); se mueve la ficha, que es la que agrupa los precios.

---

## ADR-022: La búsqueda de productos va por términos con índice de texto completo

**Fecha**: 2026-10-21
**Estado**: aceptado
**Contexto**: Buscar "aceite oliva" no encontraba "Aceite de oliva virgen extra" (ni ningún otro aceite de oliva), aunque el producto estaba en la base de datos con su precio. La búsqueda usaba dos mecanismos, y los dos fallaban:

- `icontains` exige que la consulta aparezca como **subcadena continua**, así que en "Aceite **de** oliva virgen extra" no está: hay palabras de por medio.
- La similitud de trigramas daba 0,448, por debajo del umbral de 0,5 (medido sobre los nombres reales de la base de datos).

**Decisión**: La búsqueda pasa a ser **por términos**: se usa `plainto_tsquery` sobre una columna generada con el `tsvector` del nombre normalizado, con índice GIN. "aceite oliva" se convierte en `'aceit' & 'oliv'` y encuentra el producto aunque el nombre tenga palabras intermedias. Además:

- La normalización del nombre vive en la **base de datos** (función `nombre_buscable_normalizado`, migración 0004) y no solo en la expresión de la columna, para que la consulta aplique exactamente la misma regla que el nombre almacenado. Un test verifica que coincide con `normalizar_nombre` del dominio.
- Se mantiene la similitud de trigramas como alternativa, para las consultas con erratas ("tomte triturado"), donde los términos no coinciden.

**Consecuencias**:
- ✅ "aceite oliva" encuentra los 5 productos de aceite de oliva; "leche entera" no trae "Leche de avena" ni "Agua mineral".
- ✅ El stemming del diccionario `spanish` hace que "tomates" encuentre "Tomate" y "lactea" encuentre "Láctea".
- ✅ Con índice GIN, la búsqueda no se degrada al crecer el catálogo.
- ⚠️ La columna `nombre_buscable` es generada: si cambia la regla de normalización, hace falta una migración que la recalcule.
- ⚠️ La búsqueda por términos es más permisiva que la subcadena: "aceite oliva" trae también "Atún claro en aceite de oliva", que es correcto (contiene ambos términos).

**Alternativas consideradas**:
- **Bajar el umbral de similitud a 0,4**: "aceite oliva" con "Aceite de girasol" da 0,292, pero otros pares no relacionados se closerían; y no arreglaba el caso de las palabras intermedias.
- **Tokenizar la consulta en Python y hacer un `LIKE` por término**: obliga a N condicionales `ILIKE` sobre la tabla y no aprovecha ningún índice.
- **PostgreSQL full-text con `to_tsvector` sobre el nombre sin normalizar**: "1L" y "1 L" seguirían siendo tokens distintos.

---

## ADR-023: El LLM de la ingesta es gratuito, pero la búsqueda web se cobra

**Fecha**: 2026-10-21
**Estado**: aceptado
**Contexto**: Con `openai/gpt-4o-mini:online`, 20 búsquedas consumieron los 20 $ de saldo de OpenRouter. Dos causas se solapaban:

1. El modelo **de pago** (0,15 $/1M de entrada) se pagaba por cada llamada, y la búsqueda web sumaba 0,007 $ por petición.
2. La app llama al LLM **hasta 27 veces por búsqueda** (3 cadenas × 3 pasadas × 3 reintentos), cada llamada con su búsqueda web.

**Decisión**:
- El LLM pasa a ser **gratuito**: `nvidia/nemotron-3.5-super-vl:free:online`. Es el único gratuito que devuelve un **objeto JSON** con el esquema que exige el productor (los `gemma-4-*` devuelven un array y el parser los rechaza), y con contexto de 1 M.
- Se fija el motor de búsqueda a `parallel` (0,005 $ por petición) en vez del Exa `auto` por defecto (0,007 $), con la nueva variable `LLM_MOTOR_BUSQUEDA`.
- `LLM_MAX_PASADAS` (2) y `LLM_MAX_INTENTOS` (2) acotan las llamadas por búsqueda: 3 cadenas × 2 × 2 = 12 en el peor caso, frente a 27.

**Consecuencias**:
- ✅ El LLM no cuesta nada: el gasto es solo la búsqueda web.
- ✅ Con los topes, una búsqueda de 3 cadenas cuesta como máximo 0,06 $ (12 llamadas × 0,005 $) en vez de ~1 $.
- ⚠️ **No hay búsqueda web totalmente gratuita**: la documentación de OpenRouter lo dice ("using web search will incur extra costs, even with free models") y se comprobó que con saldo 0 el modelo gratis funciona pero cualquier motor de búsqueda devuelve 402. Hace falta un saldo mínimo en la cuenta para que la ingesta funcione.
- ⚠️ Los topes bajan la tasa de aciertos: con menos pasadas se aceptan menos productos dudosos. Es el equilibrio chosen entre coste y cobertura.

**Alternativas consideradas**:
- **`perplexity/sonar`**: la búsqueda nativa va incluida en el precio de los tokens (1 $/1M), pero el modelo es de pago y su precio por token es mucho mayor.
- **`openrouter/auto` con plugins**: encarece el LLM además de la búsqueda.
- **Sustituir la búsqueda web por la API del retailer**: no hay API pública; el verificador necesita la URL de la ficha, que es justo lo que aporta el LLM.
- **Dejar el LLM de pago con topes más agresivos**: sigue habiendo coste por token y por búsqueda, y el saldo se vuelve a agotar.

---

## ADR-024: La ficha del retailer es la fuente de verdad del precio y del nombre

**Fecha**: 2026-10-21
**Estado**: aceptado
**Contexto**: Con el LLM gratuito, muchas búsquedas se rechazaban con `precio_no_encontrado_en_html` o `agente_no_encontro`, y una búsqueda tardaba más de un minuto. Las causas, medidas sobre las peticiones reales:

1. **El LLM se equivoca en el precio.** Solo ve el *resumen* de la búsqueda, donde conviven los importes de otros artículos. Para "Leche entera Pascual 1 L" proponía 1,39 € cuando la ficha decía 1,29 €.
2. **El LLM se abstiene ante la ambigüedad.** Ante "pizza" o "galletas digestive marianilla" (marca que no aparece en los resultados) respondía `encontrado: false` y el producto se descartaba.
3. **El parser exigía JSON exacto.** Los modelos que razonan antes de responder envuelven el JSON en texto (`razonamiento`, cabecera del proveedor, ```json), y `json.loads` fallaba.
4. **La latencia es del proveedor, no de la app.** La búsqueda web del modelo gratuito tarda 20–35 s por llamada (el mismo modelo sin búsqueda responde en 0,6 s), y falla con 502 uno de cada tres veces.

**Decisión**:
- **El verificador corrige precio y nombre** con los datos estructurados de la ficha (JSON-LD, `offers.price` y `name`): la página del retailer es la fuente de verdad. El puerto `Verificador` devuelve el precio y el nombre confirmados, y el caso de uso los aplica al candidato antes de guardarlo.
- **El parser tolera el ruido**: extrae el primer objeto JSON balanceado de la respuesta, en vez de exigir que la respuesta *sea* un JSON.
- **El prompt pide un producto concreto** y anima a devolver el equivalente más cercano en vez de abstenererse.
- **Las cadenas se procesan en paralelo**: cada una tarda lo que tarda la búsqueda web, así que en serie la espera se multiplicaba.

**Consecuencias**:
- ✅ "Leche entera Pascual 1 L" se verifica a 1,29 € (el de la ficha) en vez de rechazarse por el 1,39 € que propuso el LLM.
- ✅ El verificador registra qué precio buscaba y qué encontró la página, para poder diagnosticar rechazos.
- ✅ La espera de una búsqueda de 3 cadenas pasa de la suma (~75 s) al máximo (~30 s), más los reintentos.
- ⚠️ Con el modelo gratuito, una búsqueda sigue tardando entre 1 y 3 minutos: la búsqueda web del proveedor es lenta y falla a veces (502). Con un modelo de pago la latencia baja, pero el coste por búsqueda sube. Es el compromiso que se acepta con `LLM_MAX_PASADAS` / `LLM_MAX_INTENTOS`.

**Alternativas consideradas**:
- **Exigir que el LLM acierte el precio**: frágil, depende de la calidad del modelo y del snippet de búsqueda.
- **Rascar el precio del HTML**: la página tiene los precios de otros artículos relacionados; el JSON-LD es el dato estructurado del producto.
- **Un modelo de pago**: más rápido y fiable, pero a 0,007 $ por búsqueda de búsqueda web más los tokens, que es lo que agotó el saldo.

---

## ADR-025: El rediseño visual sigue el patrón de 21st.dev sin adoptar su librería de componentes

**Fecha**: 2026-10-22
**Estado**: aceptado
**Contexto**: La interfaz era correcta pero se cohería con un único patrón: cabecera con el nombre de la aplicación, menú lateral en forma de píldoras sin iconos, casillas de verificación para elegir supermercado, filtros sueltos en una fila y resultados en filas planas. El objetivo era acercarla al patrón de paneles de producto que usan Linear, Vercel y Stripe Dashboard: barra lateral estrecha con iconos y sección activa marcada, campo de búsqueda con icono, filtros seleccionables en forma de chip, filtros agrupados en una card y resultados como cards donde el precio manda.

La referencia visual se obtuvo del catálogo de [21st.dev](https://21st.dev) (MCP `21st`): `wensity/sidebar`, `shadcnstore/app-1`, `shadcnstore/product-card-1` y `skovhm/data-table-toolbar`. Los componentes son shadcn con `framer-motion`, `@base-ui/react` y `@tabler/icons-react`.

**Decisión**:
- **Se adopta el lenguaje visual de 21st.dev, no sus dependencias.** La escala de neutros (superficie `#fafafa`, superficie activa `#f4f4f5`, borde `#e4e4e7`, texto `#18181b`) y la jerarquía (etiqueta de sección en mayúsculas atenuadas, elemento activo con fondo gris, precio grande y en negrita) se replican sobre los tokens que ya tenía el proyecto. No se instalan `framer-motion`, `@base-ui/react` ni `@tabler/icons-react`: la animación de indicador activo que aporta el sidebar de referencia es justo lo que el brief excluye, y los iconos se dibujan en línea en `components/ui/Icono.tsx`.
- **El ancho máximo del contenido baja de 60 a 54 rem** para que la columna de resultados siga siendo legible con la barra lateral abierta en un portátil de 1280 px.
- **Los filtros pasan a una card con rejilla** de 1, 2 o 5 columnas según el ancho, con `shadow-sm` (la sombra más discreta de la escala de Tailwind 3.4: `0 1px 2px 0 rgb(0 0 0 / 0.05)`) para separarla del fondo.
- **El linter de a11y admite `shadow-sm`** y sigue rechazando el resto de sombras y cualquier degradado. Antes no admitía ninguna.
- **El linter de hover pasa a analizar el `className` completo** en vez de línea a línea: al repartir las clases en varias líneas, las plantillas multilínea se escapaban de la comprobación.

**Consecuencias**:
- ✅ La interfaz sigue el patrón de los paneles de producto actuales sin añadir una sola dependencia.
- ✅ Todos los pares texto/fondo de la paleta nueva superan 4,5:1 y el linter lo comprueba; `borde-fuerte` mantiene 4,8:1 para los campos de formulario (WCAG 1.4.11).
- ✅ La lógica de negocio y las APIs no cambian: el selector de cadenas sigue alternando la misma lista, y los filtros siguen aplicando los mismos parámetros.
- ⚠️ El catálogo de 21st.dev solo permite 2 recuperaciones de código al día en el plan gratuito, y su herramienta `search` devolvió `catalog search failed` durante el rediseño. La referencia se obtuvo de la API REST (`GET /api/v1/components/search`) y de las previews de CDN, que no consumen cuota. El código completo de un componente no se pudo instalar hasta el 23 de octubre.

**Alternativas consideradas**:
- **Instalar los componentes de 21st.dev tal cual** (`npx shadcn@latest add "https://21st.dev/r/<autor>/<slug>"`): arrastra `framer-motion`, `@base-ui/react` y `@tabler/icons-react`, y con ello animaciones que el brief excluye. Además exige el árbol de primitivas de shadcn, que el proyecto no tiene.
- **Reemplazar la paleta por la del design system de 21st.dev** (negro `#171717` y dorado `#D4AF37`): era la propuesta del generador de design systems, pero rompe la identidad y el contraste ya verificado del proyecto. Se conserva el azul y solo se adopts la escala de neutros.
- **Mantener los checkboxes**: un chip con `aria-pressed` comunica el estado seleccionado en el propio control, sin casilla que sumar.

---

## Plantilla para nuevas decisiones

```markdown
## ADR-XXX: Título breve

**Fecha**: YYYY-MM-DD
**Estado**: propuesto | aceptado | rechazado | obsoleto
**Contexto**: Qué problema o duda motivó la decisión.
**Decisión**: Qué se decidió.
**Consecuencias**: Qué implica (positivas y negativas).
**Alternativas consideradas**: Qué se descartó y por qué.
```

**Reglas**:
- Un ADR por decisión. No agrupes decisiones no relacionadas.
- Append-only: no borres ADRs antiguos. Si una decisión cambia, crea uno nuevo que marque el anterior como `obsoleto` y lo referencie.
- Referencia el ADR en el commit o PR que lo implementa (`Implements ADR-004`).

