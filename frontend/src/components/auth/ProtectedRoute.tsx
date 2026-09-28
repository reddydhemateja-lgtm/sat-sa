import { useEffect, useRef } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { clearToken, getToken } from '../../services/api';
import { useCurrentUser } from '../../hooks/useAuth';
import { useSessionStore } from '../../store/session';
import Spinner from '../ui/Spinner';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation();
  const token = getToken();
  const { data: user, isLoading, isError, isFetched } = useCurrentUser();
  const setUser = useSessionStore((s) => s.setUser);
  const reset = useSessionStore((s) => s.reset);
  const handledError = useRef(false);

  useEffect(() => {
    if (user) setUser(user);
  }, [user, setUser]);

  // Only bail to login once we've actually tried and failed (not during cold-start).
  useEffect(() => {
    if (!isError || handledError.current) return;
    handledError.current = true;
    clearToken();
    reset();
  }, [isError, reset]);

  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  // Still resolving — show a real "cold start" message on first load.
  if (isLoading && !isFetched) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3 bg-slate-50 dark:bg-navy-950">
        <Spinner size="lg" />
        <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
          Connecting to server…
        </p>
        <p className="max-w-xs text-center text-xs text-slate-500 dark:text-slate-400">
          If the service has been idle, this may take up to 60 seconds.
        </p>
      </div>
    );
  }

  if (isError || (isFetched && !user)) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}