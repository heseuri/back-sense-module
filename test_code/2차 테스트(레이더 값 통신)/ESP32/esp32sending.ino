
#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <math.h>

// ===================================
// 1. Wi-Fi 및 통신 설정
// ===================================
const char* WIFI_SSID = "RearDetection_AP";
const char* WIFI_PASSWORD = "12345678";

// 반드시 Pi 5 핫스팟의 실제 IP 확인
IPAddress PI5_IP(10, 42, 0, 1);

const uint16_t PI5_PORT = 5005;
const uint16_t ESP_LOCAL_PORT = 5006;

const char* MODULE_ID = "left";

// ===================================
// 2. C4001 레이더 설정
// ===================================
#define RADAR_RX 44  // D7, C4001 TX 연결
#define RADAR_TX 43  // D6, C4001 RX 연결
#define RADAR_BAUD 9600

HardwareSerial RadarSerial(1);
WiFiUDP udp;

String radarBuffer;

bool radarRunning = true;
bool latencyMode = false;

uint32_t radarSequence = 0;
unsigned long lastReconnectAttempt = 0;

// ===================================
// 3. RTT 측정 관련 변수
// ===================================
const uint32_t PING_INTERVAL_MS = 1000;
const uint32_t PING_TIMEOUT_MS = 800;

uint32_t pingSequence = 0;
uint32_t pendingSequence = 0;
uint32_t pingSentMicros = 0;
uint32_t lastPingMillis = 0;

bool pingPending = false;

uint32_t successCount = 0;
uint32_t timeoutCount = 0;

float rttTotal = 0;
float rttMin = INFINITY;
float rttMax = 0;

// ===================================
// 4. 시리얼 출력 헬퍼
// ===================================
void logMessage(const String& msg) {
  if (!latencyMode) {
    Serial.println(msg);
  }
}

// ===================================
// 5. 레이더 명령
// ===================================
void sendRadarCommand(const char* command) {
  RadarSerial.print(command);
  RadarSerial.print("\r\n");

  if (!latencyMode) {
    Serial.print("[RADAR CMD] ");
    Serial.println(command);
  }
}

void initializeRadar() {
  delay(700);

  sendRadarCommand("sensorStop");
  delay(700);

  sendRadarCommand("setRunApp 1");
  delay(1200);

  sendRadarCommand("sensorStart");
  delay(500);

  while (RadarSerial.available()) {
    RadarSerial.read();
  }

  radarBuffer = "";
  logMessage("[RADAR] Speed Mode 준비 완료");
}

// ===================================
// 6. Wi-Fi 연결
// ===================================
void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("[WIFI] 연결 중");

  uint32_t started = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - started < 15000) {
    delay(200);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[WIFI] 연결 성공: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("[WIFI] 연결 실패");
  }
}

// ===================================
// 7. 레이더 데이터 UDP 전송
// ===================================
void sendRadarData(
  bool detected,
  float distance,
  float speed,
  int energy,
  const char* movement
) {
  if (!radarRunning ||
      WiFi.status() != WL_CONNECTED) {
    return;
  }

  char json[256];

  snprintf(
    json, sizeof(json),
    "{\"module\":\"%s\","
    "\"seq\":%lu,"
    "\"timestamp_ms\":%lu,"
    "\"detected\":%s,"
    "\"distance\":%.3f,"
    "\"speed\":%.3f,"
    "\"energy\":%d,"
    "\"movement\":\"%s\"}",
    MODULE_ID,
    (unsigned long)radarSequence++,
    (unsigned long)millis(),
    detected ? "true" : "false",
    distance,
    speed,
    energy,
    movement
  );

  if (udp.beginPacket(PI5_IP, PI5_PORT)) {
    udp.write(
      (const uint8_t*)json,
      strlen(json)
    );
    udp.endPacket();
  }

  if (!latencyMode) {
    Serial.print("[UDP SEND] ");
    Serial.println(json);
  }
}

