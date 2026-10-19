# syntax=docker/dockerfile:1

# La imagen oficial de Caddy no incluye el plugin de rate limit.
# Se compila una imagen propia con mholt/caddy-ratelimit.
FROM caddy:2.11.7-builder AS builder

RUN xcaddy build v2.11.7 \
    --with github.com/mholt/caddy-ratelimit@v0.1.0

FROM caddy:2.11.7-alpine

COPY --from=builder /usr/bin/caddy /usr/bin/caddy
