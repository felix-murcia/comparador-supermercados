"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Punto = {
  dia: string;
  verificado: number;
  sospechoso: number;
  rechazado: number;
};

/** Reparto diario de la ingesta por estado. */
export function GraficaMetricas({ puntos }: { puntos: Punto[] }) {
  if (puntos.length === 0) {
    return null;
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={puntos}>
          <CartesianGrid stroke="#e8eaed" strokeDasharray="3 3" />
          <XAxis dataKey="dia" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} allowDecimals={false} />
          <Tooltip />
          <Legend />
          <Bar dataKey="verificado" name="Verificados" fill="#1a73e8" />
          <Bar dataKey="sospechoso" name="Sospechosos" fill="#f4b400" />
          <Bar dataKey="rechazado" name="Rechazados" fill="#d93025" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
