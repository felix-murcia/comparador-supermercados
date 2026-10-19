import type { Config } from "tailwindcss";

/**
 * Tokens del estilo minimalista tipo Google: mucho espacio, un solo color
 * de acento y bordes suaves en lugar de sombras.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        borde: "#dadce0",
        texto: "#202124",
        gris: "#5f6368",
        primario: "#1a73e8",
        "primario-oscuro": "#1558d6",
        "primario-suave": "#e8f0fe",
        error: "#d93025",
        "error-suave": "#fce8e6",
      },
      fontFamily: {
        sans: [
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Arial",
          "sans-serif",
        ],
      },
      borderRadius: {
        tarjeta: "12px",
        pill: "24px",
      },
      maxWidth: {
        contenido: "60rem",
        lectura: "42rem",
      },
    },
  },
  plugins: [],
};

export default config;