// ===================================
// 8. C4001 데이터 분석
// ===================================
void parseRadarData(String line) {
  if (!radarRunning) return;

  line.trim();

  if (!line.startsWith("$DFDMD,")) {
    return;
  }

  String fields[9];
  int fieldCount = 0;
  int start = 0;

  while (fieldCount < 9) {
    int comma = line.indexOf(',', start);

    if (comma < 0) {
      fields[fieldCount++] =
        line.substring(start);
      break;
    }

    fields[fieldCount++] =
      line.substring(start, comma);

    start = comma + 1;
  }

  if (fieldCount < 2) return;

  fields[1].trim();

  if (fields[1] == "0") {
    if (!latencyMode) {
      Serial.println("[RADAR] 감지 대상 없음");
    }

    sendRadarData(
      false, 0, 0, 0, "none"
    );
    return;
  }

  if (fields[1] != "1" || fieldCount < 6) {
    return;
  }

  fields[3].trim();
  fields[4].trim();
  fields[5].trim();

  if (fields[3].isEmpty() ||
      fields[4].isEmpty() ||
      fields[5].isEmpty()) {
    return;
  }

  float distance = fields[3].toFloat();
  float speed = fields[4].toFloat();
  int energy = fields[5].toInt();

  const char* movement;

  // 이전 실험 기준. 실제 움직임으로 재검증 필요
  if (speed < -0.05f) {
    movement = "approaching";
  } else if (speed > 0.05f) {
    movement = "receding";
  } else {
    movement = "stationary";
  }

  if (!latencyMode) {
    Serial.printf(
      "[RADAR] 거리: %.3fm | "
      "속도: %.3fm/s | "
      "에너지: %d | %s\n",
      distance,
      speed,
      energy,
      movement
    );
  }

  sendRadarData(
    true, distance, speed, energy, movement
  );
}

// ===================================
// 9. 레이더 UART 수신
// ===================================
void readRadar() {
  while (RadarSerial.available()) {
    char c = (char)RadarSerial.read();

    if (c == '\n') {
      parseRadarData(radarBuffer);
      radarBuffer = "";
    } else if (c != '\r') {
      radarBuffer += c;

      if (radarBuffer.length() > 200) {
        radarBuffer = "";
      }
    }
  }
}

// ===================================
// 10. RTT 통계 초기화
// ===================================
void resetLatencyStats() {
  pingPending = false;
  successCount = 0;
  timeoutCount = 0;

  rttTotal = 0;
  rttMin = INFINITY;
  rttMax = 0;

  // 모드 시작 시 곧바로 첫 PING 전송
  lastPingMillis = millis() - PING_INTERVAL_MS;
}

// ===================================
// 11. PING 전송
// ===================================
void sendPing() {
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  uint32_t seq = ++pingSequence;

  char message[32];
  snprintf(
    message, sizeof(message),
    "PING:%lu",
    (unsigned long)seq
  );

  if (!udp.beginPacket(PI5_IP, PI5_PORT)) {
    return;
  }

  udp.write(
    (const uint8_t*)message,
    strlen(message)
  );

  // 패킷 전송 호출 시점 기준 RTT
  uint32_t sentAt = micros();

  if (udp.endPacket()) {
    pendingSequence = seq;
    pingSentMicros = sentAt;
    pingPending = true;
  }
}

// ===================================
// 12. Pi 5에서 온 PONG 수신
// ===================================
void receiveUdp() {
  int packetSize;

  while ((packetSize = udp.parsePacket()) > 0) {
    char message[64];

    int bytesRead = udp.read(
      message,
      min(packetSize, (int)sizeof(message) - 1)
    );

    if (bytesRead <= 0) continue;

    message[bytesRead] = '\0';

    if (!latencyMode || !pingPending) {
      continue;
    }

    // 다른 송신자의 응답은 무시
    if (udp.remoteIP() != PI5_IP ||
        udp.remotePort() != PI5_PORT) {
      continue;
    }

    unsigned long receivedSeq = 0;

    if (sscanf(
          message,
          "PONG:%lu",
          &receivedSeq
        ) != 1) {
      continue;
    }

    if (receivedSeq != pendingSequence) {
      continue;
    }

    uint32_t elapsedMicros =
      micros() - pingSentMicros;

    float rtt =
      elapsedMicros / 1000.0f;

    pingPending = false;

    successCount++;
    rttTotal += rtt;

    if (rtt < rttMin) rttMin = rtt;
    if (rtt > rttMax) rttMax = rtt;

    float avg = rttTotal / successCount;

    Serial.printf(
      "[RTT] %.2f ms | 평균: %.2f ms"
      " | 최소: %.2f | 최대: %.2f"
      " | 성공: %lu | 타임아웃: %lu\n",
      rtt,
      avg,
      rttMin,
      rttMax,
      (unsigned long)successCount,
      (unsigned long)timeoutCount
    );
  }
}

