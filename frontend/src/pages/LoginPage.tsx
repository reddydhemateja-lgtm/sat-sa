import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { Loader2, ShieldCheck } from 'lucide-react';

import { login } from '../services/auth';
import { getToken } from '../services/api';

export default function LoginPage() {
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (getToken()) {
      setDone(true);
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        await login({
          username: 'admin',
          password: 'Admin@12345',
        });
        if (!cancelled) setDone(true);
      } catch (err) {
        if (!cancelled) {
          setError((err as Error).message ?? 'Auto-login failed');
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  if (done) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-navy-950">
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-md bg-navy-800 text-white">
          <ShieldCheck className="h-5 w-5" strokeWidth={2.2} />
        </div>
        <div>
          <p className="text-sm font-semibold tracking-tight text-slate-900 dark:text-white">
            SAT-SA
          </p>
          <p className="text-[10px] font-medium uppercase tracking-widest text-slate-500 dark:text-slate-400">
            Supervisory Analytics
          </p>
        </div>

        {error ? (
          <div className="mt-4 max-w-sm rounded-md border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
            <p className="font-medium">Sign-in failed</p>
            <p className="mt-1">{error}</p>
            <p className="mt-2 text-[11px] text-red-600/70 dark:text-red-400/70">
              Check that the backend is running and the ADMIN_PASSWORD matches.
            </p>
          </div>
        ) : (
          <div className="mt-4 flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>Preparing supervisory workspace…</span>
          </div>
        )}
      </div>
    </div>
  );
}