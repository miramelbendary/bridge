"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Point = { label: string; average: number; attempts: number };

/** Horizontal bars, one hue (single measure), labelled axes, accessible table fallback. */
export function CompetencyChart({ data }: { data: Point[] }) {
  return (
    <figure>
      <div className="h-[340px] w-full" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 8, bottom: 8 }}>
            <CartesianGrid horizontal={false} strokeOpacity={0.25} />
            <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 12 }} />
            <YAxis type="category" dataKey="label" width={170} tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(value) => [`${value}`, "Average score"]}
              contentStyle={{ fontSize: 12, borderRadius: 6 }}
            />
            <Bar dataKey="average" fill="#0f766e" radius={[0, 4, 4, 0]} maxBarSize={18} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="sr-only">
        <table>
          <thead>
            <tr>
              <th>Competency</th>
              <th>Average</th>
              <th>Attempts</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.label}>
                <td>{d.label}</td>
                <td>{d.average}</td>
                <td>{d.attempts}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </figcaption>
    </figure>
  );
}
