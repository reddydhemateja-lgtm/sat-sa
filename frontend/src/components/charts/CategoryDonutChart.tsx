import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

interface Slice {
  name: string;
  value: number;
  color: string;
}

interface Props {
  data: Slice[];
  centerLabel?: string;
  centerValue?: number | string;
}

export default function CategoryDonutChart({
  data,
  centerLabel = 'findings',
  centerValue,
}: Props) {
  const filtered = data.filter((d) => d.value > 0);

  if (filtered.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-slate-400">
        No data to display
      </div>
    );
  }

  const computedTotal = filtered.reduce((s, d) => s + d.value, 0);
  const total = centerValue !== undefined ? centerValue : computedTotal;

  return (
    <div className="relative h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={filtered}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={95}
            paddingAngle={2}
            dataKey="value"
            stroke="#0e1a30"
            strokeWidth={2}
          >
            {filtered.map((slice, i) => (
              <Cell key={i} fill={slice.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: '#0e1a30',
              border: '1px solid #1f3150',
              borderRadius: 6,
              fontSize: 12,
              color: '#e2e8f0',
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} iconType="circle" />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-semibold text-slate-900 dark:text-white">
          {typeof total === 'number' ? total.toLocaleString() : total}
        </span>
        <span className="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {centerLabel}
        </span>
      </div>
    </div>
  );
}