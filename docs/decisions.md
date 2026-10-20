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
- ✅ La barra de progreso solo aparece en cache miss (requisito de UX).
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
**Contexto**: Al lanzar una búsqueda, la web necesita saber cuándo termina el job (T5.3) para pasar de la barra de progreso a los resultados.

**Decisión**: La web **hace polling** a `GET /v1/busquedas/{id}` cada 1,5 s desde el navegador (vía el proxy de Next). El estado del job vive en la tabla `busquedas` y lo escribe el worker; no hay canales push.

**Consecuencias**:
- ✅ Sin WebSockets ni SSE: el estado ya está en la base de datos y el worker es un proceso aparte.
- ✅ Funciona igual detrás de proxies y balanceadores (no hay conexiones largas).
- ⚠️ Hasta 1,5 s de retraso entre el fin real del job y el cambio de vista. Se asume: el trabajo de ingesta tarda segundos o minutos.
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

