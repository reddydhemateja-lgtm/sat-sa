import clsx from 'clsx';

interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
}

const sizes = {
  sm: 'h-4 w-4 border-2',
  md: 'h-6 w-6 border-2',
  lg: 'h-8 w-8 border-[3px]',
};

export default function Spinner({ size = 'md', className, label }: SpinnerProps) {
  return (
    <div className={clsx('flex items-center gap-2 text-slate-500 dark:text-slate-400', className)}>
      <span
        role="status"
        aria-label={label ?? 'Loading'}
        className={clsx(
          'animate-spin rounded-full border-current border-t-transparent text-accent',
          sizes[size],
        )}
      />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}