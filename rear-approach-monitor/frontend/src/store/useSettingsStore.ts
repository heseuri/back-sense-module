/** 앱 설정 전역 상태 (백엔드와 동기화). */

import { create } from 'zustand';
import { api } from '../lib/api';
import type { AppSettings } from '../types';

const DEFAULTS: AppSettings = {
  danger_distance_m: 2.0,
  warning_distance_m: 5.0,
  danger_speed_mps: 3.0,
  notifications_enabled: true,
  sound_enabled: true,
  vibration_enabled: true,
  led_enabled: true,
  alert_cooldown_sec: 5.0,
  detect_person: true,
  detect_bicycle: true,
  detect_car: true,
  detect_motorcycle: true,
  show_camera: true,
};

interface SettingsStore {
  settings: AppSettings;
  loaded: boolean;
  saving: boolean;
  fetch: () => Promise<void>;
  save: (next: AppSettings) => Promise<void>;
  update: (patch: Partial<AppSettings>) => void;
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  settings: DEFAULTS,
  loaded: false,
  saving: false,
  fetch: async () => {
    try {
      const s = await api.getSettings();
      set({ settings: s, loaded: true });
    } catch {
      set({ loaded: true }); // 백엔드 미기동 시 기본값 유지
    }
  },
  save: async (next) => {
    set({ saving: true });
    try {
      const saved = await api.updateSettings(next);
      set({ settings: saved });
    } finally {
      set({ saving: false });
    }
  },
  update: (patch) => set({ settings: { ...get().settings, ...patch } }),
}));
