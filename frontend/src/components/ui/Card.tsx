import clsx from 'clsx';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  padded?: boolean;
}

export default function Card({ className, padded = true, children, ...rest }: CardProps) {
  return (
    <div className={clsx('card-base', padded && 'p-5', className)} {...rest}>
      {children}
    </div>
  );
}

interface CardHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export function CardHeader({ title, subtitle, action, className }: CardHeaderProps) {
  return (
    <div className={clsx('mb-4 flex items-start justify-between gap-4', className)}>
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-slate-900 dark:text-white">
          {title}
        </h3>
        {subtitle && (
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{subtitle}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}