
from pathlib import Path
from detector import CombinedDetector
from PIL import Image, ImageOps
import numpy as np
import cv2

BASE = Path(__file__).resolve().parent

IMAGE_FOLDER = BASE / "test_images"
OUTPUT_FOLDER = BASE / "test_results"


def test_duplicates(detector):

    print("\n=== 중복 탐지 제거 기능 테스트 ===")

    # 가상의 기존 YOLO 탐지 결과
    base = [
        {
            "object_type": "person",
            "confidence": 0.90,
            "bbox": [100, 50, 250, 350],
            "source": "base"
        },
        {
            "object_type": "motorcycle",
            "confidence": 0.80,
            "bbox": [100, 200, 300, 400],
            "source": "base"
        },
        {
            "object_type": "bicycle",
            "confidence": 0.85,
            "bbox": [400, 100, 600, 400],
            "source": "base"
        }
    ]

    # 가상의 신규 YOLO 탐지 결과
    custom = [
        {
            "object_type": "electric_scooter",
            "confidence": 0.85,
            "bbox": [110, 210, 290, 390],
            "source": "custom"
        }
    ]

    result = detector.remove_duplicates(
        base, custom
    )

    before = [
        obj["object_type"]
        for obj in base + custom
    ]

    after = [
        obj["object_type"]
        for obj in result
    ]

    print("제거 전:", before)
    print("제거 후:", after)

    assert "motorcycle" not in after
    assert "person" in after
    assert "bicycle" in after
    assert "electric_scooter" in after

    print("중복 탐지 제거 테스트: PASS")


def main():

    if not IMAGE_FOLDER.is_dir():
        raise FileNotFoundError(IMAGE_FOLDER)

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=== 통합 객체 인식 모듈 실행 ===")

    detector = CombinedDetector()

    # 중복 탐지 제거 기능 검사
    test_duplicates(detector)

    extensions = {
        ".jpg", ".jpeg", ".png",
        ".webp", ".avif", ".bmp"
    }

    images = sorted(
        p for p in IMAGE_FOLDER.iterdir()
        if p.suffix.lower() in extensions
    )

    success_count = 0
    fail_count = 0

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
            fail_count += 1
            continue

        # 기존 및 신규 객체 통합 탐지
        detections, fps = detector.detect(frame)

        # 바운딩 박스 표시
        output = detector.draw(
            frame, detections, fps
        )

        print("\n" + "-" * 50)
        print("사진:", path.name)

        if not detections:
            print("인식된 객체 없음")

        for obj in detections:

            print(
                f'[{obj["source"]}] '
                f'{obj["object_type"]} | '
                f'신뢰도: {obj["confidence"]:.1%}'
            )

        print(f"추론 FPS: {fps:.2f}")

        save_path = OUTPUT_FOLDER / (
            path.name + "_result.jpg"
        )

        success, encoded = cv2.imencode(
            ".jpg", output
        )

        if success:
            encoded.tofile(str(save_path))
            success_count += 1
        else:
            fail_count += 1

    print("\n" + "=" * 50)
    print("=== 전체 테스트 완료 ===")
    print("전체 이미지:", len(images))
    print("처리 성공:", success_count)
    print("처리 실패:", fail_count)
    print("결과 저장 위치:", OUTPUT_FOLDER)


if __name__ == "__main__":
    main()
