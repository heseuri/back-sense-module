
import os
import time
import json
import math
import socket
import threading
import urllib.request
from collections import deque

# CPU 추론 부하 제한
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["OPENBLAS_NUM_THREADS"] = "2"

import cv2
import numpy as np
import torch
import torchvision

# ==========================================
# 1. Illegal instruction NMS 우회
# ==========================================

def safe_nms(boxes, scores, iou_threshold):
    """
    torchvision C++ NMS 대신 PyTorch 연산 사용.
    boxes: [N, 4], xyxy
    scores: [N]
    """
    if boxes.numel() == 0:
        return torch.empty(
            (0,), dtype=torch.long, device=boxes.device
        )

    x1, y1, x2, y2 = boxes.unbind(1)

    areas = (
        (x2 - x1).clamp(min=0) *
        (y2 - y1).clamp(min=0)
    )

    order = scores.argsort(descending=True)
    keep = []

    while order.numel() > 0:
        i = int(order[0].item())
        keep.append(i)

        if order.numel() == 1:
            break

        rest = order[1:]

        xx1 = torch.maximum(x1[i], x1[rest])
        yy1 = torch.maximum(y1[i], y1[rest])
        xx2 = torch.minimum(x2[i], x2[rest])
        yy2 = torch.minimum(y2[i], y2[rest])

        w = (xx2 - xx1).clamp(min=0)
        h = (yy2 - yy1).clamp(min=0)

        intersection = w * h
        union = (
            areas[i] + areas[rest] - intersection
        ).clamp(min=1e-7)

        iou = intersection / union
        order = rest[iou <= iou_threshold]

    return torch.tensor(
        keep, dtype=torch.long, device=boxes.device
    )


torchvision.ops.nms = safe_nms
torchvision.ops.boxes.nms = safe_nms

print("[NMS] Safe PyTorch NMS enabled", flush=True)

from ultralytics import YOLO


# ==========================================
# 2. 설정
# ==========================================

ESP_IP = "192.168.50.2"
CAMERA_URL = f"http://{ESP_IP}/stream"

RADAR_PORT = 5005
MODULE_ID = "left"

MODEL_PATH = "yolo26n.pt"
CONF = 0.40
IMG_SIZE = 320
TARGET_FPS = 5

CAMERA_TIMEOUT = 3.0
RADAR_TIMEOUT = 1.5

CLASS_IDS = [0, 1, 2, 3, 5, 7]

RISK_NAMES = [
    "SAFE", "CAUTION", "WARNING", "DANGER"
]

RISK_COLORS = [
    (40, 170, 40),
    (0, 220, 230),
    (0, 140, 255),
    (30, 30, 240)
]


# ==========================================
# 3. 카메라 수신
# ==========================================

class CameraReceiver:
    def __init__(self):
        self.lock = threading.Lock()
        self.frame = None
        self.last_time = 0.0
        self.error = "Connecting"
        self.running = True
        self.count = 0

    def start(self):
        threading.Thread(
            target=self.run, daemon=True
        ).start()

    def run(self):
        while self.running:
            try:
                print("[CAMERA] Connecting...",
                      flush=True)

                req = urllib.request.Request(
                    CAMERA_URL,
                    headers={"Connection": "close"}
                )

                with urllib.request.urlopen(
                    req, timeout=5
                ) as response:

                    print("[CAMERA] HTTP",
                          response.status, flush=True)

                    buf = bytearray()
                    last_decode = 0.0

                    while self.running:
                        chunk = response.read1(4096)

                        if not chunk:
                            raise ConnectionError(
                                "Camera stream closed"
                            )

                        buf.extend(chunk)

                        # 과도한 버퍼 증가 방지
                        if len(buf) > 1_000_000:
                            buf.clear()
                            continue

                        while True:
                            start = buf.find(b"\xff\xd8")

                            if start < 0:
                                if len(buf) > 65536:
                                    buf.clear()
                                break

                            end = buf.find(
                                b"\xff\xd9", start + 2
                            )

                            if end < 0:
                                if start > 0:
                                    del buf[:start]
                                break

                            jpg = bytes(
                                buf[start:end + 2]
                            )
                            del buf[:end + 2]

                            now = time.monotonic()

                            if now - last_decode < 0.2:
                                continue

                            frame = cv2.imdecode(
                                np.frombuffer(
                                    jpg, dtype=np.uint8
                                ),
                                cv2.IMREAD_COLOR
                            )

                            if frame is None:
                                continue

                            last_decode = now

                            with self.lock:
                                self.frame = frame
                                self.last_time = now
                                self.error = ""
                                self.count += 1

            except Exception as e:
                print("[CAMERA ERROR]", repr(e),
                      flush=True)

                with self.lock:
                    self.error = str(e)
                    self.frame = None

                time.sleep(2)

    def snapshot(self):
        with self.lock:
            ok = (
                self.frame is not None
                and time.monotonic()
                - self.last_time < CAMERA_TIMEOUT
            )

            frame = (
                self.frame.copy() if ok else None
            )

            return frame, ok, self.error


