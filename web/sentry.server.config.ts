import * as Sentry from "@sentry/nextjs";

/**
 * Sentry en el servidor de Next.js: captura los errores de las Server
 * Components, Route Handlers y de la API interna.
 */
Sentry.init({
  dsn: process.env.SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_APP_ENV,
  tracesSampleRate: 0.1,
});
