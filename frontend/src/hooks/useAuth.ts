import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import * as authService from '../services/auth';
import { clearToken, getToken } from '../services/api';
import type { LoginRequest, User } from '../types';

const ME_KEY = ['auth', 'me'] as const;

export function useCurrentUser() {
  const hasToken = Boolean(getToken());
  return useQuery<User>({
    queryKey: ME_KEY,
    queryFn: authService.fetchCurrentUser,
    enabled: hasToken,
    // Retry on network failures (cold starts) but not on 401 (real auth failure)
    retry: (failureCount, error) => {
      const status = (error as { status?: number })?.status;
      if (status === 401 || status === 403) return false;
      return failureCount < 3;
    },
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 8000),
    refetchOnMount: true,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
    staleTime: 5 * 60 * 1000,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: (payload: LoginRequest) => authService.login(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(ME_KEY, data.user);
      navigate('/dashboard', { replace: true });
    },
  });
}

export function useLogout() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useCallback(() => {
    clearToken();
    queryClient.removeQueries({ queryKey: ME_KEY });
    navigate('/login', { replace: true });
  }, [navigate, queryClient]);
}