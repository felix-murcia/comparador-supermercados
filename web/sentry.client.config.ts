import * as Sentry from "@sentry/nextjs";

/**
 * Sentry en el navegador: captura los errores de cliente (JS, promesas
 * rechazadas y errores de renderizado).
 */
Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_APP_ENV,
  tracesSampleRate: 0.1,
});
