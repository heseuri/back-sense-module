
from pathlib import Path
from ultralytics import YOLO
import cv2
import time

BASE = Path(__file__).resolve().parent

# 모델 경로
BASE_MODEL = BASE / "yolo11n.pt"
CUSTOM_MODEL = BASE / "best.pt"

# 신뢰도 임계값
BASE_CONF = 0.40
CUSTOM_CONF = 0.35

# 중복 탐지 판단 임계값
DUPLICATE_IOU = 0.50

# 기존 객체 6종
BASE_CLASSES = [0, 1, 2, 3, 5, 7]


def calculate_iou(a, b):
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])

    intersection = (
        max(0, x2 - x1) * max(0, y2 - y1)
    )

    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])

    union = area_a + area_b - intersection

    return intersection / union if union > 0 else 0


class CombinedDetector:

    def __init__(self):
        self.base_model = YOLO(str(BASE_MODEL))
        self.custom_model = YOLO(str(CUSTOM_MODEL))

    def parse_results(self, result, source):
        detections = []

        for box in result.boxes:
            class_id = int(box.cls.item())

            detections.append({
                "object_type": result.names[class_id],
                "confidence": float(box.conf.item()),
                "bbox": box.xyxy[0].tolist(),
                "source": source
            })

        return detections

    def remove_duplicates(self, base, custom):
        filtered = []

        for old in base:
            duplicate = False

            # 이동수단 간 중복 탐지만 검사
            if old["object_type"] in (
                "bicycle", "motorcycle"
            ):
                for new in custom:
                    overlap = calculate_iou(
                        old["bbox"],
                        new["bbox"]
                    )

                    if overlap >= DUPLICATE_IOU:
                        duplicate = True
                        break

            if not duplicate:
                filtered.append(old)

        return filtered + custom

    def detect(self, frame):
        start = time.perf_counter()

        # 기존 YOLO 객체 탐지
        base_result = self.base_model.predict(
            source=frame,
            imgsz=416,
            conf=BASE_CONF,
            classes=BASE_CLASSES,
            device="cpu",
            verbose=False
        )[0]

        # 신규 객체 탐지
        custom_result = self.custom_model.predict(
            source=frame,
            imgsz=640,
            conf=CUSTOM_CONF,
            device="cpu",
            verbose=False
        )[0]

        base = self.parse_results(
            base_result, "base"
        )

        custom = self.parse_results(
            custom_result, "custom"
        )

        # 중복 탐지 제거
        detections = self.remove_duplicates(
            base, custom
        )

        elapsed = time.perf_counter() - start
        fps = 1 / elapsed if elapsed > 0 else 0

        return detections, fps

    def draw(self, frame, detections, fps):
        output = frame.copy()

        for obj in detections:

            x1, y1, x2, y2 = map(
                int, obj["bbox"]
            )

            label = (
                f'{obj["object_type"]} '
                f'{obj["confidence"]:.2f}'
            )

            # 기존 객체: 초록색
            # 신규 객체: 파란색
            color = (
                (0, 255, 0)
                if obj["source"] == "base"
                else (255, 0, 0)
            )

            cv2.rectangle(
                output,
                (x1, y1),
                (x2, y2),
                color,
                2
            )

            cv2.putText(
                output,
                label,
                (x1, max(20, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )

        cv2.putText(
            output,
            f"Detection FPS: {fps:.2f}",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        return output
