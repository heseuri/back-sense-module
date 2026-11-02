import { useLiveStore } from '../store/useLiveStore';
import { useSettingsStore } from '../store/useSettingsStore';
import { useStale } from '../hooks/useStale';
import { moduleLabel, objectTypeLabel } from '../lib/labels';
import { AlertTriangleIcon, ObjectIcon, ArrowDownIcon } from './icons';

/**
 * 전역 위험 강조 오버레이 (명세 3.4: "위험 상황 발생 시 화면 강조").
 *
 * 최고 위험도가 danger이고 데이터가 최신일 때, 화면 가장자리에 붉은 테두리를
 * 펄스로 표시하고 하단에 가장 위험한 객체 요약을 띄운다.
 * - 오래된 데이터로는 강조하지 않는다 (stale 시 숨김).
 * - 테두리는 pointer-events-none 이라 조작을 방해하지 않는다.
 */
export function DangerOverlay() {
  const live = useLiveStore((s) => s.live);
  const settings = useSettingsStore((s) => s.settings);
  const stale = useStale();

  const isDanger =
    !stale &&
    settings.notifications_enabled &&
    live?.highest_risk === 'danger';

  if (!isDanger || !live) return null;

  // 가장 위험하고 가장 가까운 객체를 대표로 선택
  const danger = live.detections
    .filter((d) => d.risk_level === 'danger')
    .sort((a, b) => (a.distance ?? 99) - (b.distance ?? 99))[0];

  return (
    <div className="pointer-events-none fixed inset-0 z-40">
      {/* 붉은 테두리 글로우 (펄스) */}
      <div className="absolute inset-0 animate-pulse-danger rounded-[28px] ring-[6px] ring-inset ring-risk-danger/70 shadow-[inset_0_0_80px_rgba(239,68,68,0.35)]" />

      {/* 하단 요약 배너 */}
      {danger && (
        <div className="absolute inset-x-0 bottom-20 flex justify-center px-4 nav-safe-bottom">
          <div className="animate-slide-up flex w-full max-w-md items-center gap-3 rounded-2xl border border-risk-danger/60 bg-risk-danger/15 px-4 py-3 shadow-glow-danger backdrop-blur-xl">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-risk-danger/50 bg-base-900/50">
              <ObjectIcon type={danger.object_type} className="h-7 w-7 text-risk-danger" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5 text-sm font-bold text-risk-danger glow-danger">
                <AlertTriangleIcon className="h-4 w-4" />
                위험! {moduleLabel[danger.module]} {objectTypeLabel[danger.object_type]}
              </div>
              <div className="tabular mt-0.5 flex items-center gap-2 text-xs text-slate-200">
                {danger.movement === 'approaching' && (
                  <ArrowDownIcon className="h-3.5 w-3.5 text-risk-danger" />
                )}
                <span className="font-semibold">
                  {danger.distance != null ? `${danger.distance.toFixed(1)}m` : '거리 미상'}
                </span>
                {danger.speed != null && (
                  <span className="text-slate-400">
                    {Math.abs(danger.speed).toFixed(1)}m/s 접근
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
