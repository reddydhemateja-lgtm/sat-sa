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

  // Fire exactly once when the query settles into an error state.
  useEffect(() => {
    if (!isError || handledError.current) return;
    handledError.current = true;
    clearToken();
    reset();
  }, [isError, reset]);

  // No token → straight to login.
  if (!token) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  // Token present, query in flight → spinner.
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-navy-950">
        <Spinner size="lg" label="Verifying session…" />
      </div>
    );
  }

  // Token present, query failed → login.
  if (isError || (isFetched && !user)) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}