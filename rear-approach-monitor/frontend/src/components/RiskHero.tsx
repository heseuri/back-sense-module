import type { DetectionEvent, RiskLevel } from '../types';
import { moduleLabel, riskColor, riskLabel } from '../lib/labels';
import { AlertTriangleIcon, PersonIcon } from './icons';

/**
 * 메인 화면 최상단 — 사용자가 가장 먼저 확인해야 하는 정보:
 * 현재 위험도 + 접근 방향 (명세 5절).
 */
const GLOW: Record<RiskLevel, string> = {
  safe: 'shadow-glow-safe',
  warning: 'shadow-glow-warning',
  danger: 'shadow-glow-danger',
};
const RING_BG: Record<RiskLevel, string> = {
  safe: 'from-risk-safe/25',
  warning: 'from-risk-warning/25',
  danger: 'from-risk-danger/30',
};

export function RiskHero({
  risk,
  detections,
  stale,
}: {
  risk: RiskLevel;
  detections: DetectionEvent[];
  stale: boolean;
}) {
  const c = riskColor[risk];

  const approaching = detections.filter((d) => d.movement === 'approaching');
  const dirs = new Set(approaching.map((d) => d.module));
  const directionText =
    dirs.size === 0
      ? '접근 중인 객체 없음'
      : Array.from(dirs)
          .map((m) => moduleLabel[m])
          .join(' · ') + ' 접근';

  return (
    <section
      className={`card relative overflow-hidden ${GLOW[risk]} ${
        risk === 'danger' ? 'animate-pulse-danger' : ''
      }`}
    >
      {/* 상단 중앙 방사형 글로우 */}
      <div
        className={`pointer-events-none absolute -top-16 left-1/2 h-40 w-80 -translate-x-1/2 rounded-full bg-gradient-to-b ${RING_BG[risk]} to-transparent blur-2xl`}
      />

      <div className="relative px-5 py-7 text-center">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400">
          현재 위험도
        </p>

        {risk === 'danger' && (
          <AlertTriangleIcon className="mx-auto mt-2 h-7 w-7 text-risk-danger" />
        )}

        <div
          className={`mt-1 text-6xl font-black tracking-tight ${c.text} ${
            risk === 'danger' ? 'glow-danger' : risk === 'safe' ? '' : ''
          }`}
        >
          {riskLabel[risk]}
        </div>
        <p className="mt-2 text-sm font-semibold text-slate-200">{directionText}</p>

        {stale && (
          <p className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-base-900/70 px-3 py-1 text-xs text-amber-300">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            최신 데이터 아님 · 위험도 판단 보류
          </p>
        )}

        {/* 좌/우 방향 인디케이터 */}
        <div className="mt-5 flex items-center justify-center gap-7">
          <DirArrow active={dirs.has('left')} risk={risk} side="left" />
          <div className="relative flex h-14 w-14 items-center justify-center rounded-full border border-accent/40 bg-accent/10">
            <PersonIcon className="h-7 w-7 text-accent" />
          </div>
          <DirArrow active={dirs.has('right')} risk={risk} side="right" />
        </div>
      </div>
    </section>
  );
}

function DirArrow({
  active,
  risk,
  side,
}: {
  active: boolean;
  risk: RiskLevel;
  side: 'left' | 'right';
}) {
  const c = riskColor[risk];
  return (
    <div
      className={`flex flex-col items-center gap-1 transition-all duration-300 ${
        active ? 'opacity-100 scale-100' : 'opacity-25 scale-90'
      }`}
    >
      <svg
        viewBox="0 0 24 24"
        className={`h-8 w-8 ${active ? c.text : 'text-slate-500'} ${
          active ? 'drop-shadow-[0_0_8px_currentColor]' : ''
        }`}
        fill="none"
        stroke="currentColor"
        strokeWidth={2.2}
        strokeLinecap="round"
        strokeLinejoin="round"
        style={{ transform: side === 'right' ? 'scaleX(-1)' : undefined }}
      >
        <path d="M11 6l-6 6 6 6M5 12h14" />
      </svg>
      <span className="text-[10px] font-medium text-slate-400">{moduleLabel[side]}</span>
    </div>
  );
}
