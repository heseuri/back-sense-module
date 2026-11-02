import { useEffect, useState } from 'react';
import { useLiveStore } from '../store/useLiveStore';

/**
 * 마지막 메시지 수신 이후 경과 시간이 임계값을 넘으면 stale=true.
 * 오래된 센서 데이터로 위험도를 판단하지 않도록 UI에서 경고하는 데 사용 (명세 8절).
 */
export function useStale(thresholdSec = 3): boolean {
  const lastMessageAt = useLiveStore((s) => s.lastMessageAt);
  const conn = useLiveStore((s) => s.conn);
  const [, tick] = useState(0);

  // 1초마다 재평가
  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(id);
  }, []);

  if (conn !== 'connected') return true;
  if (lastMessageAt == null) return true;
  return (Date.now() - lastMessageAt) / 1000 > thresholdSec;
}
