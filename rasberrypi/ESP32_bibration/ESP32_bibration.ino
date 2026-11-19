
#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>

// =======================================
// 핀 설정
// =======================================

#define LEFT_MOTOR  D1
#define RIGHT_MOTOR D2

#define SERVICE_UUID \
  "4fafc201-1fb5-459e-8fcc-c5c9c331914b"

#define CHAR_UUID \
  "beb5483e-36e1-4688-b7f5-ea07361b26a8"

const uint32_t COMMAND_TIMEOUT = 1200;

// =======================================
// BLE 수신 상태
// =======================================

volatile uint8_t receivedLeft = 0;
volatile uint8_t receivedRight = 0;

volatile uint32_t lastReceived = 0;
volatile bool bleConnected = false;

uint8_t activeLeft = 0;
uint8_t activeRight = 0;

uint32_t leftPatternStart = 0;
uint32_t rightPatternStart = 0;

BLEServer* bleServer = nullptr;


// =======================================
// 모터 정지
// =======================================

void stopMotors() {
  digitalWrite(LEFT_MOTOR, LOW);
  digitalWrite(RIGHT_MOTOR, LOW);
}


// =======================================
// BLE 명령 수신
// =======================================

class AlertCallbacks
    : public BLECharacteristicCallbacks {

  void onWrite(
      BLECharacteristic* characteristic
  ) override {

    String data = characteristic->getValue();

    if (data.length() != 2) {
      Serial.println("[BLE] Invalid packet");
      return;
    }

    uint8_t left = (uint8_t)data[0];
    uint8_t right = (uint8_t)data[1];

    if (left > 3 || right > 3) {
      Serial.println("[BLE] Invalid risk");
      return;
    }

    receivedLeft = left;
    receivedRight = right;
    lastReceived = millis();

    Serial.printf(
      "[BLE RX] LEFT=%u RIGHT=%u\n",
      left, right
    );
  }
};


// =======================================
// BLE 연결 이벤트
// =======================================

class ServerCallbacks
    : public BLEServerCallbacks {

  void onConnect(BLEServer* server) override {
    bleConnected = true;
    receivedLeft = 0;
    receivedRight = 0;
    lastReceived = 0;

    Serial.println("[BLE] Connected");
  }

  void onDisconnect(BLEServer* server) override {
    bleConnected = false;
    receivedLeft = 0;
    receivedRight = 0;
    lastReceived = 0;

    Serial.println("[BLE] Disconnected");

    BLEDevice::startAdvertising();

    Serial.println("[BLE] Advertising restarted");
  }
};


// =======================================
// 위험 단계별 진동 패턴
// =======================================

bool motorPattern(
    uint8_t risk,
    uint32_t elapsed
) {
  uint32_t onTime = 0;
  uint32_t offTime = 0;

  switch (risk) {

    case 1:
      onTime = 100;
      offTime = 900;
      break;

    case 2:
      onTime = 250;
      offTime = 350;
      break;

    case 3:
      onTime = 450;
      offTime = 100;
      break;

    default:
      return false;
  }

  uint32_t period = onTime + offTime;

  return (elapsed % period) < onTime;
}


// =======================================
// 초기 설정
// =======================================

void setup() {
  Serial.begin(115200);

  pinMode(LEFT_MOTOR, OUTPUT);
  pinMode(RIGHT_MOTOR, OUTPUT);

  stopMotors();

  Serial.println("==========================");
  Serial.println(" REAR ALERT WRIST MODULE");
  Serial.println("==========================");

  // BLE 장치 시작
  BLEDevice::init("RearAlert-Wrist");

  bleServer = BLEDevice::createServer();

  bleServer->setCallbacks(
    new ServerCallbacks()
  );

  // BLE 서비스 생성
  BLEService* service =
    bleServer->createService(SERVICE_UUID);

  // 위험도 수신 특성
  BLECharacteristic* characteristic =
    service->createCharacteristic(
      CHAR_UUID,
      BLECharacteristic::PROPERTY_WRITE
    );

  characteristic->setCallbacks(
    new AlertCallbacks()
  );

  service->start();

  // BLE 광고 시작
  BLEAdvertising* advertising =
    BLEDevice::getAdvertising();

  advertising->addServiceUUID(SERVICE_UUID);
  advertising->setScanResponse(true);
  advertising->start();

  Serial.println("[SYSTEM] Wrist ready");
  Serial.println("[BLE] Advertising started");
  Serial.println("[BLE] Waiting for Raspberry Pi");
}


// =======================================
// 메인 루프
// =======================================

void loop() {
  uint32_t now = millis();

  bool timedOut =
      lastReceived == 0 ||
      (now - lastReceived > COMMAND_TIMEOUT);

  // BLE 연결 또는 수신이 끊겼다면 정지
  if (!bleConnected || timedOut) {
    activeLeft = 0;
    activeRight = 0;

    stopMotors();

    delay(5);
    return;
  }

  uint8_t nextLeft = receivedLeft;
  uint8_t nextRight = receivedRight;

  // 왼쪽 위험 단계 변경
  if (nextLeft != activeLeft) {
    activeLeft = nextLeft;
    leftPatternStart = now;

    Serial.printf(
      "[LEFT] Risk=%u\n",
      activeLeft
    );
  }

  // 오른쪽 위험 단계 변경
  if (nextRight != activeRight) {
    activeRight = nextRight;
    rightPatternStart = now;

    Serial.printf(
      "[RIGHT] Risk=%u\n",
      activeRight
    );
  }

  // 진동 패턴 계산
  bool leftOn = motorPattern(
    activeLeft,
    now - leftPatternStart
  );

  bool rightOn = motorPattern(
    activeRight,
    now - rightPatternStart
  );

  // MOSFET을 통한 모터 제어
  digitalWrite(
    LEFT_MOTOR,
    leftOn ? HIGH : LOW
  );

  digitalWrite(
    RIGHT_MOTOR,
    rightOn ? HIGH : LOW
  );

  delay(5);
}
