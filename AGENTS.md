# AGENTS.md

**Propósito**: Este archivo es el contrato operativo para cualquier agente de IA (OpenCode) que trabaje en este repositorio. Define dónde está la información, cómo navegarla, qué reglas son inviolables y cómo proceder ante ambigüedad.

**Última actualización**: 2026-10-19

---

## 1. Lectura obligatoria al inicio de cada sesión

Antes de escribir una sola línea de código, el agente debe leer, en este orden:

0. `@docs/CLAUDE.md` — Reglas de uso oblgatorio no negociables.
1. `@docs/PLAN.md` — Plan de acción y requisitos de negocio (contexto maestro).
2. `@docs/decisions.md` — Registro de decisiones arquitectónicas (ADRs).
3. `@docs/CONVENTIONS.md` — Convenciones de código, nombres y estructura.
4. `@README.md` — Cómo arrancar el proyecto en local.

Si alguno de estos archivos no existe, **detente y pregunta** antes de continuar. No improvises su contenido.

---

## 2. Mapa del repositorio

```
/
├── AGENTS.md                  ← este archivo
├── README.md                  ← arranque rápido
├── docs/
│   ├── PLAN.md                ← plan de acción y requisitos (FUENTE DE VERDAD)
│   ├── decisions.md           ← ADRs (append-only)
│   └── CONVENTIONS.md         ← convenciones de código
├── api/                       ← backend FastAPI
│   ├── src/
│   │   ├── dominio/           ← entidades + reglas (sin frameworks)
│   │   ├── aplicacion/        ← casos de uso
│   │   ├── puertos/           ← interfaces
│   │   ├── adaptadores/       ← implementaciones concretas
│   │   ├── api_http/          ← capa FastAPI (traduce, no decide)
│   │   ├── config.py          ← pydantic-settings
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── web/                       ← frontend Next.js 14
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── locales/
│   ├── Dockerfile
│   └── package.json
├── infra/
│   ├── docker-compose.base.yml
│   ├── docker-compose.dev.yml
│   ├── docker-compose.prod.yml
│   ├── caddy/
│   ├── postgres/
│   └── k8s/                   ← plantillas, NO desplegar aún
├── .env.example
├── .gitignore
└── .pre-commit-config.yaml
```

**Regla de navegación**: un tema = un archivo. Si necesitas información sobre un módulo, busca en su carpeta antes de asumir. Si no la encuentras, pregunta.

---

## 3. Reglas inviolables

Estas reglas **no se negocian**. Si una tarea requiere violarlas, detente y explica por qué antes de actuar.

### 3.1 Seguridad
- **PROHIBIDO** hardcodear secretos: API keys, passwords, tokens, client secrets, nombres propios de personas reales, DSNs con credenciales.
- Todo secreto va en `.env` (nunca commiteado) y se referencia por variable de entorno.
- `.env.example` debe existir con claves vacías y comentarios.
- Si detectas un secreto en código, **no lo commitees**: avisa y propón moverlo a `.env`.
- No loguees `authorization`, `api_key`, `password`, `token`, `cookie`.
- No añadas dependencias que requieran telemetría obligatoria sin preguntar.

### 3.2 Arquitectura
- Respetar la separación de capas: `dominio` → `aplicacion` → `puertos` → `adaptadores` → `api_http`.
- `dominio` no importa frameworks (ni FastAPI, ni SQLAlchemy, ni Pydantic).
- `api_http` no contiene lógica de negocio: solo traduce HTTP ↔ casos de uso.
- `adaptadores` implementan `puertos`; nunca al revés.
- La API es **stateless**: nada de estado en memoria del proceso que deba sobrevivir a un reinicio.
- Procesos separados: `api`, `worker`, `scheduler`. No mezclar responsabilidades.

### 3.3 Código
- **SOLID** estricto. Si una clase tiene más de una razón para cambiar, divídela.
- **Complejidad ciclomática baja**: early returns, diccionarios de dispatch, funciones cortas (<30 líneas idealmente).
- Sin `if` anidados de más de 3 niveles. Si aparecen, extrae función o usa un patrón.
- Tipado obligatorio en Python (`mypy` en CI) y TypeScript (`strict: true`).
- Sin `print` en código de producción: usa el logger configurado.
- Sin `TODO` sin issue asociado. Si añades uno, referencia el issue: `# TODO(#123): ...`.

