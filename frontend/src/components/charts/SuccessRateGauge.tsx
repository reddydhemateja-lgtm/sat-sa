interface Props {
  /** Success rate as a percentage, 0-100 */
  value: number;
  label?: string;
  sublabel?: string;
}

export default function SuccessRateGauge({ value, label, sublabel }: Props) {
  const clamped = Math.max(0, Math.min(100, value));

  const size = 180;
  const strokeWidth = 16;
  const radius = (size - strokeWidth) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const startAngle = 135;
  const endAngle = 405;

  const angle = startAngle + (clamped / 100) * (endAngle - startAngle);

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

  // Green for high success, amber for medium, red for low
  const tone = clamped >= 95 ? '#16a34a' : clamped >= 75 ? '#d97706' : '#dc2626';

  return (
    <div className="flex flex-col items-center">
      <svg viewBox={`0 0 ${size} ${size}`} className="h-44 w-44">
        {/* Track */}
        <path
          d={arcPath(startAngle, endAngle)}
          fill="none"
          stroke="#1f3150"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Value arc */}
        <path
          d={arcPath(startAngle, angle)}
          fill="none"
          stroke={tone}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Center value */}
        <text
          x={cx}
          y={cy + 6}
          textAnchor="middle"
          fill="#e2e8f0"
          fontSize="26"
          fontWeight="600"
        >
          {clamped.toFixed(1)}%
        </text>
        <text
          x={cx}
          y={cy + 28}
          textAnchor="middle"
          fill="#94a3b8"
          fontSize="10"
          letterSpacing="1"
        >
          SUCCESS
        </text>
      </svg>
      {label && (
        <p className="mt-1 text-sm font-medium text-slate-800 dark:text-slate-200">
          {label}
        </p>
      )}
      {sublabel && (
        <p className="mt-0.5 text-[11px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {sublabel}
        </p>
      )}
    </div>
  );
}