const { withSentryConfig } = require("@sentry/nextjs");

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Las imágenes son SVG locales (logos de las cadenas). El optimizador de
  // imágenes no sirve para SVG y abre una vía de ataque innecesaria
  // (CVE-2026-44578 / GHSA-2xp9-vwfh-vxw4), así que se desactiva.
  images: {
    unoptimized: true,
  },
};

module.exports = withSentryConfig(nextConfig, {
  // Sin token de autenticación no se suben los source maps: el build no falla.
  silent: true,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
});
