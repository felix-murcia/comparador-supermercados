#!/usr/bin/env node
/**
 * Comprueba que no queden textos visibles escritos a mano en el JSX.
 *
 * Regla: cualquier literal de cadena en un atributo que no sea técnico
 * (clases, ids, URLs, atributos SVG…) debe salir de `locales/es.json` vía
 * `t()`. También revisa el texto de los nodos JSX.
 *
 * Los literales que sí son válidos (unidades, símbolos) están en PERMITIDOS.
 */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(RAIZ, "src");

/** Literales que no se traducen (unidades, símbolos o valores técnicos). */
const PERMITIDOS = new Set(["€", "€/kg-L", "€/kg", "€/L", "–", "—", "·"]);

/** Atributos cuyo valor literal no es texto visible para la persona usuaria. */
const ATRIBUTOS_TECNICOS = new Set([
  "autoComplete",
  "charSet",
  "className",
  "cx",
  "cy",
  "d",
  "defaultValue",
  "encoding",
  "fill",
  "fontFamily",
  "fontSize",
  "height",
  "href",
  "id",
  "inputMode",
  "key",
  "lang",
  "loading",
  "max",
  "min",
  "name",
  "opacity",
  "points",
  "priority",
  "r",
  "rel",
  "role",
  "rx",
  "ry",
  "src",
  "stroke",
  "strokeDasharray",
  "strokeLinecap",
  "strokeLinejoin",
  "strokeWidth",
  "step",
  "style",
  "target",
  "textAnchor",
  "type",
  "viewBox",
  "width",
  "x",
  "xmlns",
  "y",
]);

const PATRON_ATRIBUTO = /([A-Za-z][A-Za-z0-9-]*)=(?:"([^"]*)"|'([^']*)')/g;
const PATRON_TEXTO_JSX = />([^<>{}]*[A-Za-zÁÉÍÓÚÑáéíóúñ][^<>{}]*)</g;
const PATRON_METADATA = /\b(title|description|label)\s*:\s*"([^"]+)"/g;

function archivosTsx(directorio) {
  const encontrados = [];
  for (const entrada of readdirSync(directorio)) {
    const ruta = join(directorio, entrada);
    if (statSync(ruta).isDirectory()) {
      encontrados.push(...archivosTsx(ruta));
    } else if (ruta.endsWith(".tsx")) {
      encontrados.push(ruta);
    }
  }
  return encontrados;
}

function esPermitido(texto) {
  const limpio = texto.trim();
  if (!limpio || PERMITIDOS.has(limpio)) {
    return true;
  }
  // Valores técnicos: clases, identificadores o rutas.
  return /^[a-z0-9_.:/#-]+$/.test(limpio);
}

const problemas = [];

// Claves duplicadas: en JSON la última gana y oculta las anteriores.
for (const nombre of ["es.json"]) {
  const ruta = join(RAIZ, "src", "locales", nombre);
  let contenido;
  try {
    contenido = readFileSync(ruta, "utf8");
  } catch {
    continue;
  }
  const vistas = new Set();
  for (const coincidencia of contenido.matchAll(/^\s{2}"([^"]+)":/gm)) {
    if (vistas.has(coincidencia[1])) {
      problemas.push(`locales/${nombre}: clave duplicada "${coincidencia[1]}"`);
    }
    vistas.add(coincidencia[1]);
  }
}

for (const archivo of archivosTsx(SRC)) {
  const contenido = readFileSync(archivo, "utf8");
  const lineas = contenido.split("\n");

  lineas.forEach((linea, indice) => {
    for (const coincidencia of linea.matchAll(PATRON_ATRIBUTO)) {
      const atributo = coincidencia[1];
      const valor = coincidencia[2] ?? coincidencia[3] ?? "";
      if (ATRIBUTOS_TECNICOS.has(atributo) || esPermitido(valor)) {
        continue;
      }
      problemas.push({
        archivo: relative(RAIZ, archivo),
        linea: indice + 1,
        tipo: atributo,
        valor: valor.trim(),
      });
    }

    const sinEtiquetas = linea.replace(/<[^>]*>/g, "");
    for (const coincidencia of sinEtiquetas.matchAll(PATRON_TEXTO_JSX)) {
      const texto = coincidencia[1];
      if (esPermitido(texto)) {
        continue;
      }
      problemas.push({
        archivo: relative(RAIZ, archivo),
        linea: indice + 1,
        tipo: "texto",
        valor: texto.trim(),
      });
    }

    // La metadata (título y descripción de la pestaña) también es visible.
    for (const coincidencia of linea.matchAll(PATRON_METADATA)) {
      const valor = coincidencia[2];
      if (esPermitido(valor)) {
        continue;
      }
      problemas.push({
        archivo: relative(RAIZ, archivo),
        linea: indice + 1,
        tipo: `metadata.${coincidencia[1]}`,
        valor: valor.trim(),
      });
    }
  });
}

if (problemas.length === 0) {
  console.log("i18n: sin textos hardcodeados en el JSX");
  process.exit(0);
}

console.error("i18n: hay textos visibles fuera de locales/es.json:");
for (const problema of problemas) {
  console.error(
    `  ${problema.archivo}:${problema.linea} [${problema.tipo}] ${problema.valor}`,
  );
}
process.exit(1);