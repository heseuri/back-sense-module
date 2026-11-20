
import argparse
import json
import math
import socket
import threading
import time
import urllib.request
from collections import deque

import cv2
import numpy as np
from ultralytics import YOLO


# ======================================
# 1. 실행 설정
# ======================================

parser = argparse.ArgumentParser()

parser.add_argument(
    "--classes",
    nargs="+",
    type=int,
    default=[0, 1, 2, 3, 5, 7]
)

parser.add_argument(
    "--model",
    default="yolo26n.pt"
)

parser.add_argument(
    "--conf",
    type=float,
    default=0.40
)

args = parser.parse_args()

ESP32_IP = "192.168.50.2"
CAMERA_URL = f"http://{ESP32_IP}/stream"

RADAR_PORT = 5005
MODULE_ID = "left"

YOLO_IMGSZ = 320
TARGET_FPS = 5

CAMERA_TIMEOUT = 3.0
RADAR_TIMEOUT = 1.5

# 거리·속도 유효 범위
MIN_DISTANCE = 0.2
MAX_DISTANCE = 25.0

# 접근속도 양수 = 접근
MIN_APPROACH_SPEED = 0.20

# 위험도 기준: 거리 m, TTC 초
RISK_LIMITS = [
    (3, 1.0, 1.0),
    (2, 2.0, 2.0),
    (1, 3.0, 3.5)
]

# 오경보 방지
RISK_CONFIRM_COUNT = 2
RISK_RELEASE_DELAY = 0.7

# 근거리 지속 감지 억제
CLOSE_DISTANCE = 1.0
CLOSE_HOLD_TIME = 3.0
STABLE_RANGE = 0.20
STABLE_SPEED = 0.20

# 알림 재활성화
REARM_DISTANCE = 1.8
REARM_TIME = 1.0

# 억제 중 다시 접근하면 경고
EMERGENCY_SPEED = 0.8
EMERGENCY_DROP = 0.05

CLASS_LABELS = {
    "person": "PERSON",
    "bicycle": "BICYCLE",
    "car": "CAR",
    "motorcycle": "MOTORCYCLE",
    "bus": "BUS",
    "truck": "TRUCK",
    "electric_scooter": "E-SCOOTER",
    "wheelchair": "WHEELCHAIR"
}

RISK_NAMES = [
    "SAFE", "CAUTION", "WARNING", "DANGER"
]

# BGR
RISK_COLORS = [
    (40, 170, 40),
    (0, 210, 230),
    (0, 130, 255),
    (40, 40, 230)
]


# ======================================
# 2. MJPEG 카메라 수신
# ======================================


