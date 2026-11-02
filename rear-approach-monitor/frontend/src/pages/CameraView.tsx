import { Layout } from '../components/Layout';
import { useModeStore } from '../store/useModeStore';
import { CameraIcon } from '../components/icons';

/**
 * 3.3 카메라 영상 모니터링
 *
 * 영상 스트리밍은 Raspberry Pi 5에서 제공하는 스트림을 사용하도록 설계되었으나,
 * 현재(7단계 미구현) 실제 스트림이 연결되지 않았다.
 * → 연결되지 않은 경우 "연결 대기 화면"을 표시한다 (명세 3.3, 8절).
 *   실제 연결된 것처럼 보이게 하지 않는다.
 */
export default function CameraView() {
  const mode = useModeStore((s) => s.mode);

  return (
    <Layout title="카메라 모니터링">
      <div className="grid gap-3">
        <CameraPanel side="좌측" mode={mode} />
        <CameraPanel side="우측" mode={mode} />
      </div>

      <p className="mt-3 text-xs text-slate-500">
        객체 인식 바운딩 박스 · 신뢰도 표시는 실제 스트림(7단계) 연동 시 제공됩니다.
      </p>
    </Layout>
  );
}

function CameraPanel({ side, mode }: { side: string; mode: string }) {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between border-b border-base-500/30 px-3 py-2">
        <span className="text-sm font-semibold">{side} 후방 카메라</span>
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-risk-warning">
          <span className="h-2 w-2 rounded-full bg-risk-warning animate-pulse" />
          스트림 미연결
        </span>
      </div>

      {/* 연결 대기 화면 */}
      <div className="relative flex aspect-video items-center justify-center bg-base-900">
        {/* 스캔라인 애니메이션 */}
        <div className="absolute inset-0 opacity-20 [background:repeating-linear-gradient(0deg,transparent,transparent_3px,rgba(34,211,238,0.3)_4px)]" />
        <div className="relative text-center">
          <CameraIcon className="mx-auto h-9 w-9 text-slate-500" />
          <p className="mt-2 text-sm text-slate-400">카메라 영상 연결 대기 중</p>
          <p className="mt-1 text-xs text-slate-600">
            {mode === 'device'
              ? 'Raspberry Pi 5 스트림 미연동 (7단계)'
              : '시뮬레이션 모드 — 샘플 영상 미제공'}
          </p>
        </div>
      </div>
    </div>
  );
}
