import { forwardRef, type InputHTMLAttributes } from 'react';
import clsx from 'clsx';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string | null;
  hint?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, hint, id, className, ...rest },
  ref,
) {
  const inputId = id ?? rest.name ?? undefined;

  return (
    <div className="w-full">
      {label && (
        <label htmlFor={inputId} className="label-base">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={clsx(
          'input-base',
          error && 'border-status-critical focus:border-status-critical focus:ring-status-critical/20',
          className,
        )}
        {...rest}
      />
      {error ? (
        <p className="mt-1 text-xs text-status-critical">{error}</p>
      ) : hint ? (
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p>
      ) : null}
    </div>
  );
});

export default Input;