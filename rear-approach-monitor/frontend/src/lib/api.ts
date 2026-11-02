/** REST API 클라이언트. 백엔드 주소는 .env(VITE_API_BASE)로 설정. */

import type {
  AppSettings,
  DetectionRecord,
  DeviceStatus,
  Stats,
} from '../types';

/**
 * 백엔드 주소 결정 규칙:
 * 1) 빌드 시 VITE_API_BASE가 지정돼 있으면 그 값을 사용 (APK/배포/커스텀 환경).
 * 2) 네이티브 앱(Capacitor APK)인데 1)이 없으면 경고 — localhost는 "폰 자신"을
 *    가리켜 동작하지 않으므로, APK 빌드 시 반드시 PC의 LAN IP를 주입해야 한다.
 * 3) 웹 브라우저이면 "현재 접속한 호스트"의 8000 포트를 자동 사용한다.
 *    - PC에서 localhost로 열면  -> http://localhost:8000
 *    - 폰 브라우저에서 PC IP로 열면 -> http://<PC-IP>:8000
 */
const BACKEND_PORT = 8000;

/** Capacitor 네이티브(WebView) 환경인지 판별. */
function isNative(): boolean {
  const cap = (window as unknown as { Capacitor?: { isNativePlatform?: () => boolean } })
    .Capacitor;
  return !!cap?.isNativePlatform?.();
}

function autoBase(proto: 'http' | 'ws'): string {
  // 네이티브 앱에서 호스트가 localhost/capacitor 스킴이면 백엔드를 찾을 수 없다.
  if (isNative()) {
    console.warn(
      '[api] 네이티브 앱에서 VITE_API_BASE가 설정되지 않았습니다. ' +
        'APK 빌드 시 PC의 LAN IP(예: http://192.168.0.10:8000)를 지정하세요.',
    );
  }
  const host = window.location.hostname || 'localhost';
  const scheme = proto === 'http' ? 'http' : 'ws';
  return `${scheme}://${host}:${BACKEND_PORT}`;
}

export const API_BASE = import.meta.env.VITE_API_BASE ?? autoBase('http');
// WS_BASE: VITE_API_BASE가 주어지면 http->ws로 자동 변환해 일관성 유지.
export const WS_BASE =
  import.meta.env.VITE_WS_BASE ??
  (import.meta.env.VITE_API_BASE
    ? import.meta.env.VITE_API_BASE.replace(/^http/, 'ws')
    : autoBase('ws'));

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API ${path} 실패: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ status: string; mode: string }>('/api/health'),

  getSettings: () => req<AppSettings>('/api/settings'),
  updateSettings: (s: AppSettings) =>
    req<AppSettings>('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(s),
    }),

  getDevices: () => req<DeviceStatus[]>('/api/devices'),
  getStats: () => req<Stats>('/api/stats'),

  getDetections: (params?: {
    date?: string;
    object_type?: string;
    risk_level?: string;
    limit?: number;
  }) => {
    const q = new URLSearchParams();
    if (params?.date) q.set('date', params.date);
    if (params?.object_type) q.set('object_type', params.object_type);
    if (params?.risk_level) q.set('risk_level', params.risk_level);
    if (params?.limit) q.set('limit', String(params.limit));
    const qs = q.toString();
    return req<DetectionRecord[]>(`/api/detections${qs ? `?${qs}` : ''}`);
  },

  getMode: () => req<{ mode: string }>('/api/mode'),
  setMode: (mode: 'simulation' | 'device') =>
    req<{ mode: string }>('/api/mode', {
      method: 'POST',
      body: JSON.stringify({ mode }),
    }),

  triggerScenario: (scenario: 'danger_left' | 'danger_right' | 'clear') =>
    req<{ ok: boolean }>(`/api/simulate/${scenario}`, { method: 'POST' }),
};