class CameraReceiver:
    def __init__(self):
        self.lock = threading.Lock()
        self.frame = None
        self.last_frame_time = 0.0
        self.error = "Connecting"
        self.frame_count = 0

    def start(self):
        threading.Thread(
            target=self.run,
            daemon=True
        ).start()

    def run(self):
        while True:
            try:
                print("[CAMERA] Connecting:", CAMERA_URL)

                request = urllib.request.Request(
                    CAMERA_URL,
                    headers={
                        "Connection": "close",
                        "Cache-Control": "no-cache"
                    }
                )

                with urllib.request.urlopen(
                    request,
                    timeout=10
                ) as response:

                    print(
                        "[CAMERA] HTTP:",
                        response.status
                    )

                    buffer = bytearray()
                    last_decode = 0.0

                    with self.lock:
                        self.error = ""

                    while True:
                        # read1()은 가능한 데이터를 반환해
                        # 고정 바이트 수 대기를 줄임
                        chunk = response.read1(4096)

                        if not chunk:
                            raise ConnectionError(
                                "MJPEG stream closed"
                            )

                        buffer.extend(chunk)

                        # 한 번에 여러 프레임이 들어올 수 있음
                        while True:
                            start = buffer.find(b"\xff\xd8")

                            if start < 0:
                                if len(buffer) > 65536:
                                    buffer.clear()
                                break

                            end = buffer.find(
                                b"\xff\xd9",
                                start + 2
                            )

                            if end < 0:
                                if start > 0:
                                    del buffer[:start]
                                break

                            jpeg = bytes(
                                buffer[start:end + 2]
                            )

                            del buffer[:end + 2]

                            now = time.monotonic()

                            # 수신은 계속하되 디코딩은
                            # 초당 최대 5장만 수행
                            if now - last_decode < 0.2:
                                continue

                            frame = cv2.imdecode(
                                np.frombuffer(
                                    jpeg,
                                    dtype=np.uint8
                                ),
                                cv2.IMREAD_COLOR
                            )

                            if frame is None:
                                continue

                            last_decode = now

                            with self.lock:
                                self.frame = frame
                                self.last_frame_time = now
                                self.frame_count += 1

                            if self.frame_count % 25 == 0:
                                print(
                                    "[CAMERA] Frames:",
                                    self.frame_count
                                )

                        if len(buffer) > 1_000_000:
                            print(
                                "[CAMERA] Buffer reset"
                            )
                            buffer.clear()

            except Exception as e:
                print("[CAMERA ERROR]", repr(e))

                with self.lock:
                    self.error = str(e)
                    self.frame = None

                time.sleep(2)

    def snapshot(self):
        with self.lock:
            online = (
                self.frame is not None
                and time.monotonic()
                - self.last_frame_time < CAMERA_TIMEOUT
            )

            return (
                self.frame.copy()
                if online else None,
                online,
                self.error
            )

# ======================================
# 3. 레이더 상태 및 위험도 관리
# ======================================

