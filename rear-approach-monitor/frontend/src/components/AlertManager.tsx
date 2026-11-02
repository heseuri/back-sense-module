import { useEffect, useRef } from 'react';
import { useLiveStore } from '../store/useLiveStore';
import { useSettingsStore } from '../store/useSettingsStore';
import { playAlertSound, vibrate } from '../lib/sound';
import { moduleLabel, objectTypeLabel, riskColor } from '../lib/labels';
import { ObjectIcon, AlertTriangleIcon } from './icons';

/**
 * 전역 위험 알림 매니저.
 * - 새 alert 도착 시: 알림음(설정), 진동(설정), 브라우저 알림
 * - 화면 상단에 토스트 형태로 표시 (쿨다운은 백엔드에서 이미 적용됨)
 */
export function AlertManager() {
  const alerts = useLiveStore((s) => s.alerts);
  const dismissAlert = useLiveStore((s) => s.dismissAlert);
  const settings = useSettingsStore((s) => s.settings);
  const lastHandledId = useRef<string | null>(null);

  // 새 알림에 반응
  useEffect(() => {
    const latest = alerts[0];
    if (!latest || latest.id === lastHandledId.current) return;
    lastHandledId.current = latest.id;

    if (settings.sound_enabled) playAlertSound();
    if (settings.vibration_enabled) vibrate();

    // 브라우저 알림
    if (settings.notifications_enabled && 'Notification' in window) {
      if (Notification.permission === 'granted') {
        const e = latest.event;
        new Notification('⚠️ 후방 위험 접근', {
          body: `${moduleLabel[e.module]} · ${objectTypeLabel[e.object_type]} · ${
            e.distance != null ? e.distance.toFixed(1) + 'm' : '거리 미상'
          }`,
          tag: latest.id,
        });
      }
    }

    // 3.5초 후 자동 소멸
    const t = setTimeout(() => dismissAlert(latest.id), 3500);
    return () => clearTimeout(t);
  }, [alerts, settings, dismissAlert]);

  // 최대 3개까지만 토스트로 표시
  const visible = alerts.slice(0, 3);

  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-50 flex flex-col items-center gap-2 px-3 pt-safe">
      {visible.map((a) => {
        const e = a.event;
        const c = riskColor[e.risk_level];
        return (
          <div
            key={a.id}
            className={`pointer-events-auto mt-2 w-full max-w-md animate-slide-down rounded-2xl border ${c.border} ${c.bg} px-4 py-3 shadow-glow-danger backdrop-blur-xl`}
            role="alert"
          >
            <div className="flex items-center gap-3">
              <div
                className={`relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border ${c.border} bg-base-900/40`}
              >
                <ObjectIcon type={e.object_type} className={`h-6 w-6 ${c.text}`} />
              </div>
              <div className="min-w-0 flex-1">
                <div className={`flex items-center gap-1 text-sm font-bold ${c.text}`}>
                  <AlertTriangleIcon className="h-4 w-4" />
                  {moduleLabel[e.module]}에서 {objectTypeLabel[e.object_type]} 접근
                </div>
                <div className="tabular text-xs text-slate-300">
                  {e.distance != null ? `${e.distance.toFixed(1)}m` : '거리 미상'}
                  {e.speed != null && ` · ${Math.abs(e.speed).toFixed(1)}m/s`}
                </div>
              </div>
              <button
                onClick={() => dismissAlert(a.id)}
                className="shrink-0 rounded-lg px-2 py-1 text-xs text-slate-400 hover:text-slate-100"
              >
                닫기
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
