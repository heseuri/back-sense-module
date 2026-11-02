/** 동작 모드(시뮬레이션/실제장치) 전역 상태. */

import { create } from 'zustand';
import { api } from '../lib/api';
import type { DataSource } from '../types';

interface ModeStore {
  mode: DataSource;
  loading: boolean;
  fetchMode: () => Promise<void>;
  setMode: (mode: DataSource) => Promise<void>;
}

export const useModeStore = create<ModeStore>((set) => ({
  mode: 'simulation',
  loading: false,
  fetchMode: async () => {
    try {
      const { mode } = await api.getMode();
      set({ mode: mode as DataSource });
    } catch {
      /* 백엔드 미기동 시 무시 */
    }
  },
  setMode: async (mode) => {
    set({ loading: true });
    try {
      const res = await api.setMode(mode);
      set({ mode: res.mode as DataSource });
    } finally {
      set({ loading: false });
    }
  },
}));
