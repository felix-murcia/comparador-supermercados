/** Tipos de la lista de la compra y de su resumen de ahorro. */

export type Item = {
  id: string;
  producto_id: string;
  cantidad: number;
  cadena_compra_id: string | null;
  precio_snapshot: string | null;
  producto_nombre: string | null;
  producto_marca: string | null;
  cadena_compra: string | null;
};

export type Lista = {
  id: string;
  nombre: string;
  items: Item[];
};

export type CosteCadena = {
  cadena: string;
  coste: string;
  porcentaje_a: number | null;
  productos_no_disponibles: string[];
};

/** Producto equivalente usado en una cadena, con su marca. */
export type Equivalente = {
  nombre: string;
  marca: string | null;
};

/** Un producto de la lista con su precio en cada cadena. */
export type ProductoResumen = {
  producto_id: string;
  nombre: string;
  cantidad: number;
  precios: Record<string, string>;
  equivalentes: Record<string, Equivalente>;
  mejor_cadena: string | null;
  ahorro: string | null;
};

export type Resumen = {
  coste_total: string;
  por_cadena: CosteCadena[];
  porcentaje_c: number | null;
  coste_optimo: string;
  coste_mixta_real: string;
  avisos: string[];
  productos: ProductoResumen[];
  /** Cadena donde la lista sale más barata. */
  mejor_cadena: string | null;
  /** Ahorro frente a la cadena más cara. */
  ahorro_maximo: string | null;
};
