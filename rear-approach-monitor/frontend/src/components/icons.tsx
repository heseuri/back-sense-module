/**
 * 통일된 SVG 아이콘 세트.
 * 이모지는 플랫폼별 렌더링 차이가 커서, 안전 모니터링 UI 일관성을 위해
 * 라인 스타일 SVG로 대체한다. 모두 currentColor를 따르므로 색상은 부모에서 제어.
 */
import type { ObjectType } from '../types';

type P = { className?: string };
const base = (p: P) => ({
  className: p.className,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
});

export const PersonIcon = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="6" r="3" />
    <path d="M6 21v-1a6 6 0 0 1 12 0v1" />
  </svg>
);

export const BicycleIcon = (p: P) => (
  <svg {...base(p)}>
    <circle cx="6" cy="17" r="3.2" />
    <circle cx="18" cy="17" r="3.2" />
    <path d="M6 17l4-7h5m-2 0l3 7M10 10l-1.5-3H6.5" />
  </svg>
);

export const CarIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 13l1.8-4.5A2 2 0 0 1 6.7 7h10.6a2 2 0 0 1 1.9 1.5L21 13v4a1 1 0 0 1-1 1h-1.5a1 1 0 0 1-1-1v-1H6.5v1a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z" />
    <path d="M3 13h18" />
    <circle cx="7.5" cy="16" r="0.6" fill="currentColor" />
    <circle cx="16.5" cy="16" r="0.6" fill="currentColor" />
  </svg>
);

export const MotorcycleIcon = (p: P) => (
  <svg {...base(p)}>
    <circle cx="5" cy="16" r="3" />
    <circle cx="19" cy="16" r="3" />
    <path d="M5 16l4-5h4l2 2h3m-9-2l-1-2H6" />
  </svg>
);

export const TruckIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M2 7h11v9H2zM13 10h4l3 3v3h-7z" />
    <circle cx="6" cy="18" r="1.6" />
    <circle cx="17" cy="18" r="1.6" />
  </svg>
);

export const QuestionIcon = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9.5 9a2.5 2.5 0 1 1 3.4 2.3c-.8.3-1.4 1-1.4 1.9v.3" />
    <circle cx="11.9" cy="16.5" r="0.7" fill="currentColor" />
  </svg>
);

/** 객체 종류 → 아이콘 컴포넌트 */
export function ObjectIcon({
  type,
  className,
}: {
  type: ObjectType;
  className?: string;
}) {
  switch (type) {
    case 'person':
      return <PersonIcon className={className} />;
    case 'bicycle':
      return <BicycleIcon className={className} />;
    case 'car':
    case 'bus':
    case 'truck':
      return type === 'truck' || type === 'bus' ? (
        <TruckIcon className={className} />
      ) : (
        <CarIcon className={className} />
      );
    case 'motorcycle':
      return <MotorcycleIcon className={className} />;
    default:
      return <QuestionIcon className={className} />;
  }
}

// --- UI 아이콘 -------------------------------------------------------------
export const DashboardIcon = (p: P) => (
  <svg {...base(p)}>
    <rect x="3" y="3" width="7" height="9" rx="1.5" />
    <rect x="14" y="3" width="7" height="5" rx="1.5" />
    <rect x="14" y="12" width="7" height="9" rx="1.5" />
    <rect x="3" y="16" width="7" height="5" rx="1.5" />
  </svg>
);

export const RadarIcon = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="5" />
    <path d="M12 12l6-3" />
    <circle cx="12" cy="12" r="1" fill="currentColor" />
  </svg>
);

export const CameraIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 8a2 2 0 0 1 2-2h2l1.2-1.6a1 1 0 0 1 .8-.4h6a1 1 0 0 1 .8.4L17 6h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    <circle cx="12" cy="12.5" r="3.2" />
  </svg>
);

export const HistoryIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
    <path d="M3 4v4h4" />
    <path d="M12 8v4l3 2" />
  </svg>
);

export const SettingsIcon = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-2.82 1.17V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 7.3 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 3 15a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 7.3a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 3h.09A1.65 1.65 0 0 0 11 1.6V1a2 2 0 0 1 4 0v.09A1.65 1.65 0 0 0 16.7 3c.46.19.99.1 1.36-.27l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 21 9v.09" />
  </svg>
);

export const AlertTriangleIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
    <path d="M12 9v4" />
    <circle cx="12" cy="17" r="0.6" fill="currentColor" />
  </svg>
);

export const ArrowDownIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 5v14M6 13l6 6 6-6" />
  </svg>
);

export const ArrowUpIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 19V5M6 11l6-6 6 6" />
  </svg>
);
