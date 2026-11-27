
from pathlib import Path
from ultralytics import YOLO
from PIL import Image, ImageOps
import cv2
import numpy as np
import time

BASE = Path(__file__).resolve().parent

# 기존 YOLO 모델
BASE_MODEL = BASE / "yolo11n.pt"

# 추가 학습한 V4 모델
CUSTOM_MODEL = (
    BASE / "runs" / "rear_safety_v4"
    / "weights" / "best.pt"
)

# 테스트 및 결과 폴더
IMAGE_FOLDER = BASE / "test_images"
OUTPUT_FOLDER = BASE / "runs" / "combined_test"

# 신뢰도 임계값
BASE_CONF = 0.40
CUSTOM_CONF = 0.35

# 기존 팀 프로젝트의 탐지 클래스
BASE_CLASSES = [0, 1, 2, 3, 5, 7]


def draw_results(frame, result, color, source):
    for box in result.boxes:

        class_id = int(box.cls.item())
        confidence = float(box.conf.item())
        class_name = result.names[class_id]

        x1, y1, x2, y2 = map(
            int, box.xyxy[0].tolist()
        )

        label = f"{class_name} {confidence:.2f}"

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            color,
            2
        )

        cv2.putText(
            frame,
            label,
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2
        )

        print(
            f"[{source}] {class_name} | "
            f"신뢰도: {confidence:.1%}"
        )


def main():

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    # 두 모델 불러오기
    base_model = YOLO(str(BASE_MODEL))
    custom_model = YOLO(str(CUSTOM_MODEL))

    extensions = {
        ".jpg", ".jpeg", ".png",
        ".webp", ".avif", ".bmp"
    }

    images = sorted(
        p for p in IMAGE_FOLDER.iterdir()
        if p.suffix.lower() in extensions
    )

    print("=" * 50)
    print("YOLO 통합 객체 인식 테스트")
    print("=" * 50)
    print("기존 모델 임계값:", BASE_CONF)
    print("신규 모델 임계값:", CUSTOM_CONF)

    for path in images:

        try:
            with Image.open(path) as image:
                rgb = np.array(
                    ImageOps.exif_transpose(image)
                    .convert("RGB")
                )

            frame = cv2.cvtColor(
                rgb, cv2.COLOR_RGB2BGR
            )

        except Exception as error:
            print("이미지 읽기 실패:", path.name)
            print(error)
            continue

        print("\n" + "-" * 50)
        print("사진:", path.name)

        start = time.perf_counter()

        # 기존 객체 탐지
        base_result = base_model.predict(
            source=frame,
            conf=BASE_CONF,
            classes=BASE_CLASSES,
            imgsz=416,
            device="cpu",
            verbose=False
        )[0]

        # 신규 객체 탐지
        custom_result = custom_model.predict(
            source=frame,
            conf=CUSTOM_CONF,
            imgsz=640,
            device="cpu",
            verbose=False
        )[0]

        elapsed = time.perf_counter() - start

        # 결과를 하나의 이미지에 표시
        output = frame.copy()

        # 기존 객체: 초록색
        draw_results(
            output,
            base_result,
            (0, 255, 0),
            "기존 YOLO"
        )

        # 신규 객체: 파란색
        draw_results(
            output,
            custom_result,
            (255, 0, 0),
            "신규 YOLO"
        )

        print(f"통합 추론 시간: {elapsed * 1000:.1f}ms")

        # 결과 저장
        save_path = OUTPUT_FOLDER / (
            path.name + "_combined.jpg"
        )

        success, encoded = cv2.imencode(
            ".jpg", output
        )

        if success:
            encoded.tofile(str(save_path))

    print("\n=== 통합 객체 인식 테스트 완료 ===")
    print("결과 저장 위치:", OUTPUT_FOLDER)


if __name__ == "__main__":
    main()
