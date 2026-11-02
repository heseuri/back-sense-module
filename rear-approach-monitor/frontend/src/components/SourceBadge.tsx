import type { DataSource } from '../types';

/**
 * 데이터 출처 배지.
 * 시뮬레이션 데이터와 실제 데이터를 명확히 구분한다 (명세 6절).
 */
export function SourceBadge({ source }: { source: DataSource }) {
  if (source === 'simulation') {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 border border-amber-500/40 px-2.5 py-1 text-xs font-semibold text-amber-300">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />
        시뮬레이션
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-accent/15 border border-accent/40 px-2.5 py-1 text-xs font-semibold text-accent">
      <span className="h-1.5 w-1.5 rounded-full bg-accent" />
      실제 장치
    </span>
  );
}
