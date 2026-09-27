import { api, clearToken, setToken } from './api';
import type { LoginRequest, LoginResponse, User } from '../types';

export async function login(payload: LoginRequest): Promise<LoginResponse> {
  const data = await api.post<LoginResponse>('/auth/login', payload);
  setToken(data.access_token);
  return data;
}

export async function logout(): Promise<void> {
  clearToken();
}

export async function fetchCurrentUser(): Promise<User> {
  return api.get<User>('/auth/me');
}