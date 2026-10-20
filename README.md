# Comparador de Precios de Supermercados Españoles

Aplicación web para comparar precios de productos de supermercados en España (DIA, Carrefour, Mercadona), gestionar listas de la compra y calcular el ahorro real de comprar la misma cesta en distintas cadenas o de forma mixta.

**Estado**: 🟡 En desarrollo (Épica 0 parcial — 6/8; Épica 1 — Autenticación completada; Épica 2 — Modelo de datos completada)
**Versión**: 0.1.0-dev
**Licencia**: Por definir

---

## ¿Qué hace?

- **Compara precios verificados** de productos entre supermercados (no estimados: cada precio tiene URL fuente y fecha).
- **Calcula el ahorro real** de una cesta completa:
  - % A: vs. la cadena más cara.
  - % C: vs. la cesta óptima (mezclando lo más barato de cada cadena).
- **Gestiona listas de la compra** con coste total y ahorro.
- **Histórico de precios** por producto.
- **Interfaz minimalista** tipo Google: buscar → comparar → decidir.

**Público objetivo**: consumidores españoles que quieren optimizar el gasto de la compra.

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | Next.js 14 (App Router) + React + TypeScript |
| BD | PostgreSQL 16 (primario + réplica) |
| Caché/Cola | Redis 7 |
| Reverse proxy | Caddy 2 |
| Contenedores | Docker + docker-compose |
| Auth | Auth.js (OAuth Google + Microsoft) |
| CI/CD | GitHub Actions |
| Observabilidad | Sentry + UptimeRobot |

Detalle completo en [`docs/decisions.md`](docs/decisions.md) (ADR-001).

---

## Documentación

Antes de tocar código, lee en este orden:

| Documento | Qué contiene |
|-----------|--------------|
| [`AGENTS.md`](AGENTS.md) | Contrato operativo para agentes de IA (reglas, flujo, checklist) |
| [`docs/PLAN.md`](docs/PLAN.md) | Requisitos de negocio y plan de acción (fuente de verdad) |
| [`docs/CONVENTIONS.md`](docs/CONVENTIONS.md) | Convenciones de código, nombres, estructura, testing |
| [`docs/decisions.md`](docs/decisions.md) | ADRs (el "por qué" de cada decisión arquitectónica) |
| [`docs/BACKLOG.md`](docs/BACKLOG.md) | Tareas ejecutables por épicas con dependencias |

**Regla**: si algo no está en estos documentos, no existe. Si necesitas una decisión nueva, propón un ADR antes de implementar.

---

## Requisitos previos

- **Docker** ≥ 24 y **Docker Compose** ≥ 2.24
- **Node.js** ≥ 20 (solo si trabajas en `web/` fuera de Docker)
- **Python** ≥ 3.12 (solo si trabajas en `api/` fuera de Docker)
- **Git** ≥ 2.40
- **Make** (opcional, para atajos)

Verifica:

```bash
docker --version
docker compose version
node --version
python --version
```

---

## Arranque rápido (dev)

### 1. Clonar el repo

```bash
git clone <url-del-repo> comparador-precios
cd comparador-precios
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y rellena **como mínimo**:

```env
APP_SECRET_KEY=<genera con: openssl rand -hex 32>
POSTGRES_PASSWORD=<elige una contraseña>
POSTGRES_REPLICATION_PASSWORD=<elige otra contraseña para replicación>
GOOGLE_CLIENT_ID=<de Google Cloud Console>
GOOGLE_CLIENT_SECRET=<de Google Cloud Console>
MICROSOFT_CLIENT_ID=<de Azure Portal>
MICROSOFT_CLIENT_SECRET=<de Azure Portal>
LLM_API_KEY=<de tu proveedor>
```

> ⚠️ **Nunca commitees `.env`**. Está en `.gitignore`. Si detectas un secreto en el repo, avisa: es una penalización grave según `AGENTS.md` §3.1.

> Los comandos de Compose usan `--env-file .env` para que los puertos e `IMAGE_TAG` de `.env` se apliquen a la interpolación. Los secretos se inyectan en los contenedores mediante `env_file`.

### 3. Levantar el entorno

```bash
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml up -d --build
```

Espera a que todos los servicios estén `healthy`:

```bash
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml ps
```

### 4. Aplicar migraciones y seed

```bash
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec api alembic upgrade head
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec api python -m scripts.seed
```

### 5. Abrir la app

- **Web (vía Caddy)**: http://localhost
- **API (vía Caddy)**: http://localhost/api/health/ready
- **Web directo**: http://localhost:3000
- **API directa**: http://localhost:8000
- **Docs API (dev)**: http://localhost:8000/docs

---

## Autenticación (OAuth en dev)

La web usa Auth.js (NextAuth) con Google y Microsoft Entra ID. La sesión se firma como JWT HS256 con `NEXTAUTH_SECRET` (ADR-012) y la API valida ese mismo token.

1. **Google Cloud Console** → *APIs y servicios* → *Credenciales* → *ID de cliente de OAuth* (tipo "Aplicación web"):
   - Orígenes autorizados: `http://localhost:3000`
   - URI de redirección: `http://localhost:3000/api/auth/callback/google`
