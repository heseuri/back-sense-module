import type { CapacitorConfig } from '@capacitor/cli';

/**
 * Capacitor 설정.
 *
 * webDir: Vite 빌드 산출물 경로.
 * server.cleartext + androidScheme=http:
 *   LAN의 백엔드가 https가 아닌 http(평문)이므로, Android에서 평문 통신을 허용해야
 *   WebView가 http://<PC-IP>:8000 에 접속할 수 있다.
 *   (운영 배포 시에는 https 백엔드를 쓰고 이 옵션을 제거할 것.)
 */
const config: CapacitorConfig = {
  appId: 'com.rearmonitor.app',
  appName: '후방 감지 모니터',
  webDir: 'dist',
  android: {
    // 백엔드가 http라서 평문 트래픽 허용이 필요하다.
    allowMixedContent: true,
  },
  server: {
    androidScheme: 'http',
    cleartext: true,
  },
};

export default config;