### 3.4 Datos
- Lecturas de API pública → `engine_ro` (réplica).
- Escrituras, migraciones, ingesta → `engine_rw` (primario).
- Migraciones con Alembic, ejecutadas como job separado, **nunca** en el arranque de la API.
- `precios` es append-only. No se actualiza, se inserta nueva fila.

### 3.5 Despliegue
- Todo debe funcionar en `docker-compose.dev.yml` en local.
- Todo debe ser portable a Kubernetes/OpenShift: stateless, env vars, healthchecks, sin cron interno.
- No añadir servicios de infraestructura nuevos (Kafka, Elasticsearch, etc.) sin aprobación explícita.

---

## 4. Flujo de trabajo del agente

### 4.1 Antes de implementar
1. Localiza la épica y el issue correspondiente en `@docs/PLAN.md` (sección 8).
2. Verifica si hay un ADR relacionado en `@docs/decisions.md`.
3. Si el issue es ambiguo, **pregunta antes de escribir código**. No asumas.
4. Si el issue requiere una decisión arquitectónica nueva, propón un ADR primero.

### 4.2 Durante la implementación
1. Crea una rama con nombre descriptivo: `feat/epica-X-descripcion` o `fix/descripcion`.
2. Commits atómicos con mensajes en formato Conventional Commits:
   - `feat(api): añadir endpoint POST /busquedas`
   - `fix(worker): corregir reintento en verificador`
   - `docs(plan): actualizar criterios de aceptación`
3. Tests junto al código, no después.
4. Si tocas el esquema de BD, incluye migración Alembic en el mismo PR.
5. Si añades una dependencia, justifícala en el PR.

### 4.3 Antes de cerrar
1. Ejecuta tests: `pytest` (api) y `npm test` (web).
2. Ejecuta linters: `ruff`, `mypy` (api), `eslint`, `tsc` (web).
3. Verifica que `gitleaks` pasa.
4. Verifica que `docker compose -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml up` levanta sin errores.
5. Actualiza `@docs/decisions.md` si tomaste una decisión nueva.
6. Marca el issue como completado en `@docs/PLAN.md` si aplica.

---

## 5. Comandos frecuentes

```bash
# Levantar entorno dev
docker compose -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml up -d

# Ver logs de la API
docker compose -f infra/docker-compose.base.yml -f infra/docker-compose.dev.yml logs -f api

# Migraciones
docker compose exec api alembic upgrade head

# Crear migración
docker compose exec api alembic revision --autogenerate -m "descripcion"

# Tests backend
docker compose exec api pytest

# Tests frontend
docker compose exec web npm test

# Linters backend
docker compose exec api ruff check .
docker compose exec api mypy src

# Linters frontend
docker compose exec web npm run lint
docker compose exec web npx tsc --noEmit

# Gitleaks
pre-commit run gitleaks --all-files
```

Si un comando falla, **lee el error completo antes de proponer un fix**. No apliques parches a ciegas.

---

## 6. Convenciones de código

### 6.1 Python (api)
- Formato: `ruff format` (línea 100).
- Imports ordenados por `ruff` (isort integrado).
- Nombres:
  - Clases: `PascalCase`
  - Funciones/variables: `snake_case`
  - Constantes: `UPPER_SNAKE_CASE`
  - Módulos: `snake_case`
- Puertos (interfaces): sufijo `Port` o nombre de dominio (`Productor`, `Verificador`, `RepositorioPrecios`).
- Adaptadores: prefijo por tecnología (`SQLAlchemyRepositorioPrecios`, `LLMProductor`, `RedisCache`).
- Casos de uso: verbo en infinitivo (`BuscarProducto`, `CalcularAhorroLista`).
- DTOs de entrada/salida de API: sufijo `Request` / `Response`.

### 6.2 TypeScript (web)
- Formato: `prettier` + `eslint`.
- Componentes: `PascalCase` en archivos `PascalCase.tsx`.
- Hooks: `useCamelCase`.
- Utilidades: `camelCase.ts`.
- Tipos: `PascalCase`, sin prefijo `I`.
- Sin `any`. Si es inevitable, `unknown` + type guard.

