import { create } from 'zustand';

export type DataMode = 'complete' | 'modified';

const STORAGE_KEY = 'sat-sa-data-mode';

function readInitial(): DataMode {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'complete' || stored === 'modified') return stored;
  return 'complete';
}

interface DataModeState {
  mode: DataMode;
  setMode: (mode: DataMode) => void;
}

export const useDataModeStore = create<DataModeState>((set) => ({
  mode: readInitial(),
  setMode: (mode) => {
    localStorage.setItem(STORAGE_KEY, mode);
    set({ mode });
  },
}));