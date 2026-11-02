import { useEffect, useState } from 'react';
import { Layout } from '../components/Layout';
import { useSettingsStore } from '../store/useSettingsStore';
import { DevicesSection } from '../components/DevicesSection';
import type { AppSettings } from '../types';

/** 3.6 설정 + 3.7 장치 관리 (하나의 설정 화면에 통합) */
export default function Settings() {
  const { settings, fetch, save, saving, loaded } = useSettingsStore();
  const [draft, setDraft] = useState<AppSettings>(settings);
  const [notifPerm, setNotifPerm] = useState(
    'Notification' in window ? Notification.permission : 'denied',
  );

  useEffect(() => {
    fetch();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (loaded) setDraft(settings);
  }, [loaded, settings]);

  const set = <K extends keyof AppSettings>(k: K, v: AppSettings[K]) =>
    setDraft((d) => ({ ...d, [k]: v }));

  const requestNotif = async () => {
    if ('Notification' in window) {
      const p = await Notification.requestPermission();
      setNotifPerm(p);
    }
  };

  return (
    <Layout title="설정 · 장치 관리">
      {/* 위험도 임계값 */}
      <Group title="위험도 판단 기준">
        <NumberRow
          label="위험 거리 임계값"
          unit="m"
          value={draft.danger_distance_m}
          step={0.5}
          onChange={(v) => set('danger_distance_m', v)}
        />
        <NumberRow
          label="주의 거리 임계값"
          unit="m"
          value={draft.warning_distance_m}
          step={0.5}
          onChange={(v) => set('warning_distance_m', v)}
        />
        <NumberRow
          label="위험 접근 속도 임계값"
          unit="m/s"
          value={draft.danger_speed_mps}
          step={0.5}
          onChange={(v) => set('danger_speed_mps', v)}
        />
      </Group>

      {/* 알림 */}
      <Group title="알림">
        <ToggleRow
          label="알림 활성화"
          value={draft.notifications_enabled}
          onChange={(v) => set('notifications_enabled', v)}
        />
        <ToggleRow
          label="알림음"
          value={draft.sound_enabled}
          onChange={(v) => set('sound_enabled', v)}
        />
        <ToggleRow
          label="진동 알림 (ESP32)"
          value={draft.vibration_enabled}
          onChange={(v) => set('vibration_enabled', v)}
        />
        <ToggleRow
          label="LED 알림 (ESP32)"
          value={draft.led_enabled}
          onChange={(v) => set('led_enabled', v)}
        />
        <NumberRow
          label="중복 알림 쿨다운"
          unit="초"
          value={draft.alert_cooldown_sec}
          step={1}
          onChange={(v) => set('alert_cooldown_sec', v)}
        />
        {/* 브라우저 알림 권한 */}
        <div className="flex items-center justify-between py-2">
          <span className="text-sm text-slate-300">브라우저 알림 권한</span>
          {notifPerm === 'granted' ? (
            <span className="text-xs font-semibold text-risk-safe">허용됨</span>
          ) : (
            <button
              onClick={requestNotif}
              className="rounded-lg bg-accent/20 px-3 py-1.5 text-xs font-semibold text-accent"
            >
              권한 요청
            </button>
          )}
        </div>
      </Group>

      {/* 객체 종류별 감지 */}
      <Group title="객체 종류별 감지">
        <ToggleRow label="사람" value={draft.detect_person} onChange={(v) => set('detect_person', v)} />
        <ToggleRow label="자전거" value={draft.detect_bicycle} onChange={(v) => set('detect_bicycle', v)} />
        <ToggleRow label="자동차 · 버스 · 트럭" value={draft.detect_car} onChange={(v) => set('detect_car', v)} />
        <ToggleRow label="오토바이" value={draft.detect_motorcycle} onChange={(v) => set('detect_motorcycle', v)} />
      </Group>

      {/* 카메라 */}
      <Group title="화면">
        <ToggleRow
          label="카메라 영상 표시"
          value={draft.show_camera}
          onChange={(v) => set('show_camera', v)}
        />
      </Group>

      {/* 저장 */}
      <button
        onClick={() => save(draft)}
        disabled={saving}
        className="mt-4 w-full rounded-xl bg-accent py-3 text-sm font-bold text-base-900 transition-opacity disabled:opacity-50"
      >
        {saving ? '저장 중…' : '설정 저장'}
      </button>
      <p className="mt-2 text-center text-[11px] text-slate-500">
        저장된 설정은 백엔드 위험도 판단에 즉시 반영되며, 향후 Raspberry Pi 5와 연동됩니다.
      </p>

      {/* 3.7 장치 관리 */}
      <DevicesSection />
    </Layout>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-4 card p-4">
      <h2 className="mb-1 text-sm font-semibold text-accent">{title}</h2>
      <div className="divide-y divide-base-500/20">{children}</div>
    </section>
  );
}

function ToggleRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-2.5">
      <span className="text-sm text-slate-300">{label}</span>
      <button
        onClick={() => onChange(!value)}
        className={`relative h-6 w-11 rounded-full transition-colors ${
          value ? 'bg-accent' : 'bg-base-500'
        }`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
            value ? 'translate-x-5' : 'translate-x-0.5'
          }`}
        />
      </button>
    </div>
  );
}

function NumberRow({
  label,
  unit,
  value,
  step,
  onChange,
}: {
  label: string;
  unit: string;
  value: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center justify-between py-2.5">
      <span className="text-sm text-slate-300">{label}</span>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onChange(Math.max(0, +(value - step).toFixed(2)))}
          className="h-7 w-7 rounded-lg bg-base-600 text-lg leading-none text-slate-200"
        >
          −
        </button>
        <span className="tabular w-16 text-center text-sm font-semibold">
          {value}
          <span className="ml-0.5 text-xs text-slate-500">{unit}</span>
        </span>
        <button
          onClick={() => onChange(+(value + step).toFixed(2))}
          className="h-7 w-7 rounded-lg bg-base-600 text-lg leading-none text-slate-200"
        >
          +
        </button>
      </div>
    </div>
  );
}
