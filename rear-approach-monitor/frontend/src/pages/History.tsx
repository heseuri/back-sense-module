import { useEffect, useState } from 'react';
import { Layout } from '../components/Layout';
import { api } from '../lib/api';
import type { DetectionRecord, Stats } from '../types';
import {
  moduleLabel,
  objectTypeLabel,
  riskColor,
  riskLabel,
  timeStr,
} from '../lib/labels';
import { ObjectIcon } from '../components/icons';

/** 3.5 감지 기록 및 통계 */
export default function History() {
  const [records, setRecords] = useState<DetectionRecord[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);

  // 필터
  const today = new Date().toISOString().slice(0, 10);
  const [date, setDate] = useState(today);
  const [objType, setObjType] = useState('');
  const [risk, setRisk] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const [recs, st] = await Promise.all([
        api.getDetections({
          date: date || undefined,
          object_type: objType || undefined,
          risk_level: risk || undefined,
          limit: 300,
        }),
        api.getStats(),
      ]);
      setRecords(recs);
      setStats(st);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, objType, risk]);

  return (
    <Layout title="감지 기록 · 통계">
      {/* 통계 요약 */}
      {stats && (
        <section className="grid grid-cols-2 gap-2">
          <StatBox label="오늘 감지" value={stats.today_detections} accent />
          <StatBox label="위험 알림" value={stats.today_danger_alerts} danger />
          <StatBox label="좌측 감지" value={stats.left_count} />
          <StatBox label="우측 감지" value={stats.right_count} />
        </section>
      )}

      {/* 객체 종류별 비율 */}
      {stats && Object.keys(stats.by_object_type).length > 0 && (
        <section className="mt-3 card p-3">
          <div className="mb-2 text-xs font-semibold text-slate-300">객체 종류별 비율</div>
          <TypeBars data={stats.by_object_type} />
        </section>
      )}

      {/* 시간대별 */}
      {stats && (
        <section className="mt-3 card p-3">
          <div className="mb-2 text-xs font-semibold text-slate-300">시간대별 감지</div>
          <HourChart byHour={stats.by_hour} />
        </section>
      )}

      {/* 필터 */}
      <section className="mt-3 flex flex-wrap gap-2">
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="rounded-lg border border-base-500/40 bg-base-700/60 px-2 py-1.5 text-xs text-slate-200"
        />
        <Select value={objType} onChange={setObjType} label="종류 전체">
          <option value="person">사람</option>
          <option value="bicycle">자전거</option>
          <option value="car">자동차</option>
          <option value="motorcycle">오토바이</option>
        </Select>
        <Select value={risk} onChange={setRisk} label="위험도 전체">
          <option value="warning">주의</option>
          <option value="danger">위험</option>
        </Select>
      </section>

      {/* 기록 목록 */}
      <section className="mt-3">
        {loading ? (
          <div className="card p-6 text-center text-sm text-slate-500">불러오는 중…</div>
        ) : records.length === 0 ? (
          <div className="card p-6 text-center text-sm text-slate-500">
            해당 조건의 감지 기록이 없습니다
          </div>
        ) : (
          <div className="grid gap-2">
            {records.map((r) => {
              const c = riskColor[r.risk_level];
              return (
                <div key={r.id} className={`card flex items-center gap-3 border ${c.border} p-2.5`}>
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${c.bg}`}>
                    <ObjectIcon type={r.object_type} className={`h-5 w-5 ${c.text}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 text-sm">
                      <span className="font-semibold">{objectTypeLabel[r.object_type]}</span>
                      <span className={`rounded px-1.5 py-0.5 text-[10px] ${c.bg} ${c.text}`}>
                        {riskLabel[r.risk_level]}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 tabular">
                      {timeStr(r.timestamp)} · {moduleLabel[r.module]} ·{' '}
                      {r.distance != null ? `${r.distance.toFixed(1)}m` : '거리?'} ·{' '}
                      {r.speed != null ? `${Math.abs(r.speed).toFixed(1)}m/s` : ''}
                      {r.duration_ms != null && ` · ${(r.duration_ms / 1000).toFixed(1)}s`}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </Layout>
  );
}

function StatBox({
  label,
  value,
  accent,
  danger,
}: {
  label: string;
  value: number;
  accent?: boolean;
  danger?: boolean;
}) {
  const cls = danger ? 'text-risk-danger' : accent ? 'text-accent' : 'text-slate-100';
  return (
    <div className="card p-3 text-center">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`tabular text-2xl font-black ${cls}`}>{value}</div>
    </div>
  );
}

function Select({
  value,
  onChange,
  label,
  children,
}: {
  value: string;
  onChange: (v: string) => void;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-base-500/40 bg-base-700/60 px-2 py-1.5 text-xs text-slate-200"
    >
      <option value="">{label}</option>
      {children}
    </select>
  );
}

function TypeBars({ data }: { data: Record<string, number> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  return (
    <div className="space-y-1.5">
      {Object.entries(data).map(([type, count]) => {
        const pct = (count / total) * 100;
        return (
          <div key={type} className="flex items-center gap-2 text-xs">
            <span className="w-14 shrink-0 text-slate-400">
              {objectTypeLabel[type as keyof typeof objectTypeLabel] ?? type}
            </span>
            <div className="h-3 flex-1 overflow-hidden rounded-full bg-base-800">
              <div className="h-full rounded-full bg-accent" style={{ width: `${pct}%` }} />
            </div>
            <span className="w-12 shrink-0 text-right tabular text-slate-300">
              {pct.toFixed(0)}%
            </span>
          </div>
        );
      })}
    </div>
  );
}

function HourChart({ byHour }: { byHour: Record<string, number> }) {
  const max = Math.max(1, ...Object.values(byHour));
  return (
    <div className="flex h-24 items-end gap-0.5">
      {Array.from({ length: 24 }, (_, h) => {
        const key = String(h).padStart(2, '0');
        const v = byHour[key] ?? 0;
        return (
          <div key={h} className="flex flex-1 flex-col items-center justify-end">
            <div
              className="w-full rounded-t bg-accent/70"
              style={{ height: `${(v / max) * 100}%`, minHeight: v > 0 ? 3 : 0 }}
              title={`${key}시: ${v}건`}
            />
            {h % 6 === 0 && <span className="mt-0.5 text-[8px] text-slate-600">{key}</span>}
          </div>
        );
      })}
    </div>
  );
}
