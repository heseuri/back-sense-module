import { useLiveStore, type ConnStatus } from '../store/useLiveStore';

const MAP: Record<ConnStatus, { label: string; color: string; dot: string }> = {
  connected: { label: '연결됨', color: 'text-risk-safe', dot: 'bg-risk-safe' },
  connecting: { label: '연결 중', color: 'text-risk-warning', dot: 'bg-risk-warning animate-pulse' },
  disconnected: { label: '연결 끊김', color: 'text-risk-danger', dot: 'bg-risk-danger animate-pulse' },
};

/** WebSocket 연결 상태 표시 (자동 재연결 시 'connecting') */
export function ConnIndicator() {
  const conn = useLiveStore((s) => s.conn);
  const m = MAP[conn];
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${m.color}`}>
      <span className={`h-2 w-2 rounded-full ${m.dot}`} />
      {m.label}
    </span>
  );
}
