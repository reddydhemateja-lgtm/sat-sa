import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
} from 'recharts';

interface DataPoint {
  label: string;
  EXECUTION_GAP: number;
  NEGATIVE_SPACE: number;
  ANOMALY: number;
  PEER_DEVIATION: number;
}

interface Props {
  data: DataPoint[];
}

export default function FindingsTrendChart({ data }: Props) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-xs text-slate-400">
        No trend data available
      </div>
    );
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
          <XAxis
            dataKey="label"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={{ stroke: '#334155' }}
          />
          <YAxis
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            axisLine={{ stroke: '#334155' }}
            tickLine={{ stroke: '#334155' }}
            allowDecimals={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0e1a30',
              border: '1px solid #1f3150',
              borderRadius: 6,
              fontSize: 12,
              color: '#e2e8f0',
            }}
            labelStyle={{ color: '#94a3b8', fontSize: 11 }}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} iconType="circle" />
          <Line type="monotone" dataKey="EXECUTION_GAP" name="Execution Gap" stroke="#dc2626" strokeWidth={2} dot={{ r: 3, fill: '#dc2626' }} />
          <Line type="monotone" dataKey="NEGATIVE_SPACE" name="Negative Space" stroke="#0ea5e9" strokeWidth={2} dot={{ r: 3, fill: '#0ea5e9' }} />
          <Line type="monotone" dataKey="ANOMALY" name="Anomaly" stroke="#d97706" strokeWidth={2} dot={{ r: 3, fill: '#d97706' }} />
          <Line type="monotone" dataKey="PEER_DEVIATION" name="Peer Deviation" stroke="#64748b" strokeWidth={2} dot={{ r: 3, fill: '#64748b' }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}