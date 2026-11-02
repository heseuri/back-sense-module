import { NavLink } from 'react-router-dom';
import {
  DashboardIcon,
  RadarIcon,
  CameraIcon,
  HistoryIcon,
  SettingsIcon,
} from './icons';

/** 모바일 하단 내비게이션 (명세 5절). SVG 아이콘 + 글래스 바. */
const items = [
  { to: '/', label: '대시보드', Icon: DashboardIcon },
  { to: '/radar', label: '시각화', Icon: RadarIcon },
  { to: '/camera', label: '카메라', Icon: CameraIcon },
  { to: '/history', label: '기록', Icon: HistoryIcon },
  { to: '/settings', label: '설정', Icon: SettingsIcon },
];

export function BottomNav() {
  return (
    <nav className="fixed bottom-0 inset-x-0 z-30 nav-safe-bottom border-t border-white/[0.06] bg-base-900/80 backdrop-blur-2xl">
      <ul className="mx-auto flex max-w-xl items-stretch justify-around">
        {items.map(({ to, label, Icon }) => (
          <li key={to} className="flex-1">
            <NavLink
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `group relative flex flex-col items-center gap-1 pt-2.5 pb-2 text-[10px] font-medium transition-colors ${
                  isActive ? 'text-accent' : 'text-slate-500 hover:text-slate-300'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {/* 활성 표시 상단 바 */}
                  <span
                    className={`absolute top-0 h-0.5 w-8 rounded-full bg-accent transition-opacity ${
                      isActive ? 'opacity-100 shadow-glow-accent' : 'opacity-0'
                    }`}
                  />
                  <Icon
                    className={`h-6 w-6 transition-transform ${
                      isActive ? 'scale-110' : 'group-active:scale-90'
                    }`}
                  />
                  {label}
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
