# syntax=docker/dockerfile:1

# ---------- Base común ----------
FROM node:20-alpine AS base

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

WORKDIR /app

# ---------- Dependencias ----------
FROM base AS deps

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# ---------- Desarrollo: hot-reload ----------
FROM base AS dev

ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1

COPY --from=deps --chown=nextjs:nodejs /app/node_modules ./node_modules
COPY --chown=nextjs:nodejs . .
RUN mkdir -p .next && chown nextjs:nodejs .next /app

USER nextjs
EXPOSE 3000

CMD ["npm", "run", "dev"]

# ---------- Build de producción ----------
FROM base AS builder

ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# ---------- Runtime de producción (standalone) ----------
FROM base AS runner

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
