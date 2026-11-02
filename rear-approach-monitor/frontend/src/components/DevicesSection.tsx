import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useModeStore } from '../store/useModeStore';
import type { DeviceStatus } from '../types';
import { secondsAgo, timeStr } from '../lib/labels';

/** 3.7 장치 관리 섹션. */
export function DevicesSection() {
  const [devices, setDevices] = useState<DeviceStatus[]>([]);
  const mode = useModeStore((s) => s.mode);

  const load = async () => {
    try {
      setDevices(await api.getDevices());
    } catch {
      setDevices([]);
    }
  };

  useEffect(() => {
    load();
    const id = setInterval(load, 2000); // 주기적 갱신
    return () => clearInterval(id);
  }, [mode]);

  return (
    <section className="mt-4 card p-4">
      <h2 className="mb-2 text-sm font-semibold text-accent">장치 관리</h2>
      {mode === 'device' && (
        <p className="mb-2 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
          실제 장치 모드 — 하드웨어 통신이 아직 구현되지 않아 연결을 확인할 수 없습니다.
        </p>
      )}
      <div className="grid gap-2">
        {devices.map((d) => {
          // 마지막 수신 이후 일정 시간 지나면 끊김 간주 (명세 3.7, 8절)
          const stale = secondsAgo(d.last_seen) > 5;
          const connected = d.connected && !stale;
          return (
            <div key={d.device_id} className="flex items-center justify-between rounded-xl bg-base-800/50 px-3 py-2.5">
              <div className="min-w-0">
                <div className="text-sm font-medium text-slate-200">{d.name}</div>
                <div className="text-[11px] text-slate-500">
                  {d.note}
                  {d.last_seen && ` · 최종 ${timeStr(d.last_seen)}`}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-3">
                {d.battery_percent != null && (
                  <span className="tabular text-xs text-slate-400">🔋 {d.battery_percent}%</span>
                )}
                <span
                  className={`inline-flex items-center gap-1.5 text-xs font-semibold ${
                    connected ? 'text-risk-safe' : 'text-risk-danger'
                  }`}
                >
                  <span className={`h-2 w-2 rounded-full ${connected ? 'bg-risk-safe' : 'bg-risk-danger'}`} />
                  {connected ? '연결됨' : '끊김'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
