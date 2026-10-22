import type { Config } from "tailwindcss";

/**
 * Tokens del estilo minimalista: mucho espacio, un solo color de acento y
 * bordes suaves en lugar de sombras marcadas.
 *
 * Los tonos neutros siguen la escala de zinc (referencia visual de 21st.dev
 * / shadcn): superficies casi blancas para el reposo, gris muy claro para
 * el elemento activo de la navegación y un texto casi negro. Todos los
 * pares texto/fondo superan 4,5:1; el linter de a11y lo comprueba.
 */
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        borde: "#e4e4e7",
        // Borde de los campos de formulario: 4,8:1 sobre blanco (WCAG 1.4.11).
        "borde-fuerte": "#71717a",
        texto: "#18181b",
        gris: "#6b6b73",
        primario: "#2563eb",
        "primario-oscuro": "#1d4ed8",
        "primario-suave": "#eff6ff",
        error: "#dc2626",
        "error-suave": "#fef2f2",
        // Superficie en reposo (campos, chips) y superficie del elemento
        // activo de la navegación.
        superficie: "#fafafa",
        "superficie-activa": "#f4f4f5",
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
        // Con la barra lateral abierta, 54 rem caben en un portátil de
        // 1280 px sin que la columna de resultados se vuelva ilegible.
        contenido: "54rem",
        lectura: "42rem",
      },
    },
  },
  plugins: [],
};

export default config;
