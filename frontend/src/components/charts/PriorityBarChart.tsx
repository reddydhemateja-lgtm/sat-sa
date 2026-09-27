import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

interface Datum {
  name: string;
  value: number;
  color: string;
}

interface Props {
  data: Datum[];
}

export default function PriorityBarChart({ data }: Props) {
  if (!data || data.every((d) => d.value === 0)) {
    return (
      <div className="flex h-56 items-center justify-center text-xs text-slate-400">
        No priority data available
      </div>
    );
  }

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 16, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
          <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#334155' }} tickLine={{ stroke: '#334155' }} />
          <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#334155' }} tickLine={{ stroke: '#334155' }} allowDecimals={false} />
          <Tooltip
            cursor={{ fill: '#1f3150', opacity: 0.3 }}
            contentStyle={{ backgroundColor: '#0e1a30', border: '1px solid #1f3150', borderRadius: 6, fontSize: 12, color: '#e2e8f0' }}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}