// ===================================
// 13. RTT 측정 관리
// ===================================
void handleLatency() {
  if (!latencyMode) return;

  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  receiveUdp();

  if (pingPending) {
    uint32_t elapsedMs =
      (micros() - pingSentMicros) / 1000;

    if (elapsedMs >= PING_TIMEOUT_MS) {
      pingPending = false;
      timeoutCount++;

      Serial.printf(
        "[RTT] 응답 없음 (800ms 초과)"
        " | 타임아웃: %lu\n",
        (unsigned long)timeoutCount
      );
    }
  }

  if (!pingPending &&
      millis() - lastPingMillis >= PING_INTERVAL_MS) {

    lastPingMillis = millis();
    sendPing();
  }
}

// ===================================
// 14. 시리얼 명령어
// ===================================
void handleSerialCommands() {
  while (Serial.available()) {
    char command = Serial.read();

    if (command == '\r' ||
        command == '\n') {
      continue;
    }

    switch (command) {

      case 's':
      case 'S':
        if (radarRunning) {
          radarRunning = false;
          sendRadarCommand("sensorStop");
          radarBuffer = "";

          Serial.println("[SYSTEM] 레이더 중지");
        } else {
          Serial.println("[SYSTEM] 이미 중지 상태");
        }
        break;

      case 'r':
      case 'R':
        if (!radarRunning) {
          sendRadarCommand("sensorStart");

          radarBuffer = "";
          radarRunning = true;

          Serial.println("[SYSTEM] 레이더 재개");
        } else {
          Serial.println("[SYSTEM] 이미 실행 중");
        }
        break;

      case 't':
      case 'T':
        latencyMode = !latencyMode;

        if (latencyMode) {
          resetLatencyStats();

          Serial.println();
          Serial.println(
            "========== RTT 측정 시작 =========="
          );
          Serial.println(
            "레이더 측정 및 전송은 계속됩니다."
          );
          Serial.println(
            "종료하려면 t를 다시 입력하세요."
          );
        } else {
          pingPending = false;

          Serial.println();
          Serial.println(
            "========== RTT 측정 종료 =========="
          );
          Serial.println(
            "기존 레이더 출력 모드로 복귀"
          );
        }
        break;

      case 'p':
      case 'P':
        Serial.println();
        Serial.println("===== 현재 상태 =====");

        Serial.print("레이더: ");
        Serial.println(
          radarRunning ? "실행 중" : "중지"
        );

        Serial.print("Wi-Fi: ");
        Serial.println(
          WiFi.status() == WL_CONNECTED
          ? "연결됨" : "연결 안 됨"
        );

        Serial.print("RTT 모드: ");
        Serial.println(
          latencyMode ? "ON" : "OFF"
        );

        if (WiFi.status() == WL_CONNECTED) {
          Serial.print("ESP32 IP: ");
          Serial.println(WiFi.localIP());
        }

        Serial.printf(
          "RTT 성공: %lu / 타임아웃: %lu\n",
          (unsigned long)successCount,
          (unsigned long)timeoutCount
        );

        Serial.println("====================");
        break;

      case 'h':
      case 'H':
        Serial.println();
        Serial.println("===== 명령어 =====");
        Serial.println("s : 레이더 중지");
        Serial.println("r : 레이더 재개");
        Serial.println("t : RTT 모드 ON/OFF");
        Serial.println("p : 상태 확인");
        Serial.println("h : 도움말");
        Serial.println("==================");
        break;

      default:
        Serial.print("[UNKNOWN] ");
        Serial.println(command);
        break;
    }
  }
}

// ===================================
// 15. 초기 설정
// ===================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println(
    "=== ESP32-S3 C4001 Wi-Fi + RTT ==="
  );

  RadarSerial.begin(
    RADAR_BAUD,
    SERIAL_8N1,
    RADAR_RX,
    RADAR_TX
  );

  initializeRadar();
  connectWiFi();

  // UDP 수신 포트 개방
  if (!udp.begin(ESP_LOCAL_PORT)) {
    Serial.println("[UDP] 포트 열기 실패");
  }

  Serial.println();
  Serial.println(
    "s:중지 r:재개 t:지연측정 p:상태 h:도움말"
  );
}

// ===================================
// 16. 메인 루프
// ===================================
void loop() {
  handleSerialCommands();

  if (radarRunning) {
    readRadar();
  } else {
    while (RadarSerial.available()) {
      RadarSerial.read();
    }
    radarBuffer = "";
  }

  handleLatency();

  if (WiFi.status() != WL_CONNECTED &&
      millis() - lastReconnectAttempt >= 5000) {

    lastReconnectAttempt = millis();

    if (!latencyMode) {
      Serial.println("[WIFI] 재연결 시도");
    }

    WiFi.reconnect();
  }

  delay(1);
}
