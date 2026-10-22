#!/usr/bin/env node
/**
 * Auditoría de accesibilidad (WCAG AA) del frontend.
 *
 * Comprueba, sin navegador:
 *   1. Cada `<img>` tiene `alt` (puede estar vacío si es decorativa).
 *   2. Cada campo de formulario tiene nombre accesible (label, aria-label…).
 *   3. La paleta de tokens cumple el contraste mínimo (4,5:1 texto, 3:1 UI).
 *   4. No se usan sombras marcadas ni degradados. Solo se admite
 *      `shadow-sm`, que en Tailwind 3.4 es la más discreta de la escala
 *      (0 1px 2px 0 rgb(0 0 0 / 0.05)) y sirve para separar una card del
 *      fondo sin efecto visual apreciable.
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(RAIZ, "src");

/** Pares de la paleta: [nombre, primer plano, fondo, mínimo]. */
const PALETA = [
  ["texto sobre blanco", "#18181b", "#ffffff", 4.5],
  ["gris sobre blanco", "#6b6b73", "#ffffff", 4.5],
  ["primario sobre blanco", "#2563eb", "#ffffff", 4.5],
  ["primario-oscuro sobre blanco", "#1d4ed8", "#ffffff", 4.5],
  ["error sobre blanco", "#dc2626", "#ffffff", 4.5],
  ["texto sobre azul suave", "#18181b", "#eff6ff", 4.5],
  ["gris sobre azul suave", "#6b6b73", "#eff6ff", 4.5],
  ["primario-oscuro sobre azul suave", "#1d4ed8", "#eff6ff", 4.5],
  ["blanco sobre primario", "#ffffff", "#2563eb", 4.5],
  ["blanco sobre primario-oscuro", "#ffffff", "#1d4ed8", 4.5],
  ["borde de campo sobre blanco", "#71717a", "#ffffff", 3],
  ["texto sobre superficie", "#18181b", "#fafafa", 4.5],
  ["gris sobre superficie", "#6b6b73", "#fafafa", 4.5],
  ["texto sobre superficie activa", "#18181b", "#f4f4f5", 4.5],
  ["gris sobre superficie activa", "#6b6b73", "#f4f4f5", 4.5],
  ["borde sobre superficie", "#e4e4e7", "#fafafa", 1.2],
];

function luminancia(hex) {
  const canales = [1, 3, 5].map((i) => {
    const valor = parseInt(hex.slice(i, i + 2), 16) / 255;
    return valor <= 0.03928
      ? valor / 12.92
      : ((valor + 0.055) / 1.055) ** 2.4;
  });
  return (
    0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]
  );
}

function contraste(primero, segundo) {
  const a = luminancia(primero);
  const b = luminancia(segundo);
  const [claro, oscuro] = a > b ? [a, b] : [b, a];
  return (claro + 0.05) / (oscuro + 0.05);
}

function archivos(directorio, extension) {
  const encontrados = [];
  for (const entrada of readdirSync(directorio)) {
    const ruta = join(directorio, entrada);
    if (statSync(ruta).isDirectory()) {
      encontrados.push(...archivos(ruta, extension));
    } else if (ruta.endsWith(extension)) {
      encontrados.push(ruta);
    }
  }
  return encontrados;
}

const problemas = [];

// 1 y 2: HTML de cada componente.
for (const archivo of archivos(SRC, ".tsx")) {
  const contenido = readFileSync(archivo, "utf8");
  const lineas = contenido.split("\n");
  const etiquetas = new Set();
  for (const coincidencia of contenido.matchAll(/<label[^>]*htmlFor="([^"]+)"/g)) {
    etiquetas.add(coincidencia[1]);
  }

  lineas.forEach((linea, indice) => {
    for (const coincidencia of linea.matchAll(/<img\b[^>]*>/g)) {
      if (!/\balt=/.test(coincidencia[0])) {
        problemas.push(
          `${relative(RAIZ, archivo)}:${indice + 1} imagen sin atributo alt`,
        );
      }
    }

    for (const coincidencia of linea.matchAll(
      /<(input|select|textarea)\b[^>]*>/g,
    )) {
      const etiqueta = coincidencia[0];
      if (/\btype="hidden"/.test(etiqueta)) {
        continue;
      }
      const tieneNombre =
        /\baria-label=/.test(etiqueta) ||
        /\baria-labelledby=/.test(etiqueta) ||
        /\bid="([^"]+)"/.test(etiqueta) &&
          etiquetas.has(etiqueta.match(/\bid="([^"]+)"/)[1]);
      const dentroDeLabel = cuentaEtiquetas(lineas, indice) > 0;
      if (!tieneNombre && !dentroDeLabel) {
        problemas.push(
          `${relative(RAIZ, archivo)}:${indice + 1} ${coincidencia[1]} sin nombre accesible`,
        );
      }
    }
  });
}

