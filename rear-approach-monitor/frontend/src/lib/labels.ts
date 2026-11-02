/** 열거값 → 한글 라벨 / 색상 / 아이콘 매핑 유틸. */

import type { Movement, ObjectType, RiskLevel } from '../types';

export const objectTypeLabel: Record<ObjectType, string> = {
  person: '사람',
  bicycle: '자전거',
  car: '자동차',
  motorcycle: '오토바이',
  bus: '버스',
  truck: '트럭',
  unknown: '미상',
};

/** 객체 종류별 이모지 아이콘 (시각화/기록용) */
export const objectTypeIcon: Record<ObjectType, string> = {
  person: '🚶',
  bicycle: '🚲',
  car: '🚗',
  motorcycle: '🏍️',
  bus: '🚌',
  truck: '🚚',
  unknown: '❔',
};

export const movementLabel: Record<Movement, string> = {
  approaching: '접근 중',
  receding: '멀어지는 중',
  stationary: '정지',
};

export const riskLabel: Record<RiskLevel, string> = {
  safe: '안전',
  warning: '주의',
  danger: '위험',
};

/** 위험도 → Tailwind 색상 클래스 모음 */
export const riskColor: Record<
  RiskLevel,
  { text: string; bg: string; border: string; ring: string; hex: string }
> = {
  safe: {
    text: 'text-risk-safe',
    bg: 'bg-risk-safe/15',
    border: 'border-risk-safe/40',
    ring: 'ring-risk-safe',
    hex: '#22c55e',
  },
  warning: {
    text: 'text-risk-warning',
    bg: 'bg-risk-warning/15',
    border: 'border-risk-warning/40',
    ring: 'ring-risk-warning',
    hex: '#eab308',
  },
  danger: {
    text: 'text-risk-danger',
    bg: 'bg-risk-danger/20',
    border: 'border-risk-danger/50',
    ring: 'ring-risk-danger',
    hex: '#ef4444',
  },
};

export const moduleLabel: Record<'left' | 'right', string> = {
  left: '좌측',
  right: '우측',
};

/** ISO 문자열 → HH:MM:SS */
export function timeStr(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString('ko-KR', { hour12: false });
}

/** 마지막 수신 이후 경과 초 */
export function secondsAgo(iso: string | null): number {
  if (!iso) return Infinity;
  return (Date.now() - new Date(iso).getTime()) / 1000;
}
