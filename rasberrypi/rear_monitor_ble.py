
import os
import time
import json
import math
import socket
import asyncio
import argparse
import threading
import urllib.request
from collections import deque

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")

import cv2
import numpy as np
import torch
import torchvision


# =====================================================
# 1. Raspberry Pi 5 Safe NMS
# 기존 Illegal instruction 오류 우회
# =====================================================

def safe_nms(boxes, scores, iou_threshold):
    if boxes.numel() == 0:
        return torch.empty(
            (0,), dtype=torch.long, device=boxes.device
        )

    x1, y1, x2, y2 = boxes.unbind(1)

    areas = (
        (x2 - x1).clamp(min=0)
        * (y2 - y1).clamp(min=0)
    )

    order = scores.argsort(descending=True)
    keep = []

    while order.numel() > 0:
        index = int(order[0].item())
        keep.append(index)

        if order.numel() == 1:
            break

        rest = order[1:]

        xx1 = torch.maximum(x1[index], x1[rest])
        yy1 = torch.maximum(y1[index], y1[rest])
        xx2 = torch.minimum(x2[index], x2[rest])
        yy2 = torch.minimum(y2[index], y2[rest])

        intersection = (
            (xx2 - xx1).clamp(min=0)
            * (yy2 - yy1).clamp(min=0)
        )

        union = (
            areas[index] + areas[rest] - intersection
        ).clamp(min=1e-7)

        iou = intersection / union
        order = rest[iou <= iou_threshold]

    return torch.tensor(
        keep, dtype=torch.long, device=boxes.device
    )


torchvision.ops.nms = safe_nms
torchvision.ops.boxes.nms = safe_nms

from ultralytics import YOLO
from bleak import BleakClient, BleakScanner


# =====================================================
# 2. 실행 설정
# =====================================================

parser = argparse.ArgumentParser()

parser.add_argument("--model", default="yolo26n.pt")
parser.add_argument("--module", choices=["left", "right"],
                    default="left")
parser.add_argument("--camera-ip", default="192.168.50.2")
parser.add_argument("--fps", type=float, default=5.0)
parser.add_argument("--conf", type=float, default=0.40)
parser.add_argument("--no-gui", action="store_true")
parser.add_argument("--no-ble", action="store_true")

args = parser.parse_args()

CAMERA_URL = f"http://{args.camera_ip}/stream"
MODULE_ID = args.module

RADAR_PORT = 5005

YOLO_IMGSZ = 320
TARGET_FPS = max(1.0, min(args.fps, 15.0))

CLASS_IDS = [0, 1, 2, 3, 5, 7]

CAMERA_TIMEOUT = 3.0
RADAR_TIMEOUT = 1.5

MIN_DISTANCE = 0.2
MAX_DISTANCE = 25.0
MIN_APPROACH_SPEED = 0.20

# 위험 단계: (단계, 거리 m, TTC 초)
RISK_LIMITS = [
    (3, 1.0, 1.0),
    (2, 2.0, 2.0),
    (1, 3.0, 3.5)
]

RISK_CONFIRM_COUNT = 2
RISK_RELEASE_DELAY = 0.7

CLOSE_DISTANCE = 1.0
CLOSE_HOLD_TIME = 3.0
STABLE_SPEED = 0.20
STABLE_RANGE = 0.20

REARM_DISTANCE = 1.8
REARM_TIME = 1.0

EMERGENCY_SPEED = 0.8
EMERGENCY_DROP = 0.05

RISK_NAMES = [
    "SAFE", "CAUTION", "WARNING", "DANGER"
]

RISK_COLORS = [
    (40, 170, 40),
    (0, 210, 230),
    (0, 130, 255),
    (40, 40, 230)
]


# =====================================================
# 3. BLE 설정
# 손목 ESP32 코드와 UUID가 동일해야 함
# =====================================================

WRIST_NAME = "RearAlert-Wrist"

BLE_CHAR_UUID = (
    "beb5483e-36e1-4688-b7f5-ea07361b26a8"
)

