import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// PWA 지원 + React 플러그인
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: '후방 접근 감지 모니터',
        short_name: '후방감지',
        description: '후방 접근 감지 시스템 실시간 모니터링',
        theme_color: '#0a0e1a',
        background_color: '#0a0e1a',
        display: 'standalone',
        orientation: 'portrait',
        icons: [
          {
            src: 'icon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'any maskable',
          },
        ],
      },
    }),
  ],
  server: {
    port: 5173,
    host: true,
  },
});
