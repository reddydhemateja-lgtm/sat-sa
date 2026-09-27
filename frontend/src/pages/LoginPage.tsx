import { useState, type FormEvent } from 'react';
import { Navigate } from 'react-router-dom';
import { ShieldCheck, Loader2 } from 'lucide-react';

import Button from '../components/ui/Button';
import Input from '../components/ui/Input';
import { useLogin } from '../hooks/useAuth';
import { getToken } from '../services/api';
import { ApiRequestError } from '../services/api';

export default function LoginPage() {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const loginMutation = useLogin();

  if (getToken()) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await loginMutation.mutateAsync({ username, password });
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else {
        setError('Unable to reach the server. Please try again.');
      }
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-navy-950">
      {/* Left: brand panel */}
      <div className="hidden w-1/2 flex-col justify-between bg-navy-900 p-12 text-white lg:flex">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-navy-800">
            <ShieldCheck className="h-5 w-5" strokeWidth={2.2} />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight">SAT-SA</p>
            <p className="text-[10px] font-medium uppercase tracking-widest text-slate-400">
              Supervisory Analytics
            </p>
          </div>
        </div>

        <div className="max-w-md">
          <h1 className="text-3xl font-semibold leading-tight tracking-tight">
            Evidence-driven supervisory analytics for SOC assessment.
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-slate-300">
            Analyse periodic SOC operational evidence across Critical Sector Entities.
            Detect execution gaps, negative space, anomalies, and peer deviations — and
            review the supporting records before any supervisory conclusion is drawn.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4 text-xs text-slate-400">
          <div>
            <p className="font-semibold text-white">Execution Gaps</p>
            <p className="mt-1">Rule-based indicators with full evidence links.</p>
          </div>
          <div>
            <p className="font-semibold text-white">Negative Space</p>
            <p className="mt-1">Expected evidence that is missing from submissions.</p>
          </div>
          <div>
            <p className="font-semibold text-white">Peer Comparison</p>
            <p className="mt-1">Normalized indicators across configured peer groups.</p>
          </div>
        </div>
      </div>

      {/* Right: login form */}
      <div className="flex w-full items-center justify-center p-6 lg:w-1/2">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-md bg-navy-800 text-white">
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
            </div>
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-semibold tracking-tight text-slate-900 dark:text-white">
              Sign in
            </h2>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Use your supervisor or analyst credentials.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Username"
              name="username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
            />
            <Input
              label="Password"
              name="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            {error && (
              <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
                {error}
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full"
              disabled={loginMutation.isPending}
            >
              {loginMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Signing in…
                </>
              ) : (
                'Sign in'
              )}
            </Button>
          </form>

          <p className="mt-8 text-center text-[11px] text-slate-400 dark:text-slate-500">
            NTRO / NCIIPC — Supervisory Analytics Tool for SOC Assessment
          </p>
        </div>
      </div>
    </div>
  );
}