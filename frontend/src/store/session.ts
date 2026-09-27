import { create } from 'zustand';

import type { User } from '../types';
import { getToken } from '../services/api';

interface SessionState {
  user: User | null;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  reset: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  user: null,
  isAuthenticated: Boolean(getToken()),
  setUser: (user) => set({ user, isAuthenticated: user !== null }),
  reset: () => set({ user: null, isAuthenticated: false }),
}));