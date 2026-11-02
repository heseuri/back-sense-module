/** WebAudio로 간단한 경고음을 생성한다 (외부 음원 파일 불필요). */

let ctx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  try {
    if (!ctx) ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
    return ctx;
  } catch {
    return null;
  }
}

/** 위험 경고음 (삐-삐 2연음). */
export function playAlertSound() {
  const ac = getCtx();
  if (!ac) return;
  const now = ac.currentTime;
  [0, 0.18].forEach((offset) => {
    const osc = ac.createOscillator();
    const gain = ac.createGain();
    osc.type = 'square';
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.0001, now + offset);
    gain.gain.exponentialRampToValueAtTime(0.18, now + offset + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + offset + 0.14);
    osc.connect(gain).connect(ac.destination);
    osc.start(now + offset);
    osc.stop(now + offset + 0.15);
  });
}

/** 진동 (지원 기기에서만). */
export function vibrate(pattern: number | number[] = [120, 60, 120]) {
  if ('vibrate' in navigator) navigator.vibrate(pattern);
}
