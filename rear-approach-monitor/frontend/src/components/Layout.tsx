import type { ReactNode } from 'react';
import { TopBar } from './TopBar';
import { BottomNav } from './BottomNav';
import { AlertManager } from './AlertManager';
import { DangerOverlay } from './DangerOverlay';

/** 공통 페이지 레이아웃: 상단 바 + 본문 + 하단 내비 + 전역 알림/위험강조. */
export function Layout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="min-h-full">
      <DangerOverlay />
      <AlertManager />
      <TopBar title={title} />
      <main className="mx-auto max-w-xl px-4 pb-24 pt-4">{children}</main>
      <BottomNav />
    </div>
  );
}
