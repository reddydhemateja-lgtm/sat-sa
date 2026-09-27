import clsx from 'clsx';

type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'critical' | 'high';

interface BadgeProps {
  children: React.ReactNode;
  tone?: Tone;
  className?: string;
}

const tones: Record<Tone, string> = {
  neutral:
    'bg-slate-100 text-slate-700 ring-slate-200 ' +
    'dark:bg-navy-800 dark:text-slate-300 dark:ring-navy-700',
  info:
    'bg-sky-50 text-sky-700 ring-sky-200 ' +
    'dark:bg-sky-950/40 dark:text-sky-300 dark:ring-sky-900',
  success:
    'bg-emerald-50 text-emerald-700 ring-emerald-200 ' +
    'dark:bg-emerald-950/40 dark:text-emerald-300 dark:ring-emerald-900',
  warning:
    'bg-amber-50 text-amber-700 ring-amber-200 ' +
    'dark:bg-amber-950/40 dark:text-amber-300 dark:ring-amber-900',
  high:
    'bg-orange-50 text-orange-700 ring-orange-200 ' +
    'dark:bg-orange-950/40 dark:text-orange-300 dark:ring-orange-900',
  critical:
    'bg-red-50 text-red-700 ring-red-200 ' +
    'dark:bg-red-950/40 dark:text-red-300 dark:ring-red-900',
};

export default function Badge({ children, tone = 'neutral', className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}