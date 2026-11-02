# 후방 접근 감지 시스템 모니터링 애플리케이션

Raspberry Pi + mmWave 레이더 + 카메라 + ESP32-S3 기반 후방 접근 감지 시스템의
실시간 상태 모니터링 / 제어 웹 애플리케이션입니다.

> ⚠️ 현재 **1~3단계**까지 구현되었습니다. (프로젝트 구조, 실시간 대시보드/시각화, 시뮬레이션 + WebSocket)
> 실제 하드웨어 통신(6~7단계)은 아직 연결되지 않았으며, 앱 내에서 **시뮬레이션 모드**로 명확히 표시됩니다.

---

## 1. 시스템 개요

사용자의 후방에서 접근하는 사람 / 자전거 / 자동차 / 오토바이 등을 감지하고,
접근 방향·거리·속도·위험도를 분석하여 사용자에게 위험 상황을 알립니다.

### 하드웨어 구성 (목표)

| 모듈 | 구성 | 역할 |
|------|------|------|
| A. 후방 감지 모듈 (좌/우) | Raspberry Pi Zero 2 W + OV5647 카메라 + C4001 mmWave 레이더 | 영상·레이더 데이터 수집 후 Wi-Fi 전송 |
| B. 중앙 처리 모듈 | Raspberry Pi 5 4GB + YOLO11n | 객체 인식 + 레이더 결합 + 위험도 판단 |
| C. 알림 수신 모듈 | XIAO ESP32-S3 + 진동모터 + DotStar 8×8 LED | 진동·LED 위험 알림 |

---

## 2. 기술 스택

- **프론트엔드**: React 18 + TypeScript + Vite + Tailwind CSS + PWA
- **백엔드**: Python FastAPI + WebSocket + REST API + SQLite

프론트엔드/백엔드가 분리되어 있어 향후 모바일 앱(React Native 등)으로 확장이 용이합니다.

---

## 3. 실행 방법

### 3.1 백엔드 (FastAPI)

```bash
cd backend
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- REST API 문서: http://localhost:8000/docs
- WebSocket: `ws://localhost:8000/ws/stream`

### 3.2 프론트엔드 (React)

```bash
cd frontend
npm install
npm run dev
```

- 개발 서버: http://localhost:5173
- 백엔드 주소는 **접속한 호스트 기준으로 자동 결정**됩니다 (접속 호스트의 8000 포트).
  - PC에서 `localhost`로 열면 → `http://localhost:8000`
  - 폰에서 `http://<PC-IP>:5173`으로 열면 → `http://<PC-IP>:8000`
- 커스텀/배포 환경에서는 `frontend/.env`에 `VITE_API_BASE` / `VITE_WS_BASE`를 지정하면 그 값이 우선합니다.

### 3.3 📱 스마트폰에서 접속하기

PC와 폰이 **같은 Wi-Fi**에 연결돼 있어야 합니다.

1. 백엔드를 모든 인터페이스에 바인딩해 실행:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
2. 프론트엔드 dev 서버 실행 (`npm run dev` — 이미 `host: true`로 네트워크 노출됨).
3. 폰 브라우저에서 접속:
   ```
   http://<PC의 LAN IP>:5173
   ```
   예: `http://192.168.219.102:5173`
   (PC IP는 Windows에서 `ipconfig`의 IPv4 주소로 확인)
4. 백엔드 주소는 자동으로 `http://<PC IP>:8000`을 사용하므로 별도 설정이 필요 없습니다.
5. **홈 화면에 추가**(iOS 공유 메뉴 / Android 메뉴)하면 PWA가 전체화면 앱처럼 실행됩니다.

> 방화벽에서 5173 / 8000 포트의 인바운드가 막혀 있으면 폰에서 접속되지 않습니다.
> 최초 접속 시 Windows 방화벽 허용 팝업이 뜨면 "사설 네트워크"를 허용하세요.

---

## 4. 동작 모드

| 모드 | 설명 | 데이터 출처 |
|------|------|-------------|
| **시뮬레이션 모드** (기본) | 가상의 객체 접근 시나리오를 생성 | 백엔드 `simulator.py` |
| **실제 장치 연결 모드** | Raspberry Pi 5 API 연결 (6~7단계에서 구현 예정) | 실제 센서/카메라 |

- 시뮬레이션 데이터는 모든 응답에 `source: "simulation"` 플래그를 포함하며, UI에 **"시뮬레이션"** 배지가 항상 노출됩니다.
- 실제 장치가 연결되지 않은 경우 연결된 것처럼 표시하지 않습니다.

---

## 5. 데이터 통신 구조

Raspberry Pi 5 → 백엔드로 전송된다고 가정하는 감지 이벤트 JSON:

```json
{
  "timestamp": "2026-10-27T12:00:00+09:00",
  "module": "left",
  "detected": true,
  "object_type": "bicycle",
  "confidence": 0.92,
  "distance": 2.4,
  "speed": -1.2,
  "movement": "approaching",
  "risk_level": "warning"
}
```

### 속도 부호 규칙 (가정, 실측 검증 필요)

C4001 등 mmWave 레이더의 radial velocity 부호 규칙은 센서/펌웨어 설정에 따라 달라집니다.
본 구현에서는 아래 **가정**을 사용하며, 실제 센서 연동 시(6단계) 반드시 실측으로 검증해야 합니다.

- `speed < 0` → 거리 감소(접근, approaching)
- `speed > 0` → 거리 증가(이탈, receding)
- `speed ≈ 0` → 정지(stationary)

> 백엔드는 센서가 보낸 `movement` 값을 우선 신뢰하고, 없을 때만 위 규칙으로 보정합니다.
> 임의 확정하지 않도록 `movement`가 제공되면 그대로 사용합니다.

---

## 6. 구현 단계 진행 상황

- [x] 1단계: 프로젝트 구조 생성 및 기본 UI
- [x] 2단계: 실시간 대시보드 및 후방 감지 시각화
- [x] 3단계: 시뮬레이션 데이터와 WebSocket 통신
- [x] 4단계: 위험 알림 및 감지 기록
- [x] 5단계: 설정 및 장치 관리 (설정 API + 장치 상태 API)
- [ ] 6단계: Raspberry Pi 5 실제 데이터 연동 (미구현 — 인터페이스만 설계)
- [ ] 7단계: 카메라 스트리밍 연동 (미구현 — 대기 화면 제공)
- [ ] 8단계: 모바일 최적화 및 최종 테스트

### 4단계 상세 (위험 알림 및 감지 기록)

- **track 생명주기 기반 기록**: 같은 객체를 틱마다 여러 행으로 저장하지 않고,
  track이 소멸할 때 **요약 1건**(생애 최고 위험도 + 지속 시간)만 기록한다.
  → 통계(오늘 감지 수, 위험 알림 횟수)가 부풀려지지 않는다.
- **중복 알림 쿨다운**: 동일 track에 대해 `alert_cooldown_sec`(설정값) 내 1회만 알림.
- **위험 강조 오버레이**(`DangerOverlay`): 최고 위험도=danger이고 데이터가 최신일 때만
  화면 가장자리를 붉게 펄스하고 가장 가까운 위험 객체를 요약 표시.
  오래된 데이터로는 강조하지 않는다.
- **알림음/진동/브라우저 알림**: 설정으로 각각 on/off. 설정은 백엔드에 저장되어
  위험도 판단·알림 로직에 즉시 반영된다.

> 실제 하드웨어 통신 부분(6·7단계)은 코드와 UI에서 "미구현 / 시뮬레이션"으로 명확히 표시됩니다.