class RadarTracker:
    def __init__(self):
        self.lock = threading.Lock()

        self.last_packet_time = 0
        self.last_seq = None

        self.valid = False
        self.detected = False

        self.history = deque(maxlen=100)

        self.distance = None
        self.raw_speed = None
        self.approach_speed = 0.0
        self.ttc = None

        self.risk = 0
        self.pending_risk = 0
        self.pending_count = 0
        self.last_risk_time = 0

        self.suppressed = False
        self.close_start = None
        self.rearm_start = None
        self.emergency_count = 0

        self.previous_distance = None
        self.previous_time = None

    def reset_target(self):
        self.history.clear()
        self.distance = None
        self.raw_speed = None
        self.approach_speed = 0.0
        self.ttc = None

        self.risk = 0
        self.pending_risk = 0
        self.pending_count = 0

        self.close_start = None
        self.rearm_start = None
        self.suppressed = False
        self.emergency_count = 0

        self.previous_distance = None
        self.previous_time = None

    def calculate_risk(self):
        if self.distance is None:
            return 0

        if self.approach_speed < MIN_APPROACH_SPEED:
            return 0

        for level, d_limit, t_limit in RISK_LIMITS:
            if self.distance <= d_limit:
                return level

            if self.ttc is not None:
                if self.ttc <= t_limit:
                    return level

        return 0

    def update_risk(self, candidate, now):
        if candidate > self.risk:
            if candidate == self.pending_risk:
                self.pending_count += 1
            else:
                self.pending_risk = candidate
                self.pending_count = 1

            if self.pending_count >= RISK_CONFIRM_COUNT:
                self.risk = candidate
                self.last_risk_time = now
                self.pending_count = 0

        elif candidate == self.risk:
            self.pending_count = 0

            if candidate > 0:
                self.last_risk_time = now

        else:
            self.pending_count = 0

            if now - self.last_risk_time >= RISK_RELEASE_DELAY:
                self.risk = candidate

    def update_suppression(
        self,
        now,
        rapid_approach
    ):
        d = self.distance

        if d is None:
            return

        # 알림 억제 중
        if self.suppressed:

            if rapid_approach:
                self.emergency_count += 1
            else:
                self.emergency_count = 0

            # 2회 연속 급접근 확인 시 즉시 재경고
            if self.emergency_count >= 2:
                self.suppressed = False
                self.close_start = None
                self.rearm_start = None
                self.emergency_count = 0

                self.risk = max(
                    2, self.calculate_risk()
                )
                self.last_risk_time = now

                print("[ALERT] RAPID APPROACH")
                return

            # 충분히 멀어지면 재활성화
            if d >= REARM_DISTANCE:

                if self.rearm_start is None:
                    self.rearm_start = now

                elif now - self.rearm_start >= REARM_TIME:
                    self.suppressed = False
                    self.close_start = None
                    self.rearm_start = None
                    self.emergency_count = 0
                    self.risk = 0

                    print("[ALERT] REARMED")

            else:
                self.rearm_start = None

            return

        # 근거리에서 정체 상태인지 확인
        if (
            d <= CLOSE_DISTANCE
            and abs(self.approach_speed) <= STABLE_SPEED
        ):

            if self.close_start is None:
                self.close_start = now

            elapsed = now - self.close_start

            if elapsed >= CLOSE_HOLD_TIME:
                samples = [
                    v for t, v in self.history
                    if t >= self.close_start
                ]

                if (
                    len(samples) >= 5
                    and max(samples) - min(samples)
                    <= STABLE_RANGE
                ):
                    self.suppressed = True
                    self.risk = 0
                    self.pending_count = 0

                    print("[ALERT] CLOSE HOLD MUTED")
                else:
                    self.close_start = now

        else:
            self.close_start = None

    def update(self, packet):
        now = time.monotonic()

        with self.lock:
            seq = packet.get("seq")

            # 동일 패킷 중복 처리 방지
            if seq is not None and seq == self.last_seq:
                return

            self.last_seq = seq
            self.last_packet_time = now

            self.valid = packet.get("valid") is True
            self.detected = packet.get("detected") is True

            if not self.valid or not self.detected:
                self.reset_target()
                return

            try:
                raw_d = float(packet["distance_m"])
                raw_s = float(packet["speed_mps"])
            except (KeyError, TypeError, ValueError):
                self.valid = False
                self.reset_target()
                return

            if (
                not math.isfinite(raw_d)
                or not math.isfinite(raw_s)
                or not MIN_DISTANCE <= raw_d <= MAX_DISTANCE
            ):
                self.valid = False
                self.reset_target()
                return

            self.raw_speed = raw_s

            # 순간 접근속도 계산
            rapid = False

            if self.previous_distance is not None:
                dt = now - self.previous_time
                drop = self.previous_distance - raw_d

                if dt > 0:
                    instant_speed = drop / dt

                    rapid = (
                        drop >= EMERGENCY_DROP
                        and instant_speed >= EMERGENCY_SPEED
                        and instant_speed <= 20.0
                    )

            self.previous_distance = raw_d
            self.previous_time = now

            self.history.append((now, raw_d))

            # 최근 1.2초 거리값
            recent = [
                (t, d) for t, d in self.history
                if now - t <= 1.2
            ]

            # 최근 5개 샘플 중앙값
            distances = [d for _, d in recent]

            self.distance = float(
                np.median(distances[-5:])
            )

            # 연속 거리 측정으로 접근속도 계산
            if len(recent) >= 2:
                t0, d0 = recent[0]
                t1, d1 = recent[-1]

                if t1 - t0 >= 0.3:
                    speed = (d0 - d1) / (t1 - t0)

                    if abs(speed) <= 20:
                        self.approach_speed = speed
            else:
                self.approach_speed = 0.0

            if self.approach_speed > MIN_APPROACH_SPEED:
                self.ttc = (
                    self.distance / self.approach_speed
                )
            else:
                self.ttc = None

            self.update_suppression(now, rapid)

            if self.suppressed:
                self.risk = 0
                return

            candidate = self.calculate_risk()
            self.update_risk(candidate, now)

    def snapshot(self):
        with self.lock:
            age = time.monotonic() - self.last_packet_time

            online = (
                self.last_packet_time > 0
                and age <= RADAR_TIMEOUT
                and self.valid
            )

            if not online:
                return {
                    "online": False,
                    "detected": False,
                    "distance": None,
                    "speed": None,
                    "raw_speed": None,
                    "ttc": None,
                    "risk": None,
                    "suppressed": False
                }

            return {
                "online": True,
                "detected": self.detected,
                "distance": self.distance,
                "speed": self.approach_speed,
                "raw_speed": self.raw_speed,
                "ttc": self.ttc,
                "risk": self.risk,
                "suppressed": self.suppressed
            }


