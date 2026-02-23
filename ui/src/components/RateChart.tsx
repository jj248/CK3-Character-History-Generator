import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface SingleSeriesProps {
  title: string;
  rates: number[];
  color: string;
  seriesLabel: string;
}

// One line - used for desperation marriage rates and individual male/female series
export function RateChartSingle({ title, rates, color, seriesLabel }: SingleSeriesProps) {
  const data = rates.map((value, age) => ({ age, value: Math.round(value * 10000) / 10000 }));

  return (
    <div style={{ marginBottom: "1rem" }}>
      <h3 style={{ marginBottom: "0.5rem" }}>{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#3a2a1a" />
          <XAxis
            dataKey="age"
            label={{ value: "Age", position: "insideBottom", offset: -2, fill: "#8a7460" }}
            tick={{ fill: "#8a7460", fontSize: 11 }}
          />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(v: number) => v.toFixed(2)}
            tick={{ fill: "#8a7460", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{ background: "#2e2218", border: "1px solid #5a3e28", color: "#e8d5b0" }}
            formatter={(v: number) => [v.toFixed(4), seriesLabel]}
            labelFormatter={(age) => `Age ${age}`}
          />
          <Legend wrapperStyle={{ color: "#c4a96e", fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            dot={false}
            strokeWidth={2}
            name={seriesLabel}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

interface DualSeriesProps {
  title: string;
  maleRates: number[];
  femaleRates: number[];
}

// Two lines (male + female) on the same chart
export function RateChartDual({ title, maleRates, femaleRates }: DualSeriesProps) {
  const len = Math.max(maleRates.length, femaleRates.length);
  const data = Array.from({ length: len }, (_, age) => ({
    age,
    male:   Math.round((maleRates[age]   ?? 0) * 10000) / 10000,
    female: Math.round((femaleRates[age] ?? 0) * 10000) / 10000,
  }));

  return (
    <div style={{ marginBottom: "1rem" }}>
      <h3 style={{ marginBottom: "0.5rem" }}>{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#3a2a1a" />
          <XAxis
            dataKey="age"
            label={{ value: "Age", position: "insideBottom", offset: -2, fill: "#8a7460" }}
            tick={{ fill: "#8a7460", fontSize: 11 }}
          />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(v: number) => v.toFixed(2)}
            tick={{ fill: "#8a7460", fontSize: 11 }}
          />
          <Tooltip
            contentStyle={{ background: "#2e2218", border: "1px solid #5a3e28", color: "#e8d5b0" }}
            formatter={(v: number, name: string) => [v.toFixed(4), name]}
            labelFormatter={(age) => `Age ${age}`}
          />
          <Legend wrapperStyle={{ color: "#c4a96e", fontSize: 12 }} />
          <Line type="monotone" dataKey="male"   stroke="#5b8dd9" dot={false} strokeWidth={2} name="Male"   />
          <Line type="monotone" dataKey="female" stroke="#d96b6b" dot={false} strokeWidth={2} name="Female" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}