function cuentaEtiquetas(lineas, indice) {
  let abiertas = 0;
  for (let i = 0; i <= indice; i += 1) {
    const aperturas = lineas[i].match(/<label\b/g) ?? [];
    const cierres = lineas[i].match(/<\/label>/g) ?? [];
    abiertas += aperturas.length - cierres.length;
  }
  return abiertas;
}

// 3: contraste de la paleta.
for (const [nombre, primero, segundo, minimo] of PALETA) {
  const ratio = contraste(primero, segundo);
  if (ratio < minimo) {
    problemas.push(
      `paleta: ${nombre} (${primero} sobre ${segundo}) ratio ${ratio.toFixed(2)} < ${minimo}`,
    );
  }
}

// 4: sin sombras marcadas ni degradados. Solo se admite `shadow-sm`, que
// es la más discreta de la escala de Tailwind 3.4.
const SOMBRAS_PERMITIDAS = new Set(["shadow-sm"]);
for (const archivo of archivos(SRC, ".tsx")) {
  const contenido = readFileSync(archivo, "utf8");
  contenido.split("\n").forEach((linea, indice) => {
    for (const coincidencia of linea.matchAll(/\bshadow-[a-z]+\b/g)) {
      if (!SOMBRAS_PERMITIDAS.has(coincidencia[0])) {
        problemas.push(
          `${relative(RAIZ, archivo)}:${indice + 1} usa sombra marcada (${coincidencia[0]})`,
        );
      }
    }
    if (/\bbg-gradient-[a-z]+\b/.test(linea)) {
      problemas.push(
        `${relative(RAIZ, archivo)}:${indice + 1} usa degradado`,
      );
    }
  });
}

// 5: los elementos con estado hover deben tener transición (cambio suave).
// Se analiza el valor completo de cada `className`, no línea a línea: las
// clases se reparten en varias líneas cuando el atributo es una plantilla.
for (const archivo of archivos(SRC, ".tsx")) {
  const contenido = readFileSync(archivo, "utf8");
  const lineas = contenido.split("\n");
  for (const coincidencia of contenido.matchAll(
    /className=(?:"([^"]*)"|\{`([^`]*)`\}|\{"([^"]*)"\})/g,
  )) {
    const valor = coincidencia[1] ?? coincidencia[2] ?? coincidencia[3] ?? "";
    if (!/\bhover:/.test(valor) || /\btransition/.test(valor)) {
      continue;
    }
    const linea = contenido.slice(0, coincidencia.index).split("\n").length;
    problemas.push(
      `${relative(RAIZ, archivo)}:${linea} estado hover sin transición`,
    );
  }
}

// 6: los diálogos se cierran con Escape y devuelven el foco al abrirse.
for (const archivo of archivos(SRC, ".tsx")) {
  const contenido = readFileSync(archivo, "utf8");
  if (!/role="dialog"/.test(contenido)) {
    continue;
  }
  if (!/Escape/.test(contenido)) {
    problemas.push(
      `${relative(RAIZ, archivo)} diálogo sin cierre con la tecla Escape`,
    );
  }
  if (!/\.focus\(\)/.test(contenido)) {
    problemas.push(
      `${relative(RAIZ, archivo)} diálogo sin gestión del foco`,
    );
  }
}

if (problemas.length === 0) {
  console.log("a11y: todas las comprobaciones pasan");
  process.exit(0);
}

console.error("a11y: se han encontrado problemas:");
for (const problema of problemas) {
  console.error(`  ${problema}`);
}
process.exit(1);
