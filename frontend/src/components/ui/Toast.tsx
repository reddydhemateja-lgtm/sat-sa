import { useEffect } from 'react';
import clsx from 'clsx';

type ToastTone = 'info' | 'success' | 'warning' | 'critical';

interface ToastProps {
  tone?: ToastTone;
  title: string;
  description?: string;
  onClose?: () => void;
  duration?: number;
}

const tones: Record<ToastTone, string> = {
  info: 'border-l-sky-500',
  success: 'border-l-emerald-500',
  warning: 'border-l-amber-500',
  critical: 'border-l-red-500',
};

export default function Toast({
  tone = 'info',
  title,
  description,
  onClose,
  duration = 5000,
}: ToastProps) {
  useEffect(() => {
    if (!onClose) return;
    const id = window.setTimeout(onClose, duration);
    return () => window.clearTimeout(id);
  }, [duration, onClose]);

  return (
    <div
      role="status"
      className={clsx(
        'pointer-events-auto w-80 rounded-md border border-slate-200 border-l-4 bg-white p-4 shadow-panel',
        'dark:border-navy-800 dark:bg-navy-900',
        tones[tone],
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-slate-900 dark:text-white">{title}</p>
          {description && (
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              {description}
            </p>
          )}
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            aria-label="Dismiss"
          >
            ×
          </button>
        )}
      </div>
    </div>
  );
}