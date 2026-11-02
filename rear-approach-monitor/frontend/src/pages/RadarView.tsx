import { Layout } from '../components/Layout';
import { useLiveStore } from '../store/useLiveStore';
import { useStale } from '../hooks/useStale';
import type { DetectionEvent } from '../types';
import { moduleLabel, objectTypeLabel, riskColor } from '../lib/labels';
import { ObjectIcon, PersonIcon, ArrowDownIcon, ArrowUpIcon } from '../components/icons';

/**
 * 3.2 후방 감지 시각화
 *
 * ⚠️ 중요 제약 (명세 3.2):
 * 레이더만으로 정확한 2차원 위치가 계산되지 않으므로 임의의 (x,y) 위치를 생성하지 않는다.
 * 대신 "좌/우 감지 영역" + "거리" 정보만으로 배치한다.
 * - 가로: 좌/우 영역(고정 레인)  - 세로: 거리에 비례
 */
const MAX_RANGE_M = 12;

export default function RadarView() {
  const live = useLiveStore((s) => s.live);
  const stale = useStale();
  const detections = live?.detections ?? [];

  const left = detections.filter((d) => d.module === 'left');
  const right = detections.filter((d) => d.module === 'right');

  return (
    <Layout title="후방 감지 시각화">
      <p className="mb-3 text-xs leading-relaxed text-slate-400">
        사용자 기준 후방 접근 상황. 레이더는 정확한 2D 좌표를 제공하지 않으므로
        <span className="text-slate-200"> 좌/우 영역과 거리</span>로만 표시합니다.
      </p>

      <div className="card relative overflow-hidden p-3">
        {/* 배경 그리드 + 거리 눈금 */}
        <div className="pointer-events-none absolute inset-0 px-3 py-3">
          {[MAX_RANGE_M, 9, 6, 3, 0].map((m, i) => (
            <div
              key={m}
              className="absolute inset-x-3 flex items-center gap-2"
              style={{ top: `${(i / 4) * 100}%` }}
            >
              <span className="w-7 shrink-0 text-[9px] text-slate-600 tabular">{m}m</span>
              <div className="h-px flex-1 bg-gradient-to-r from-accent/5 via-accent/15 to-accent/5" />
            </div>
          ))}
        </div>

        {/* 두 레인 */}
        <div className="relative grid grid-cols-2 gap-2.5 pl-7" style={{ height: 380 }}>
          <Zone side="left" detections={left} />
          <Zone side="right" detections={right} />
        </div>

        {/* 사용자 (중앙 하단 = 거리 0) */}
        <div className="relative mt-2 flex flex-col items-center pb-1">
          <div className="absolute -top-6 h-16 w-16 rounded-full bg-accent/20 animate-ping-ring" />
          <div className="z-10 flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-accent to-accent-soft shadow-glow-accent">
            <PersonIcon className="h-7 w-7 text-base-900" />
          </div>
          <span className="mt-1.5 text-[11px] font-bold text-accent glow-accent">사용자</span>
        </div>

        {stale && (
          <div className="absolute inset-0 flex items-center justify-center bg-base-900/70 backdrop-blur-sm">
            <span className="flex items-center gap-2 rounded-full bg-base-800 px-4 py-2 text-sm text-amber-300">
              <span className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
              최신 데이터 수신 대기 중
            </span>
          </div>
        )}
      </div>

      {/* 범례 */}
      <section className="mt-3 card flex items-center justify-between p-3.5">
        <span className="text-xs font-semibold text-slate-300">위험도</span>
        <div className="flex gap-4 text-xs">
          <Legend hex={riskColor.safe.hex} label="안전" />
          <Legend hex={riskColor.warning.hex} label="주의" />
          <Legend hex={riskColor.danger.hex} label="위험" />
        </div>
      </section>
    </Layout>
  );
}

function Zone({ side, detections }: { side: 'left' | 'right'; detections: DetectionEvent[] }) {
  return (
    <div className="relative rounded-2xl border border-dashed border-white/[0.08] bg-gradient-to-b from-white/[0.02] to-transparent">
      <span className="absolute left-1/2 top-1.5 -translate-x-1/2 text-[9px] font-medium uppercase tracking-widest text-slate-600">
        {moduleLabel[side]}
      </span>

      {detections.map((d, i) => {
        const dist = d.distance ?? MAX_RANGE_M;
        const topPct = Math.max(6, Math.min(90, (dist / MAX_RANGE_M) * 100));
        const c = riskColor[d.risk_level];
        return (
          <div
            key={d.track_id ?? i}
            className="absolute left-1/2 flex -translate-x-1/2 flex-col items-center transition-all duration-700 ease-out"
            style={{ top: `${topPct}%` }}
          >
            <div
              className={`relative flex h-12 w-12 items-center justify-center rounded-full border-2 ${c.border} ${c.bg} backdrop-blur-sm`}
            >
              {d.risk_level === 'danger' && (
                <span className="absolute inset-0 rounded-full border-2 border-risk-danger animate-ping" />
              )}
              <ObjectIcon type={d.object_type} className={`h-6 w-6 ${c.text}`} />
            </div>
            {d.movement === 'approaching' && (
              <ArrowDownIcon className={`h-4 w-4 ${c.text}`} />
            )}
            {d.movement === 'receding' && (
              <ArrowUpIcon className="h-4 w-4 text-slate-500" />
            )}
            <span className={`tabular text-[11px] font-bold ${c.text}`}>
              {d.distance != null ? `${d.distance.toFixed(1)}m` : '거리?'}
            </span>
            <span className="text-[9px] text-slate-500">{objectTypeLabel[d.object_type]}</span>
          </div>
        );
      })}

      {detections.length === 0 && (
        <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-[10px] text-slate-600">
          객체 없음
        </span>
      )}
    </div>
  );
}

function Legend({ hex, label }: { hex: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-slate-400">
      <span
        className="h-2.5 w-2.5 rounded-full"
        style={{ backgroundColor: hex, boxShadow: `0 0 8px ${hex}` }}
      />
      {label}
    </span>
  );
}
