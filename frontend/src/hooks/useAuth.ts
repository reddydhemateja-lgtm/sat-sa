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
    retry: false,
    refetchOnMount: false,
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