# ======================================
# 4. UDP 레이더 수신 스레드
# ======================================

radars = {
    "left": RadarTracker(),
    "right": RadarTracker()
}


def receive_radar():
    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    sock.bind(("0.0.0.0", RADAR_PORT))

    print("[RADAR] UDP listening:", RADAR_PORT)

    while True:
        try:
            raw, sender = sock.recvfrom(4096)
            packet = json.loads(
                raw.decode("utf-8")
            )

            module = packet.get("module", "")

            if module in radars:
                radars[module].update(packet)

        except Exception as e:
            print("[RADAR ERROR]", e)


# ======================================
# 5. YOLO 객체 인식
# ======================================

def detect_objects(model, frame):
    results = model.predict(
        frame,
        imgsz=YOLO_IMGSZ,
        conf=args.conf,
        classes=args.classes,
        verbose=False
    )[0]

    detected = []

    for box in results.boxes:
        class_id = int(box.cls[0])
        name = results.names[class_id]

        confidence = float(box.conf[0])

        x1, y1, x2, y2 = map(
            int,
            box.xyxy[0].tolist()
        )

        detected.append({
            "name": CLASS_LABELS.get(
                name, name.upper()
            ),
            "conf": confidence,
            "box": (x1, y1, x2, y2)
        })

    return detected


# ======================================
# 6. 화면 출력
# ======================================

def text(img, message, x, y,
         color=(255, 255, 255),
         scale=0.55):

    cv2.putText(
        img,
        str(message),
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        2,
        cv2.LINE_AA
    )


def number(value, unit=""):
    if value is None:
        return "N/A"

    return f"{value:.2f}{unit}"


