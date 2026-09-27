import { Link } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';

export default function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-8 text-center dark:bg-navy-950">
      <div className="flex h-12 w-12 items-center justify-center rounded-md bg-navy-800 text-white">
        <ShieldAlert className="h-5 w-5" strokeWidth={2.2} />
      </div>
      <p className="mt-6 text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">
        404
      </p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-slate-900 dark:text-white">
        Page not found
      </h1>
      <p className="mt-2 max-w-md text-sm text-slate-500 dark:text-slate-400">
        The page you requested is not part of the Supervisory Analytics Tool. Return to
        the dashboard to continue.
      </p>
      <Link
        to="/dashboard"
        className="mt-6 inline-flex items-center rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-deep"
      >
        Back to Dashboard
      </Link>
    </div>
  );
}