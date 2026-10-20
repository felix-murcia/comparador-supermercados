const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
};

module.exports = withSentryConfig(nextConfig, {
  // Sin token de autenticación no se suben los source maps: el build no falla.
  silent: true,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
});
