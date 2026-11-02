/**
 * 전역 실시간 상태 스토어 (Zustand).
 *
 * - WebSocket 연결/자동 재연결 관리
 * - live_state / alert 메시지 처리
 * - 최신 감지 스냅샷, 연결 상태, 알림 큐 보관
 *
 * 명세 8절: WebSocket 연결이 끊어지면 자동 재연결을 시도한다.
 * 오래된 데이터로 위험도를 판단하지 않도록, stale 여부는 server_time과 비교해 UI에서 판정한다.
 */

import { create } from 'zustand';
import { WS_BASE } from '../lib/api';
import type { DetectionEvent, LiveState } from '../types';

export type ConnStatus = 'connecting' | 'connected' | 'disconnected';

export interface AlertItem {
  id: string;
  event: DetectionEvent;
  receivedAt: number;
}

interface LiveStore {
  conn: ConnStatus;
  live: LiveState | null;
  /** 가장 최근에 도착한 위험 알림들 (화면 표시용, 최대 20개) */
  alerts: AlertItem[];
  /** 마지막 WebSocket 메시지 수신 시각 (epoch ms) */
  lastMessageAt: number | null;

  connect: () => void;
  disconnect: () => void;
  dismissAlert: (id: string) => void;
  clearAlerts: () => void;
}

let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let pingTimer: ReturnType<typeof setInterval> | null = null;
let reconnectDelay = 1000; // 지수 백오프 시작값

export const useLiveStore = create<LiveStore>((set, get) => ({
  conn: 'disconnected',
  live: null,
  alerts: [],
  lastMessageAt: null,

  connect: () => {
    // 이미 연결/연결중이면 중복 연결 방지
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    set({ conn: 'connecting' });
    const ws = new WebSocket(`${WS_BASE}/ws/stream`);
    socket = ws;

    ws.onopen = () => {
      set({ conn: 'connected' });
      reconnectDelay = 1000; // 성공 시 백오프 리셋
      // 연결 유지용 ping
      pingTimer = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 15000);
    };

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        set({ lastMessageAt: Date.now() });

        if (msg.type === 'live_state') {
          set({ live: msg.data as LiveState });
        } else if (msg.type === 'alert') {
          const event = msg.data as DetectionEvent;
          const item: AlertItem = {
            id: `${event.track_id ?? 'x'}-${Date.now()}`,
            event,
            receivedAt: Date.now(),
          };
          set((s) => ({ alerts: [item, ...s.alerts].slice(0, 20) }));
        }
      } catch {
        // malformed 메시지 무시
      }
    };

    const scheduleReconnect = () => {
      set({ conn: 'disconnected' });
      if (pingTimer) {
        clearInterval(pingTimer);
        pingTimer = null;
      }
      // 자동 재연결 (지수 백오프, 최대 10초)
      if (reconnectTimer) clearTimeout(reconnectTimer);
      reconnectTimer = setTimeout(() => {
        reconnectDelay = Math.min(reconnectDelay * 1.6, 10000);
        get().connect();
      }, reconnectDelay);
    };

    ws.onclose = scheduleReconnect;
    ws.onerror = () => {
      ws.close();
    };
  },

  disconnect: () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (pingTimer) {
      clearInterval(pingTimer);
      pingTimer = null;
    }
    if (socket) {
      socket.onclose = null; // 재연결 방지
      socket.close();
      socket = null;
    }
    set({ conn: 'disconnected' });
  },

  dismissAlert: (id) =>
    set((s) => ({ alerts: s.alerts.filter((a) => a.id !== id) })),
  clearAlerts: () => set({ alerts: [] }),
}));