### 6.3 SQL
- Tablas y columnas en `snake_case`.
- Plural para tablas (`productos`, `precios`).
- Claves foráneas: `<tabla_singular>_id`.
- Timestamps: `creado_en`, `actualizado_en`.
- Booleanos: prefijo `es_` o `tiene_` cuando aporte claridad (`disponible` es aceptable).

### 6.4 API HTTP
- Versionado en path: `/v1/...`.
- Recursos en plural: `/productos`, `/listas`, `/busquedas`.
- Verbos HTTP estándar. `POST` para crear, `GET` para leer, `PATCH` para actualizar parcial, `DELETE` para borrar.
- Errores en formato `{ "code": "PRODUCTO_NO_ENCONTRADO", "message": "..." }`. El `code` es estable; el `message` puede cambiar.
- Paginación: `?limit=&offset=` con `Link` header (futuro).

---

## 7. Gestión de la ambigüedad

El agente **no debe inventar requisitos**. Si encuentra:

- **Un issue incompleto**: pregunta qué falta antes de implementar.
- **Un conflicto entre `PLAN.md` y el código actual**: señálalo y propón resolverlo vía ADR.
- **Una decisión de producto no cubierta**: pregunta. Ejemplos típicos:
  - ¿Qué pasa si un producto no existe en una cadena al calcular % A?
  - ¿Cómo se comporta el filtro `solo_con_stock` si `disponible` es `null`?
  - ¿Qué prioridad tiene provincia vs. nacional si ambos existen?
- **Una dependencia nueva**: justifica y pide aprobación.
- **Un cambio de esquema**: propón migración y ADR.

**Regla de oro**: es mejor preguntar una vez que implementar dos veces.

---

## 8. Qué NO hacer

- No crear archivos nuevos en la raíz sin justificación.
- No duplicar información entre `AGENTS.md`, `PLAN.md` y `README.md`. Cada cosa en su sitio.
- No añadir `console.log` ni `print` de depuración al código commiteado.
- No modificar migraciones ya aplicadas. Crea una nueva.
- No tocar `infra/k8s/` para desplegar: son plantillas. El despliegue es post-MVP.
- No instalar Kubernetes, Kafka, Elasticsearch, RabbitMQ ni similares en dev.
- No usar `latest` como tag de imagen en compose de prod.
- No commitear `.env`, `*.pem`, `*.key`, `secrets/`.
- No mezclar refactor con feature en el mismo PR.

---

## 9. Registro de decisiones (ADR ligero)

Cuando tomes una decisión que afecte a la arquitectura, añade una entrada en `@docs/decisions.md` con este formato:

```markdown
## ADR-XXX: Título breve

**Fecha**: YYYY-MM-DD
**Estado**: propuesto | aceptado | rechazado | obsoleto
**Contexto**: Qué problema o duda motivó la decisión.
**Decisión**: Qué se decidió.
**Consecuencias**: Qué implica (positivas y negativas).
**Alternativas consideradas**: Qué se descartó y por qué.
```

Ejemplos de decisiones que requieren ADR:
- Cambiar el proveedor de LLM.
- Añadir una nueva cadena de supermercados.
- Cambiar la fórmula de % de ahorro.
- Introducir un nuevo servicio de infraestructura.
- Cambiar el esquema de caché.

---

## 10. Contacto y escalado

Si el agente encuentra un bloqueo que no puede resolver con la información del repo:

1. Documenta el bloqueo en el PR o issue con contexto suficiente.
2. Propón al menos dos alternativas con pros y contras.
3. Espera respuesta humana antes de continuar.

**No hay prisa que justifique romper las reglas de la sección 3.**

---

## 11. Checklist rápido antes de cada PR

- [ ] He leído `PLAN.md` y el issue correspondiente.
- [ ] No hay secretos en el diff (`gitleaks` pasa).
- [ ] Respeto la separación de capas.
- [ ] Tests pasan (`pytest`, `npm test`).
- [ ] Linters pasan (`ruff`, `mypy`, `eslint`, `tsc`).
- [ ] `docker compose up` levanta sin errores.
- [ ] Si toqué BD, hay migración Alembic.
- [ ] Si tomé una decisión nueva, hay ADR.
- [ ] El commit sigue Conventional Commits.
- [ ] El PR describe qué, por qué y cómo probarlo.

---
