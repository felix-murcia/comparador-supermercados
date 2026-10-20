import { describe, expect, it } from "vitest";

import { aplicarFiltros, opcionesDisponibles } from "@/lib/filtros";
import type { Filtros, ResultadoComparacion } from "@/lib/filtros";

const SIN_FILTROS: Filtros = {
  orden: "precio_unitario",
  precioMin: null,
  precioMax: null,
  marca: "",
  categoria: "",
  soloConStock: false,
};

function resultado(
  nombre: string,
  precio: string,
  extras: Partial<ResultadoComparacion> = {},
): ResultadoComparacion {
  return {
    posicion: 0,
    producto_id: "11111111-1111-1111-1111-111111111111",
    producto_cadena_id: "22222222-2222-2222-2222-222222222222",
    nombre,
    cadena: "dia",
    precio_eur: precio,
    precio_por_litro_kg: precio,
    marca: "Pascual",
    categoria: "lacteos",
    formato: "1L",
    disponible: true,
    url_producto: null,
    cadena_id: null,
    ...extras,
  };
}

describe("aplicarFiltros", () => {
  it("filtra por marca ignorando mayúsculas", () => {
    const resultados = [
      resultado("Leche", "1.00"),
      resultado("Agua", "0.50", { marca: "Aquarius" }),
    ];

    const filtrados = aplicarFiltros(resultados, {
      ...SIN_FILTROS,
      marca: "pascual",
    });

    expect(filtrados.map((r) => r.nombre)).toEqual(["Leche"]);
  });

  it("filtra por rango de precio", () => {
    const resultados = [
      resultado("Leche", "1.50"),
      resultado("Agua", "0.50"),
    ];

    const filtrados = aplicarFiltros(resultados, {
      ...SIN_FILTROS,
      precioMin: 1.0,
    });

    expect(filtrados.map((r) => r.nombre)).toEqual(["Leche"]);
  });

  it("filtra por disponibilidad", () => {
    const resultados = [
      resultado("Leche", "1.50", { disponible: true }),
      resultado("Agua", "0.50", { disponible: false }),
    ];

    const filtrados = aplicarFiltros(resultados, {
      ...SIN_FILTROS,
      soloConStock: true,
    });

    expect(filtrados.map((r) => r.nombre)).toEqual(["Leche"]);
  });

  it("ordena por precio unitario y renumera", () => {
    const resultados = [
      resultado("Leche", "1.50"),
      resultado("Agua", "0.50"),
    ];

    const filtrados = aplicarFiltros(resultados, SIN_FILTROS);

    expect(filtrados.map((r) => r.posicion)).toEqual([1, 2]);
    expect(filtrados[0].nombre).toBe("Agua");
  });

  it("deja al final los que no tienen precio por unidad", () => {
    const resultados = [
      resultado("Sin datos", "1.00", { precio_por_litro_kg: null }),
      resultado("Con datos", "1.00"),
    ];

    const filtrados = aplicarFiltros(resultados, {
      ...SIN_FILTROS,
      orden: "precio_kg_l",
    });

    expect(filtrados[filtrados.length - 1].nombre).toBe("Sin datos");
  });

  it("extrae las marcas y categorías disponibles", () => {
    const opciones = opcionesDisponibles([
      resultado("Leche", "1.00"),
      resultado("Agua", "0.50", {
        marca: "Aquarius",
        categoria: "bebidas",
      }),
    ]);

    expect(opciones.marcas).toEqual(["Aquarius", "Pascual"]);
    expect(opciones.categorias).toEqual(["bebidas", "lacteos"]);
  });
});
