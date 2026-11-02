import { Layout } from '../components/Layout';
import { RiskHero } from '../components/RiskHero';
import { DetectionCard } from '../components/DetectionCard';
import { useLiveStore } from '../store/useLiveStore';
import { useModeStore } from '../store/useModeStore';
import { useStale } from '../hooks/useStale';
import { api } from '../lib/api';
import { timeStr } from '../lib/labels';

const SYS_LABEL: Record<string, { text: string; cls: string }> = {
  running: { text: '작동 중', cls: 'text-risk-safe' },
  degraded: { text: '일부 연결 끊김', cls: 'text-risk-warning' },
  stopped: { text: '정지됨', cls: 'text-slate-400' },
};

/** 3.1 실시간 대시보드 */
export default function Dashboard() {
  const live = useLiveStore((s) => s.live);
  const mode = useModeStore((s) => s.mode);
  const stale = useStale();

  const detections = live?.detections ?? [];
  const risk = stale ? 'safe' : live?.highest_risk ?? 'safe';
  const sys = SYS_LABEL[live?.system_status ?? 'stopped'];

  return (
    <Layout title="실시간 대시보드">
      {/* 위험도 + 접근 방향 (가장 중요한 정보) */}
      <RiskHero risk={risk} detections={detections} stale={stale} />

      {/* 시스템/연결 상태 요약 */}
      <section className="mt-3 grid grid-cols-3 gap-2">
        <StatCard label="시스템" value={sys.text} valueCls={sys.cls} />
        <StatCard
          label="감지 객체"
          value={`${live?.object_count ?? 0}`}
          valueCls="text-accent"
        />
        <StatCard
          label="마지막 수신"
          value={live ? timeStr(live.last_update) : '—'}
          small
        />
      </section>

      {/* 좌/우 모듈 연결 상태 */}
      <section className="mt-3 grid grid-cols-2 gap-2">
        <ModuleStatus label="좌측 감지 모듈" connected={!!live?.left_connected} />
        <ModuleStatus label="우측 감지 모듈" connected={!!live?.right_connected} />
      </section>

      {/* 시뮬레이션 테스트 버튼 */}
      {mode === 'simulation' && (
        <section className="mt-3">
          <div className="mb-1.5 text-[11px] font-medium text-slate-500">
            시뮬레이션 테스트
          </div>
          <div className="flex gap-2">
            <TestBtn onClick={() => api.triggerScenario('danger_left')}>
              ← 좌측 위험
            </TestBtn>
            <TestBtn onClick={() => api.triggerScenario('danger_right')}>
              우측 위험 →
            </TestBtn>
            <TestBtn onClick={() => api.triggerScenario('clear')}>초기화</TestBtn>
          </div>
        </section>
      )}

      {/* 감지된 객체 목록 */}
      <section className="mt-4">
        <h2 className="mb-2 text-sm font-semibold text-slate-300">감지된 객체</h2>
        {detections.length === 0 ? (
          <div className="card p-6 text-center text-sm text-slate-500">
            {mode === 'device'
              ? '실제 장치 미연동 — 수신 데이터 없음'
              : '현재 감지된 객체가 없습니다'}
          </div>
        ) : (
          <div className="grid gap-2">
            {detections.map((d, i) => (
              <DetectionCard key={d.track_id ?? i} d={d} />
            ))}
          </div>
        )}
      </section>
    </Layout>
  );
}

function StatCard({
  label,
  value,
  valueCls = 'text-slate-100',
  small,
}: {
  label: string;
  value: string;
  valueCls?: string;
  small?: boolean;
}) {
  return (
    <div className="card p-3 text-center">
      <div className="text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div
        className={`tabular mt-0.5 font-black leading-tight ${
          small ? 'text-sm font-bold' : 'text-2xl'
        } ${valueCls}`}
      >
        {value}
      </div>
    </div>
  );
}

function ModuleStatus({ label, connected }: { label: string; connected: boolean }) {
  return (
    <div className="card flex items-center justify-between p-3">
      <span className="text-xs text-slate-300">{label}</span>
      <span
        className={`inline-flex items-center gap-1.5 text-xs font-semibold ${
          connected ? 'text-risk-safe' : 'text-risk-danger'
        }`}
      >
        <span className="relative flex h-2 w-2">
          {connected && (
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-risk-safe opacity-60" />
          )}
          <span
            className={`relative inline-flex h-2 w-2 rounded-full ${
              connected ? 'bg-risk-safe' : 'bg-risk-danger'
            }`}
          />
        </span>
        {connected ? '연결됨' : '끊김'}
      </span>
    </div>
  );
}

function TestBtn({
  children,
  onClick,
}: {
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="card card-hover flex-1 px-2 py-2.5 text-[11px] font-semibold text-slate-200 hover:text-accent"
    >
      {children}
    </button>
  );
}
