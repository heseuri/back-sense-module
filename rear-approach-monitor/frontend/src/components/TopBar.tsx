import { ConnIndicator } from './ConnIndicator';
import { SourceBadge } from './SourceBadge';
import { useModeStore } from '../store/useModeStore';
import { useLiveStore } from '../store/useLiveStore';

/** 상단 바: 제목 + 데이터 출처 배지 + 연결 상태 + 모드 토글. */
export function TopBar({ title }: { title: string }) {
  const { mode, setMode, loading } = useModeStore();
  const live = useLiveStore((s) => s.live);
  const source = live?.source ?? mode;

  return (
    <header className="sticky top-0 z-20 pt-safe bg-base-900/85 backdrop-blur-lg border-b border-base-500/40">
      <div className="mx-auto flex max-w-xl items-center justify-between gap-2 px-4 py-3">
        <div className="min-w-0">
          <h1 className="truncate text-base font-bold tracking-tight">{title}</h1>
          <div className="mt-0.5 flex items-center gap-2">
            <SourceBadge source={source} />
            <ConnIndicator />
          </div>
        </div>

        {/* 모드 토글 */}
        <div className="flex shrink-0 rounded-xl bg-base-600/60 p-0.5 text-xs font-semibold">
          <button
            disabled={loading}
            onClick={() => setMode('simulation')}
            className={`rounded-lg px-2.5 py-1.5 transition-colors ${
              mode === 'simulation' ? 'bg-amber-500/80 text-base-900' : 'text-slate-300'
            }`}
          >
            시뮬레이션
          </button>
          <button
            disabled={loading}
            onClick={() => setMode('device')}
            className={`rounded-lg px-2.5 py-1.5 transition-colors ${
              mode === 'device' ? 'bg-accent text-base-900' : 'text-slate-300'
            }`}
          >
            실제 장치
          </button>
        </div>
      </div>
    </header>
  );
}