# ==========================================
# 4. 레이더 데이터 및 위험도 계산
# ==========================================

class RadarTracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.last_time = 0.0
        self.last_seq = None
        self.valid = False
        self.detected = False
        self.raw_speed = 0.0
        self.history = deque(maxlen=30)

    def update(self, packet):
        now = time.monotonic()

        with self.lock:
            seq = packet.get("seq")
            if seq is not None and seq == self.last_seq:
                return

            self.last_seq = seq
            self.last_time = now

            self.valid = packet.get("valid") is True
            self.detected = packet.get("detected") is True

            if not self.valid or not self.detected:
                self.history.clear()
                return

            try:
                distance = float(
                    packet["distance_m"]
                )
                speed = float(packet["speed_mps"])
            except (ValueError, TypeError, KeyError):
                self.valid = False
                self.history.clear()
                return

            if (
                not math.isfinite(distance)
                or not math.isfinite(speed)
                or not 0.2 <= distance <= 25
            ):
                self.valid = False
                self.history.clear()
                return

            self.raw_speed = speed
            self.history.append((now, distance))

    def snapshot(self):
        with self.lock:
            online = (
                self.last_time > 0
                and time.monotonic()
                - self.last_time <= RADAR_TIMEOUT
                and self.valid
            )

            result = {
                "online": online,
                "detected": False,
                "distance": None,
                "speed": 0.0,
                "raw_speed": None,
                "ttc": None,
                "risk": None if not online else 0
            }

            if not online or not self.detected:
                return result

            now = time.monotonic()
            recent = [
                (t, d) for t, d in self.history
                if now - t <= 1.2
            ]

            if not recent:
                return result

            distance = float(np.median(
                [d for _, d in recent[-5:]]
            ))

            speed = 0.0

            if len(recent) >= 2:
                t0, d0 = recent[0]
                t1, d1 = recent[-1]

                if t1 - t0 >= 0.3:
                    speed = (d0 - d1) / (t1 - t0)

            if not math.isfinite(speed) or abs(speed) > 20:
                speed = 0.0

            ttc = None
            risk = 0

            if speed > 0.2:
                ttc = distance / speed

                if distance <= 1.0 or ttc <= 1.0:
                    risk = 3
                elif distance <= 2.0 or ttc <= 2.0:
                    risk = 2
                elif distance <= 3.0 or ttc <= 3.5:
                    risk = 1

            result.update({
                "detected": True,
                "distance": distance,
                "speed": speed,
                "raw_speed": self.raw_speed,
                "ttc": ttc,
                "risk": risk
            })

            return result


radars = {
    "left": RadarTracker(),
    "right": RadarTracker()
}


def receive_radar():
    sock = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM
    )
    sock.bind(("0.0.0.0", RADAR_PORT))
    sock.settimeout(1.0)

    print("[RADAR] UDP listening:", RADAR_PORT,
          flush=True)

    while True:
        try:
            raw, sender = sock.recvfrom(4096)
            packet = json.loads(
                raw.decode("utf-8")
            )

            module = packet.get("module")

            if module in radars:
                radars[module].update(packet)

        except socket.timeout:
            continue
        except Exception as e:
            print("[RADAR ERROR]", repr(e),
                  flush=True)


# ==========================================
# 5. YOLO 인식
# ==========================================

def detect_objects(model, frame):
    results = model.predict(
        frame,
        imgsz=IMG_SIZE,
        conf=CONF,
        classes=CLASS_IDS,
        device="cpu",
        verbose=False
    )[0]

    objects = []

    for box in results.boxes:
        cid = int(box.cls[0])
        name = results.names[cid]

        xyxy = box.xyxy[0].tolist()

        objects.append({
            "name": name.upper(),
            "conf": float(box.conf[0]),
            "box": tuple(map(int, xyxy))
        })

    return objects


# ==========================================
# 6. 화면 출력
# ==========================================

def fmt(value, unit=""):
    if value is None:
        return "N/A"
    return f"{value:.2f}{unit}"