2. **Azure Portal** → *Microsoft Entra ID* → *Registros de aplicaciones* → *URI de redirección* (plataforma Web):
   - `http://localhost:3000/api/auth/callback/microsoft`
   - `MICROSOFT_TENANT_ID=common` permite cuentas de cualquier tenant.
3. Rellena en `.env`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET` y `NEXTAUTH_SECRET` (`openssl rand -hex 32`).
4. Reinicia la web (`docker compose ... up -d --build web`) y entra en http://localhost:3000/api/auth/signin.

Sin credenciales OAuth la web arranca igual, pero el flujo de login no se completa.

---

## Métricas de ingesta

Cada precio que ingiere el worker se registra en la tabla `ingesta_metricas` con su estado (`verificado`, `sospechoso`, `rechazado`), la cadena y el motivo. El resumen se consulta en el endpoint interno (requiere sesión iniciada):

```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/v1/_metrics/ingesta
```

```json
{
  "total": 120,
  "verificado": 96,
  "sospechoso": 18,
  "rechazado": 6,
  "porcentaje_verificado": 80.0,
  "porcentaje_sospechoso": 15.0,
  "porcentaje_rechazado": 5.0,
  "motivos": [{ "motivo": "desviacion_precio", "total": 12 }]
}
```

También se puede consultar en SQL:

```sql
SELECT estado, count(*) FROM ingesta_metricas GROUP BY estado;
SELECT motivo, count(*) FROM ingesta_metricas
  WHERE motivo IS NOT NULL GROUP BY motivo ORDER BY 2 DESC;
```

---

## Comandos frecuentes

### Levantar / parar

```bash
# Levantar
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml up -d

# Parar sin borrar volúmenes
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml down

# Parar y borrar todo (⚠️ borra BD)
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml down -v
```

### Logs

```bash
# Todos
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml logs -f

# Solo API
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml logs -f api

# Solo worker
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml logs -f worker
```

### Base de datos

```bash
# Migraciones
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec api alembic upgrade head

# Crear migración
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec api alembic revision --autogenerate -m "descripcion"

# Revertir una migración
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec api alembic downgrade -1

# Acceder a psql (primario)
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec postgres-primary psql -U app -d precios
```

### Tests y linters

```bash
# Backend: tests
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec api pytest

# Backend: lint + tipos
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec api ruff check .
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec api mypy src

# Frontend: tests
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec web npm test

# Frontend: lint + tipos
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec web npm run lint
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec web npx tsc --noEmit

# Frontend: guardas de i18n y accesibilidad (sin navegador)
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec web npm run lint:i18n
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec web npm run lint:a11y

# Seguridad
pre-commit run gitleaks --all-files
```

### Worker y scheduler

```bash
# Ver estado del worker
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml logs -f worker

# Lanzar ingesta manualmente (dev)
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec worker python -m src.scheduler --run-now
```

---

## Estructura del repositorio

```
/
├── AGENTS.md                  ← contrato operativo para agentes
├── README.md                  ← este archivo
├── docs/
│   ├── PLAN.md                ← plan de acción y requisitos
│   ├── CONVENTIONS.md         ← convenciones de código
│   ├── decisions.md           ← ADRs
│   └── BACKLOG.md             ← tareas ejecutables
├── api/                       ← backend FastAPI
│   ├── src/
│   │   ├── dominio/           ← entidades + reglas (sin frameworks)
│   │   ├── aplicacion/        ← casos de uso
│   │   ├── puertos/           ← interfaces
│   │   ├── adaptadores/       ← implementaciones (SQLAlchemy, LLM, Redis)
│   │   ├── api_http/          ← capa FastAPI
│   │   ├── config.py
│   │   └── main.py
│   ├── tests/
│   ├── alembic/
│   ├── scripts/
│   ├── Dockerfile
│   └── pyproject.toml
├── web/                       ← frontend Next.js 14
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── locales/
│   ├── public/logos/
│   ├── Dockerfile
│   └── package.json
├── infra/
│   ├── docker-compose.base.yml
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   ├── caddy/
│   │   ├── Caddyfile
│   │   └── Dockerfile
│   ├── postgres/init-primary.sh
│   ├── postgres/init-replica.sh
│   └── k8s/                   ← plantillas (no desplegar aún)
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
└── .github/workflows/ci.yml
```

---

## Entornos

| Entorno | Compose | Uso |
|---------|---------|-----|
| **dev** | `base.yml` + `dev.yml` | Desarrollo local, hot-reload, datos seed |
| **prod** | `base.yml` + `prod.yml` | VPS, TLS, logs JSON, Sentry |

### Deploy en prod (VPS)

**Requisitos**: VPS con Docker, dominio apuntando al VPS, puertos 80/443 abiertos.

```bash
# En el VPS
git clone <url-del-repo> /opt/comparador
cd /opt/comparador
cp .env.example .env
# Editar .env con valores de producción:
# APP_ENV=prod, DOMAIN=precios.example.com, secretos reales

docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.prod.yml up -d --build
docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.prod.yml exec api alembic upgrade head
```

**Backups**: configurar cron diario con `pg_dump` del primario. Ver `docs/PLAN.md` §RNF-06.

**No commitear** el `.env` de prod. En el VPS, permisos `600`:

```bash
chmod 600 .env
```

---

## Flujo de trabajo (desarrollo)

1. **Lee** `AGENTS.md` y el issue correspondiente en `docs/BACKLOG.md`.
2. **Crea rama**: `feat/epica-X-descripcion` o `fix/descripcion`.
3. **Implementa** con tests.
4. **Verifica** localmente:
   ```bash
   docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec api pytest
   docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec api ruff check .
   docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec api mypy src
   docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec web npm test
   docker compose --env-file .env -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml exec web npm run lint
   ```
5. **Commit** con Conventional Commits:
   ```bash
   git commit -m "feat(api): añadir endpoint POST /v1/busquedas"
   ```
6. **Abre PR** con descripción: qué, por qué, cómo probar.
7. **CI verde** obligatorio antes de merge.
8. **Actualiza** `docs/BACKLOG.md` marcando la tarea `[x]`.
9. Si tomaste una decisión nueva → **ADR** en `docs/decisions.md`.

Detalle completo en `AGENTS.md` §4.

---

## Seguridad

- **Cero secretos en código**. Si encuentras uno, avisa: es penalización grave.
- **`.env` nunca se commitea**. `.env.example` es la fuente de verdad de variables.
- **Pre-commit hook** con `gitleaks` bloquea commits con secretos.
- **Logs** redactan `authorization`, `api_key`, `password`, `token`, `cookie`.
- **Rotación de secretos** documentada por proveedor (Google, Microsoft, LLM, Postgres).

Si detectas una vulnerabilidad, **no abras un issue público**. Contacta al maintainer directamente.

---

## Estado del proyecto

| Épica | Estado | Progreso |
|-------|--------|----------|
| 0 — Fundación | 🟡 En curso | 6/8 |
| 1 — Autenticación | ✅ Completada | 5/5 |
| 2 — Modelo de datos | ✅ Completada | 6/6 |
| 3 — Ingesta | ✅ Completada | 8/8 |
| 4 — API búsqueda/comparativa | ✅ Completada | 6/6 |
| 5 — Frontend flujo principal | ✅ Completada | 8/8 |
| 6 — Perfil y listas | 🟡 En curso | 4/6 |
| 7 — Calidad y operación | ⚪ Pendiente | 0/6 |
| 8 — Escala (post-MVP) | ⚪ Futuro | — |

Detalle en [`docs/BACKLOG.md`](docs/BACKLOG.md).

---

## Roadmap (post-MVP)

- Más cadenas de supermercados (Alcampo, Eroski, Lidl, Aldi).
- i18n completo (inglés, otros países).
- App móvil (React Native o PWA).
- API pública para terceros.
- Alertas de bajada de precio.
- Comparativa de cestas predefinidas (despensa básica, vegana, sin gluten).

Priorización en `docs/PLAN.md` §8 (Épica 8).

---

## Contribuir

Proyecto personal en fase MVP. Si quieres contribuir:

1. Lee `AGENTS.md` y `docs/CONVENTIONS.md`.
2. Abre un issue describiendo el cambio antes de implementar.
3. Sigue el flujo de trabajo de la sección anterior.
4. Un PR = un issue. No mezcles refactor con feature.

---

## Contacto

- **Maintainer**: [por definir]
- **Issues**: [url del repo]/issues
- **Discusiones**: [url del repo]/discussions

---

## Licencia

Por definir. Hasta entonces, todos los derechos reservados.