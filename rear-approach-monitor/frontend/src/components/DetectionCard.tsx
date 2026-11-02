import type { DetectionEvent } from '../types';
import {
  moduleLabel,
  movementLabel,
  objectTypeLabel,
  riskColor,
  riskLabel,
} from '../lib/labels';
import { ObjectIcon, ArrowDownIcon, ArrowUpIcon } from './icons';

/** 개별 감지 객체 카드 (거리/속도/방향/이동상태/위험도). */
export function DetectionCard({ d }: { d: DetectionEvent }) {
  const c = riskColor[d.risk_level];
  return (
    <div className={`card card-hover animate-fade-in border ${c.border} p-3.5`}>
      <div className="flex items-center gap-3">
        {/* 아이콘 뱃지 */}
        <div
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${c.bg} ${c.border} border`}
        >
          <ObjectIcon type={d.object_type} className={`h-7 w-7 ${c.text}`} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-bold">{objectTypeLabel[d.object_type]}</span>
            <span
              className={`rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${c.bg} ${c.text}`}
            >
              {riskLabel[d.risk_level]}
            </span>
          </div>
          <div className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-400">
            <span>{moduleLabel[d.module]}</span>
            <span className="text-slate-600">·</span>
            <MovementBadge d={d} />
            <span className="text-slate-600">·</span>
            <span>신뢰도 {(d.confidence * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-center">
        <Metric
          label="거리"
          value={d.distance != null ? d.distance.toFixed(1) : '—'}
          unit="m"
        />
        <Metric
          label="상대 속도"
          value={d.speed != null ? Math.abs(d.speed).toFixed(1) : '—'}
          unit="m/s"
        />
      </div>
    </div>
  );
}

function MovementBadge({ d }: { d: DetectionEvent }) {
  const c = riskColor[d.risk_level];
  if (d.movement === 'approaching')
    return (
      <span className={`inline-flex items-center gap-0.5 font-semibold ${c.text}`}>
        <ArrowDownIcon className="h-3.5 w-3.5" />
        {movementLabel.approaching}
      </span>
    );
  if (d.movement === 'receding')
    return (
      <span className="inline-flex items-center gap-0.5 text-slate-500">
        <ArrowUpIcon className="h-3.5 w-3.5" />
        {movementLabel.receding}
      </span>
    );
  return <span className="text-slate-400">{movementLabel.stationary}</span>;
}

function Metric({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="rounded-xl border border-white/[0.04] bg-base-900/40 py-2.5">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="tabular text-2xl font-bold leading-tight">
        {value}
        <span className="ml-0.5 text-xs font-normal text-slate-400">{unit}</span>
      </div>
    </div>
  );
}