def put(canvas, msg, x, y, color=(255, 255, 255),
        scale=0.55):
    cv2.putText(
        canvas, str(msg), (x, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale, color, 2, cv2.LINE_AA
    )


def draw_dashboard(frame, objects, radar, camera_ok):
    h, w = frame.shape[:2]

    canvas = np.zeros((480, 1000, 3), np.uint8)
    canvas[:] = (28, 29, 34)

    canvas[:, :640] = cv2.resize(
        frame, (640, 480)
    )

    sx = 640 / w
    sy = 480 / h

    for obj in objects:
        x1, y1, x2, y2 = obj["box"]

        x1 = int(x1 * sx)
        x2 = int(x2 * sx)
        y1 = int(y1 * sy)
        y2 = int(y2 * sy)

        cv2.rectangle(
            canvas, (x1, y1), (x2, y2),
            (60, 240, 100), 2
        )

        put(
            canvas,
            f"{obj['name']} {obj['conf']:.0%}",
            x1, max(20, y1 - 8),
            (60, 255, 100), 0.45
        )

    x = 655

    put(canvas, "REAR DETECTION", x, 35,
        scale=0.72)
    put(canvas, f"MODULE: {MODULE_ID}", x, 68)
    put(canvas,
        f"CAMERA: {'ONLINE' if camera_ok else 'OFFLINE'}",
        x, 98)

    put(canvas,
        f"RADAR: {'ONLINE' if radar['online'] else 'OFFLINE'}",
        x, 128)

    put(canvas,
        "DISTANCE: " + fmt(radar["distance"], " m"),
        x, 164)
    put(canvas,
        "APPROACH: " + fmt(radar["speed"], " m/s"),
        x, 196)
    put(canvas,
        "RADAR SPEED: " + fmt(radar["raw_speed"], " m/s"),
        x, 228, scale=0.45)
    put(canvas,
        "TTC: " + fmt(radar["ttc"], " s"),
        x, 260)

    put(canvas, f"OBJECTS: {len(objects)}",
        x, 293)

    for i, obj in enumerate(objects[:3]):
        put(
            canvas,
            f"- {obj['name']} {obj['conf']:.0%}",
            x, 318 + i * 22,
            scale=0.44
        )

    risk = radar["risk"]

    if risk is None:
        label = "SENSOR OFFLINE"
        color = (80, 80, 80)
    else:
        label = (
            f"LEVEL {risk} - {RISK_NAMES[risk]}"
        )
        color = RISK_COLORS[risk]

    cv2.rectangle(
        canvas, (650, 387), (990, 447),
        color, -1
    )

    put(canvas, label, 660, 424, scale=0.60)
    put(canvas, "Q: EXIT", 660, 470,
        (170, 170, 170), scale=0.43)

    return canvas


# ==========================================
# 7. 메인 프로그램
# ==========================================

def main():
    print("================================")
    print("  REAR DETECTION MONITOR FIXED")
    print("================================")

    cv2.setNumThreads(2)
    torch.set_num_threads(2)

    print("[YOLO] Loading:", MODEL_PATH,
          flush=True)
    model = YOLO(MODEL_PATH)
    print("[YOLO] Model ready", flush=True)

    camera = CameraReceiver()
    camera.start()

    threading.Thread(
        target=receive_radar,
        daemon=True
    ).start()

    interval = 1.0 / TARGET_FPS
    last_log = 0

    print("[SYSTEM] Running", flush=True)

    try:
        while True:
            begin = time.monotonic()

            frame, camera_ok, error = camera.snapshot()
            radar = radars[MODULE_ID].snapshot()

            if camera_ok:
                print("[DEBUG] YOLO START", flush=True)

                try:
                    objects = detect_objects(
                        model, frame
                    )
                except Exception as e:
                    print("[YOLO ERROR]", repr(e),
                          flush=True)
                    objects = []

                print("[DEBUG] YOLO END", flush=True)

            else:
                frame = np.zeros(
                    (480, 640, 3), np.uint8
                )
                objects = []
                put(
                    frame, "CAMERA DISCONNECTED",
                    90, 210, (40, 40, 255), 0.7
                )

            dashboard = draw_dashboard(
                frame, objects, radar, camera_ok
            )

            cv2.imshow(
                "Rear Detection Monitor",
                dashboard
            )

            now = time.monotonic()

            if now - last_log >= 1:
                print(
                    f"[CAMERA] {camera_ok} "
                    f"[OBJECTS] {len(objects)} "
                    f"[DISTANCE] {radar['distance']} "
                    f"[SPEED] {radar['speed']:.2f} "
                    f"[TTC] {radar['ttc']} "
                    f"[RISK] {radar['risk']}",
                    flush=True
                )
                if not camera_ok and error:
                    print("[CAMERA DETAIL]", error,
                          flush=True)
                last_log = now

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            elapsed = time.monotonic() - begin

            if elapsed < interval:
                time.sleep(interval - elapsed)

    except KeyboardInterrupt:
        pass
    finally:
        camera.running = False
        cv2.destroyAllWindows()
        print("[SYSTEM] Stopped", flush=True)


if __name__ == "__main__":
    main()
