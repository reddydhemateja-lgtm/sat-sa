interface Props {
  value: number;
  label?: string;
}

export default function IndicatorGauge({ value, label }: Props) {
  const clamped = Math.max(0, Math.min(100, value));

  const size = 180;
  const strokeWidth = 16;
  const radius = (size - strokeWidth) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const startAngle = 135;
  const endAngle = 405;

  const angle = startAngle + (clamped / 100) * (endAngle - startAngle);
  const angleRad = (angle * Math.PI) / 180;

  const arcPath = (start: number, end: number) => {
    const s = (start * Math.PI) / 180;
    const e = (end * Math.PI) / 180;
    const x1 = cx + radius * Math.cos(s);
    const y1 = cy + radius * Math.sin(s);
    const x2 = cx + radius * Math.cos(e);
    const y2 = cy + radius * Math.sin(e);
    const largeArc = end - start > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`;
  };

  const needleX = cx + (radius - strokeWidth - 8) * Math.cos(angleRad);
  const needleY = cy + (radius - strokeWidth - 8) * Math.sin(angleRad);

  const tone = clamped >= 70 ? '#dc2626' : clamped >= 40 ? '#d97706' : '#16a34a';

  return (
    <div className="flex flex-col items-center">
      <svg viewBox={`0 0 ${size} ${size}`} className="h-44 w-44">
        <path d={arcPath(startAngle, endAngle)} fill="none" stroke="#1f3150" strokeWidth={strokeWidth} strokeLinecap="round" />
        <path d={arcPath(startAngle, angle)} fill="none" stroke={tone} strokeWidth={strokeWidth} strokeLinecap="round" />
        <line x1={cx} y1={cy} x2={needleX} y2={needleY} stroke="#e2e8f0" strokeWidth={2.5} strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={5} fill="#e2e8f0" />
        <text x={cx} y={cy + 34} textAnchor="middle" fill="#e2e8f0" fontSize="22" fontWeight="600">
          {clamped.toFixed(0)}
        </text>
      </svg>
      {label && (
        <p className="mt-1 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {label}
        </p>
      )}
    </div>
  );
}