"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Punto = {
  fecha: string;
  [cadena: string]: string | number;
};

const COLORES = ["#1a73e8", "#d93025", "#00913f", "#f4b400", "#a142f4"];

/** Gráfica del histórico de precios: una línea por cadena. */
export function GraficaHistorico({
  puntos,
  cadenas,
}: {
  puntos: Punto[];
  cadenas: string[];
}) {
  if (puntos.length === 0) {
    return null;
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={puntos} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="#e8eaed" strokeDasharray="3 3" />
          <XAxis dataKey="fecha" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} width={48} domain={["auto", "auto"]} />
          <Tooltip />
          <Legend />
          {cadenas.map((cadena, indice) => (
            <Line
              key={cadena}
              type="monotone"
              dataKey={cadena}
              name={cadena}
              stroke={COLORES[indice % COLORES.length]}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
