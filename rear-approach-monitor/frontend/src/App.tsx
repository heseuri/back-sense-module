import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import RadarView from './pages/RadarView';
import CameraView from './pages/CameraView';
import History from './pages/History';
import Settings from './pages/Settings';
import { useLiveStore } from './store/useLiveStore';
import { useModeStore } from './store/useModeStore';
import { useSettingsStore } from './store/useSettingsStore';

export default function App() {
  const connect = useLiveStore((s) => s.connect);
  const disconnect = useLiveStore((s) => s.disconnect);
  const fetchMode = useModeStore((s) => s.fetchMode);
  const fetchSettings = useSettingsStore((s) => s.fetch);

  // 앱 시작 시: WebSocket 연결(자동 재연결 포함) + 초기 상태 로드
  useEffect(() => {
    connect();
    fetchMode();
    fetchSettings();
    return () => disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/radar" element={<RadarView />} />
      <Route path="/camera" element={<CameraView />} />
      <Route path="/history" element={<History />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
