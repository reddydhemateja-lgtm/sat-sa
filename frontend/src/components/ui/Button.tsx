import { forwardRef, type ButtonHTMLAttributes } from 'react';
import clsx from 'clsx';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'subtle';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const variants: Record<Variant, string> = {
  primary:
    'bg-accent text-white hover:bg-accent-deep focus-visible:ring-accent/40 disabled:bg-accent/60',
  secondary:
    'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 focus-visible:ring-slate-400/40 ' +
    'dark:border-navy-700 dark:bg-navy-900 dark:text-slate-200 dark:hover:bg-navy-800',
  ghost:
    'text-slate-600 hover:bg-slate-100 focus-visible:ring-slate-400/40 ' +
    'dark:text-slate-300 dark:hover:bg-navy-800',
  subtle:
    'bg-slate-100 text-slate-700 hover:bg-slate-200 focus-visible:ring-slate-400/40 ' +
    'dark:bg-navy-800 dark:text-slate-200 dark:hover:bg-navy-700',
  danger:
    'bg-status-critical text-white hover:bg-red-700 focus-visible:ring-red-500/40',
};

const sizes: Record<Size, string> = {
  sm: 'h-8 px-3 text-xs gap-1.5',
  md: 'h-9 px-3.5 text-sm gap-2',
  lg: 'h-10 px-4 text-sm gap-2',
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'secondary',
    size = 'md',
    loading = false,
    leftIcon,
    rightIcon,
    className,
    children,
    disabled,
    ...rest
  },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={clsx(
        'inline-flex items-center justify-center rounded-md font-medium tracking-tight',
        'transition-colors duration-150 focus:outline-none focus-visible:ring-2',
        'disabled:cursor-not-allowed disabled:opacity-60',
        variants[variant],
        sizes[size],
        className,
      )}
      {...rest}
    >
      {loading ? (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        leftIcon
      )}
      {children}
      {!loading && rightIcon}
    </button>
  );
});

export default Button;