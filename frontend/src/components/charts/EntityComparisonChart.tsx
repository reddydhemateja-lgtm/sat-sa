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
  entity_id: number;
  code: string;
  indicator: number;
  findings: number;
}

interface Props {
  data: Datum[];
}

export default function EntityComparisonChart({ data }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-56 items-center justify-center text-xs text-slate-400">
        No entity data available
      </div>
    );
  }

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
          <XAxis type="number" domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#334155' }} tickLine={{ stroke: '#334155' }} />
          <YAxis type="category" dataKey="code" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={{ stroke: '#334155' }} tickLine={{ stroke: '#334155' }} width={80} />
          <Tooltip
            cursor={{ fill: '#1f3150', opacity: 0.3 }}
            contentStyle={{ backgroundColor: '#0e1a30', border: '1px solid #1f3150', borderRadius: 6, fontSize: 12, color: '#e2e8f0' }}
            formatter={(v: number) => [v.toFixed(1), 'Indicator']}
          />
          <Bar dataKey="indicator" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.indicator >= 70 ? '#dc2626' : d.indicator >= 40 ? '#d97706' : '#16a34a'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}