BLE_INTERVAL = 0.25

ble_lock = threading.Lock()
ble_connected = False
ble_error = "Not connected"
ble_last_tx = None


def set_ble_status(connected, error=""):
    global ble_connected, ble_error

    with ble_lock:
        ble_connected = connected
        ble_error = error


def get_ble_status():
    with ble_lock:
        return ble_connected, ble_error


# =====================================================
# 4. 카메라 MJPEG 수신
# =====================================================

class CameraReceiver:
    def __init__(self):
        self.lock = threading.Lock()
        self.frame = None
        self.last_time = 0.0
        self.frame_count = 0
        self.error = "Connecting"
        self.stop_event = threading.Event()

    def start(self):
        threading.Thread(
            target=self.run, daemon=True
        ).start()

    def run(self):
        while not self.stop_event.is_set():
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
                    request, timeout=5
                ) as response:

                    print("[CAMERA] HTTP:", response.status)

                    buffer = bytearray()
                    last_decode = 0.0

                    with self.lock:
                        self.error = ""

                    while not self.stop_event.is_set():
                        chunk = response.read1(4096)

                        if not chunk:
                            raise ConnectionError(
                                "Camera stream closed"
                            )

                        buffer.extend(chunk)

                        if len(buffer) > 1_000_000:
                            buffer.clear()
                            continue

                        while True:
                            start = buffer.find(b"\xff\xd8")

                            if start < 0:
                                if len(buffer) > 65536:
                                    buffer.clear()
                                break

                            end = buffer.find(
                                b"\xff\xd9", start + 2
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

                            if now - last_decode < 0.2:
                                continue

                            frame = cv2.imdecode(
                                np.frombuffer(
                                    jpeg, dtype=np.uint8
                                ),
                                cv2.IMREAD_COLOR
                            )

                            if frame is None:
                                continue

                            last_decode = now

                            with self.lock:
                                self.frame = frame
                                self.last_time = now
                                self.frame_count += 1

            except Exception as e:
                print("[CAMERA ERROR]", repr(e))

                with self.lock:
                    self.error = str(e)
                    self.frame = None

                self.stop_event.wait(2)

    def snapshot(self):
        with self.lock:
            online = (
                self.frame is not None
                and time.monotonic() - self.last_time
                < CAMERA_TIMEOUT
            )

            frame = (
                self.frame.copy() if online else None
            )

            return (
                frame, online,
                self.error, self.frame_count
            )

    def stop(self):
        self.stop_event.set()


# =====================================================
# 5. 레이더 상태 및 위험 판단
# =====================================================

class RadarTracker:
    def __init__(self):
        self.lock = threading.Lock()

        self.last_seq = None
        self.last_packet_time = 0.0

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
        self.last_risk_time = 0.0

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

        self.suppressed = False
        self.close_start = None
        self.rearm_start = None
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

            if (
                now - self.last_risk_time
                >= RISK_RELEASE_DELAY
            ):
                self.risk = candidate

    def update_suppression(self, now, rapid):
        d = self.distance

        if d is None:
            return

        if self.suppressed:
            if rapid:
                self.emergency_count += 1
            else:
                self.emergency_count = 0

            # 억제 중 급격한 접근이 감지되면 해제
            if self.emergency_count >= 2:
                self.suppressed = False
                self.close_start = None
                self.rearm_start = None
                self.emergency_count = 0

                self.risk = max(
                    2, self.calculate_risk()
                )
                self.last_risk_time = now

                print("[ALERT] Rapid approach")
                return

            # 충분히 멀어지면 재활성화
            if d >= REARM_DISTANCE:
                if self.rearm_start is None:
                    self.rearm_start = now

                elif (
                    now - self.rearm_start
                    >= REARM_TIME
                ):
                    self.suppressed = False
                    self.close_start = None
                    self.rearm_start = None
                    self.emergency_count = 0
                    self.risk = 0

                    print("[ALERT] Rearmed")
            else:
                self.rearm_start = None

            return

        stable = (
            d <= CLOSE_DISTANCE
            and abs(self.approach_speed) <= STABLE_SPEED
        )

        if not stable:
            self.close_start = None
            return

        if self.close_start is None:
            self.close_start = now
            return

        if now - self.close_start < CLOSE_HOLD_TIME:
            return

        samples = [
            value for t, value in self.history
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
            print("[ALERT] Stationary target muted")

    def update(self, packet):
        now = time.monotonic()

        with self.lock:
            seq = packet.get("seq")

            if seq is not None and seq == self.last_seq:
                return

            # ESP32 재부팅으로 시퀀스가 초기화되면
            # 기존 거리 이력을 새 데이터와 혼합하지 않음
            if (
                isinstance(seq, int)
                and isinstance(self.last_seq, int)
                and seq < self.last_seq
            ):
                self.reset_target()

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

            recent = [
                (t, d) for t, d in self.history
                if now - t <= 1.2
            ]

            distances = [d for _, d in recent]

            self.distance = float(
                np.median(distances[-5:])
            )

            self.approach_speed = 0.0

            if len(recent) >= 2:
                t0, d0 = recent[0]
                t1, d1 = recent[-1]

                dt = t1 - t0

                if dt >= 0.3:
                    speed = (d0 - d1) / dt

                    if abs(speed) <= 20.0:
                        self.approach_speed = speed

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
            online = (
                self.last_packet_time > 0
                and time.monotonic()
                - self.last_packet_time
                <= RADAR_TIMEOUT
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


radars = {
    "left": RadarTracker(),
    "right": RadarTracker()
}


# =====================================================
# 6. 레이더 UDP 수신
# =====================================================

def receive_radar(stop_event):
    sock = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    sock.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    sock.bind(("0.0.0.0", RADAR_PORT))
    sock.settimeout(1.0)

    print("[RADAR] UDP listening:", RADAR_PORT)

    try:
        while not stop_event.is_set():
            try:
                raw, sender = sock.recvfrom(4096)

                packet = json.loads(
                    raw.decode("utf-8")
                )

                if not isinstance(packet, dict):
                    continue

                module = packet.get("module")

                if module in radars:
                    radars[module].update(packet)

            except socket.timeout:
                continue

            except Exception as e:
                print("[RADAR ERROR]", repr(e))
    finally:
        sock.close()


# =====================================================
# 7. 위험도 → 손목 BLE 데이터
# =====================================================

def get_wrist_risk():
    """
    반환값: (왼쪽 위험도, 오른쪽 위험도)
    위험도는 0~3.
    """
    left = radars["left"].snapshot()
    right = radars["right"].snapshot()

    def risk_value(state):
        value = state["risk"]

        if not state["online"] or value is None:
            return 0

        return max(0, min(3, int(value)))

    return (
        risk_value(left),
        risk_value(right)
    )


# =====================================================
# 8. BLE 전송 및 자동 재연결
# =====================================================

async def wrist_ble_worker(stop_event):
    global ble_last_tx

    while not stop_event.is_set():
        set_ble_status(False, "Searching")

        try:
            print("[BLE] Searching:", WRIST_NAME)

            device = await BleakScanner.find_device_by_filter(
                lambda device, adv: (
                    device.name == WRIST_NAME
                    or adv.local_name == WRIST_NAME
                ),
                timeout=8.0
            )

            if device is None:
                print("[BLE] Wrist not found")
                await asyncio.sleep(2)
                continue

            print("[BLE] Found:", device.name)

            async with BleakClient(
                device, timeout=10.0
            ) as client:

                print("[BLE] Connected")
                set_ble_status(True)

                previous = None
                last_log = 0.0

                while (
                    client.is_connected
                    and not stop_event.is_set()
                ):
                    left, right = get_wrist_risk()

                    payload = bytes([left, right])

                    await client.write_gatt_char(
                        BLE_CHAR_UUID,
                        payload,
                        response=True
                    )

                    ble_last_tx = time.monotonic()

                    if (
                        payload != previous
                        or ble_last_tx - last_log >= 5
                    ):
                        print(
                            f"[BLE TX] L={left} R={right}",
                            flush=True
                        )
                        previous = payload
                        last_log = ble_last_tx

                    await asyncio.sleep(BLE_INTERVAL)

                # 정상 종료 시 정지 명령
                if client.is_connected:
                    try:
                        await client.write_gatt_char(
                            BLE_CHAR_UUID,
                            bytes([0, 0]),
                            response=True
                        )
                    except Exception:
                        pass

        except Exception as e:
            print("[BLE ERROR]", repr(e))
            set_ble_status(False, str(e))

        finally:
            set_ble_status(False, "Disconnected")

        if not stop_event.is_set():
            await asyncio.sleep(2)


def run_wrist_ble(stop_event):
    asyncio.run(wrist_ble_worker(stop_event))


# =====================================================
# 9. YOLO 객체 인식
# =====================================================

def detect_objects(model, frame):
    results = model.predict(
        frame,
        imgsz=YOLO_IMGSZ,
        conf=args.conf,
        classes=CLASS_IDS,
        device="cpu",
        verbose=False
    )[0]

    objects = []

    for box in results.boxes:
        class_id = int(box.cls[0])

        x1, y1, x2, y2 = map(
            int, box.xyxy[0].tolist()
        )

        objects.append({
            "name": results.names[class_id].upper(),
            "conf": float(box.conf[0]),
            "box": (x1, y1, x2, y2)
        })

    return objects


# =====================================================
# 10. 화면 표시
# =====================================================

def fmt(value, unit=""):
    if value is None:
        return "N/A"

    return f"{value:.2f}{unit}"


def draw_text(
    image, message, x, y,
    color=(255, 255, 255),
    scale=0.55
):
    cv2.putText(
        image,
        str(message),
        (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        2,
        cv2.LINE_AA
    )


def draw_dashboard(frame, objects, radar, camera_ok):
    height, width = frame.shape[:2]

    canvas = np.zeros(
        (480, 1000, 3),
        dtype=np.uint8
    )

    canvas[:] = (28, 29, 34)

    canvas[:, :640] = cv2.resize(
        frame, (640, 480)
    )

    sx = 640 / width
    sy = 480 / height

    for obj in objects:
        x1, y1, x2, y2 = obj["box"]

        p1 = (int(x1 * sx), int(y1 * sy))
        p2 = (int(x2 * sx), int(y2 * sy))

        cv2.rectangle(
            canvas, p1, p2,
            (60, 240, 100), 2
        )

        draw_text(
            canvas,
            f"{obj['name']} {obj['conf']:.0%}",
            p1[0],
            max(20, p1[1] - 8),
            (60, 255, 100),
            0.45
        )

    x = 655

    draw_text(canvas, "REAR DETECTION", x, 34,
              scale=0.70)

    draw_text(
        canvas, f"MODULE: {MODULE_ID.upper()}",
        x, 65
    )

    draw_text(
        canvas,
        f"CAMERA: {'ONLINE' if camera_ok else 'OFFLINE'}",
        x, 94
    )

    draw_text(
        canvas,
        f"RADAR: {'ONLINE' if radar['online'] else 'OFFLINE'}",
        x, 123
    )

    draw_text(
        canvas,
        "DISTANCE: " + fmt(radar["distance"], " m"),
        x, 158
    )

    draw_text(
        canvas,
        "APPROACH: " + fmt(radar["speed"], " m/s"),
        x, 188
    )

    draw_text(
        canvas,
        "TTC: " + fmt(radar["ttc"], " s"),
        x, 218
    )

    draw_text(
        canvas,
        f"OBJECTS: {len(objects)}",
        x, 248
    )

    for i, obj in enumerate(objects[:3]):
        draw_text(
            canvas,
            f"- {obj['name']} {obj['conf']:.0%}",
            x, 270 + i * 22,
            scale=0.44
        )

    ble_ok, _ = get_ble_status()

    draw_text(
        canvas,
        f"WRIST BLE: {'CONNECTED' if ble_ok else 'OFFLINE'}",
        x, 357,
        (70, 210, 100) if ble_ok else (60, 80, 255),
        0.48
    )

    risk = radar["risk"]

    if risk is None:
        label = "SENSOR OFFLINE"
        color = (80, 80, 80)

    elif radar["suppressed"]:
        label = "STATIONARY - MUTED"
        color = (110, 90, 50)

    else:
        label = (
            f"LEVEL {risk} - {RISK_NAMES[risk]}"
        )
        color = RISK_COLORS[risk]

    cv2.rectangle(
        canvas,
        (650, 387),
        (990, 447),
        color, -1
    )

    draw_text(
        canvas, label,
        660, 424,
        scale=0.58
    )

    draw_text(
        canvas, "Q: EXIT",
        660, 470,
        (170, 170, 170),
        0.43
    )

    return canvas


# =====================================================
# 11. 메인
# =====================================================

def main():
    print("=" * 45)
    print(" REAR DETECTION + WRIST BLE")
    print("=" * 45)

    cv2.setNumThreads(2)
    torch.set_num_threads(2)

    print("[SYSTEM] Safe NMS enabled")
    print("[YOLO] Loading:", args.model)

    model = YOLO(args.model)

    print("[YOLO] Ready")

    stop_event = threading.Event()

    camera = CameraReceiver()
    camera.start()

    radar_thread = threading.Thread(
        target=receive_radar,
        args=(stop_event,),
        daemon=True
    )

    radar_thread.start()

    if not args.no_ble:
        wrist_thread = threading.Thread(
            target=run_wrist_ble,
            args=(stop_event,),
            daemon=True
        )

        wrist_thread.start()
        print("[BLE] Sender started")
    else:
        print("[BLE] Disabled by --no-ble")

    interval = 1.0 / TARGET_FPS

    last_log = 0.0
    last_risk = None

    print("[CAMERA]", CAMERA_URL)
    print("[RADAR] Port:", RADAR_PORT)
    print("[SYSTEM] Started")

    try:
        while True:
            begin = time.monotonic()

            frame, camera_ok, error, count = (
                camera.snapshot()
            )

            radar = radars[MODULE_ID].snapshot()

            if camera_ok:
                try:
                    objects = detect_objects(
                        model, frame
                    )
                except Exception as e:
                    print("[YOLO ERROR]", repr(e))
                    objects = []

            else:
                frame = np.zeros(
                    (480, 640, 3),
                    dtype=np.uint8
                )

                objects = []

                draw_text(
                    frame,
                    "CAMERA DISCONNECTED",
                    90, 210,
                    (50, 50, 255),
                    0.7
                )

            if not args.no_gui:
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

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            now = time.monotonic()

            risk = radar["risk"]

            if risk != last_risk:
                print(
                    f"[RISK] {last_risk} -> {risk}",
                    flush=True
                )
                last_risk = risk

            if now - last_log >= 1:
                left, right = get_wrist_risk()
                ble_ok, _ = get_ble_status()

                print(
                    f"[CAM] {camera_ok} "
                    f"[FRAMES] {count} "
                    f"[YOLO] {len(objects)} "
                    f"[DIST] {fmt(radar['distance'])} "
                    f"[SPEED] {fmt(radar['speed'])} "
                    f"[TTC] {fmt(radar['ttc'])} "
                    f"[RISK] {risk} "
                    f"[BLE] {ble_ok} "
                    f"[WRIST] L={left} R={right}",
                    flush=True
                )

                if not camera_ok and error:
                    print("[CAMERA DETAIL]", error)

                last_log = now

            elapsed = time.monotonic() - begin

            if elapsed < interval:
                time.sleep(interval - elapsed)

    except KeyboardInterrupt:
        print("[SYSTEM] Interrupted")

    finally:
        stop_event.set()
        camera.stop()
        cv2.destroyAllWindows()
        print("[SYSTEM] Stopped")


if __name__ == "__main__":
    main()