def draw_dashboard(frame, objects, radar, camera_ok):
    image = cv2.resize(frame, (640, 480))

    canvas = np.zeros(
        (480, 1000, 3),
        dtype=np.uint8
    )

    canvas[:] = (28, 29, 34)
    canvas[:480, :640] = image

    # 원본 영상 좌표를 640x480에 맞춤
    h, w = frame.shape[:2]

    sx = 640 / w
    sy = 480 / h

    for obj in objects:
        x1, y1, x2, y2 = obj["box"]

        x1 = int(x1 * sx)
        x2 = int(x2 * sx)
        y1 = int(y1 * sy)
        y2 = int(y2 * sy)

        cv2.rectangle(
            canvas,
            (x1, y1),
            (x2, y2),
            (60, 240, 100),
            2
        )

        label = (
            f"{obj['name']} "
            f"{obj['conf'] * 100:.0f}%"
        )

        text(
            canvas,
            label,
            x1,
            max(20, y1 - 8),
            (60, 255, 100),
            0.48
        )

    px = 655

    text(
        canvas,
        "REAR DETECTION",
        px, 35,
        scale=0.75
    )

    text(
        canvas,
        f"MODULE: {MODULE_ID.upper()}",
        px, 68
    )

    text(
        canvas,
        "CAMERA: " + (
            "ONLINE" if camera_ok else "OFFLINE"
        ),
        px, 98
    )

    radar_label = (
        "NO DATA"
        if not radar["online"]
        else (
            "TARGET"
            if radar["detected"]
            else "NO TARGET"
        )
    )

    text(
        canvas,
        f"RADAR: {radar_label}",
        px, 128,
        (50, 50, 255)
        if not radar["online"]
        else (70, 210, 100)
    )

    text(
        canvas,
        "DISTANCE: "
        + number(radar["distance"], " m"),
        px, 164
    )

    text(
        canvas,
        "APPROACH: "
        + number(radar["speed"], " m/s"),
        px, 196
    )

    text(
        canvas,
        "RADAR SPEED: "
        + number(radar["raw_speed"], " m/s"),
        px, 228,
        scale=0.48
    )

    text(
        canvas,
        "TTC: "
        + number(radar["ttc"], " s"),
        px, 260
    )

    text(
        canvas,
        f"OBJECTS: {len(objects)}",
        px, 293
    )

    for i, obj in enumerate(objects[:3]):
        text(
            canvas,
            f"- {obj['name']} "
            f"{obj['conf'] * 100:.0f}%",
            px,
            318 + i * 22,
            scale=0.46
        )

    risk = radar["risk"]

    if risk is None:
        label = "SENSOR OFFLINE"
        color = (80, 80, 80)

    elif radar["suppressed"]:
        label = "CLOSE HOLD - MUTED"
        color = (110, 90, 50)

    elif risk == 0:
        label = "LEVEL 0 - SAFE"
        color = RISK_COLORS[0]

    else:
        label = (
            f"LEVEL {risk} - "
            f"{RISK_NAMES[risk]}"
        )
        color = RISK_COLORS[risk]

    cv2.rectangle(
        canvas,
        (650, 387),
        (990, 447),
        color,
        -1
    )

    text(
        canvas,
        label,
        661, 424,
        scale=0.66
    )

    text(
        canvas,
        "Q: EXIT",
        660, 471,
        (170, 170, 170),
        0.43
    )

    return canvas


# ======================================
# 7. 메인
# ======================================

def main():
    print("================================")
    print("  REAR DETECTION MONITOR")
    print("================================")

    print("[YOLO] Loading", args.model)
    model = YOLO(args.model)

    camera = CameraReceiver()
    camera.start()

    radar_thread = threading.Thread(
        target=receive_radar,
        daemon=True
    )
    radar_thread.start()

    print("[CAMERA]", CAMERA_URL)
    print("[RADAR] UDP:", RADAR_PORT)
    print("[YOLO] Classes:", args.classes)
    print("[SYSTEM] Press Q to exit")

    interval = 1.0 / TARGET_FPS
    last_log = 0.0

    while True:
        begin = time.monotonic()

        frame, camera_ok, error = camera.snapshot()
        radar = radars[MODULE_ID].snapshot()

        if camera_ok:
            try:
                objects = detect_objects(model, frame)
            except Exception as e:
                print("[YOLO ERROR]", e)
                objects = []
        else:
            frame = np.zeros(
                (480, 640, 3),
                dtype=np.uint8
            )
            objects = []

            text(
                frame,
                "CAMERA DISCONNECTED",
                100, 210,
                (50, 50, 255),
                0.8
            )

        dashboard = draw_dashboard(
            frame,
            objects,
            radar,
            camera_ok
        )

        cv2.imshow(
            "Rear Detection Monitor",
            dashboard
        )

        now = time.monotonic()

        if now - last_log >= 1:
            labels = [
                obj["name"] for obj in objects
            ]

            print(
                f"[CAMERA] {camera_ok} "
                f"[YOLO] {labels} "
                f"[RADAR] {radar['distance']}m "
                f"[SPEED] {radar['speed']}m/s "
                f"[TTC] {radar['ttc']} "
                f"[RISK] {radar['risk']} "
                f"[MUTED] {radar['suppressed']}"
            )

            if not camera_ok and error:
                print("[CAMERA DETAIL]", error)

            last_log = now

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        elapsed = time.monotonic() - begin

        if elapsed < interval:
            time.sleep(interval - elapsed)

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
