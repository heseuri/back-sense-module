
from pathlib import Path
from ultralytics import YOLO


def main():
    # 프로젝트 기본 경로
    base = Path(__file__).resolve().parent

    # V4 학습 모델 경로
    model_path = (
        base / "runs" / "rear_safety_v4"
        / "weights" / "best.pt"
    )

    # 테스트 이미지 폴더
    image_folder = base / "test_images"

    # 신뢰도 임계값
    confidence_threshold = 0.25

    # 파일 및 폴더 존재 여부 확인
    if not model_path.exists():
        raise FileNotFoundError(
            f"모델 파일이 없습니다: {model_path}"
        )

    if not image_folder.exists():
        raise FileNotFoundError(
            f"테스트 폴더가 없습니다: {image_folder}"
        )

    # V4 모델 불러오기
    model = YOLO(str(model_path))

    print("=" * 50)
    print("YOLO V4 객체 인식 테스트")
    print("=" * 50)
    print(f"사용 모델: {model_path}")
    print(f"신뢰도 임계값: {confidence_threshold:.0%}")

    # 객체 인식 실행
    results = model.predict(
        source=str(image_folder),
        conf=confidence_threshold,
        imgsz=640,
        device="cpu",
        save=True,
        project=str(base / "runs"),
        name="custom_test_v4",
        exist_ok=True,
        verbose=False
    )

    # 결과 집계
    total_images = len(results)
    detected_images = 0
    scooter_count = 0
    wheelchair_count = 0
    no_detection = 0

    # 이미지별 결과 출력
    for result in results:
        print("\n" + "-" * 50)
        print(f"사진: {Path(result.path).name}")

        if len(result.boxes) == 0:
            print("인식된 객체 없음")
            no_detection += 1
            continue

        detected_images += 1

        for box in result.boxes:
            class_id = int(box.cls.item())
            confidence = float(box.conf.item())
            class_name = model.names[class_id]

            if class_name == "electric_scooter":
                scooter_count += 1

            elif class_name == "electric_wheelchair":
                wheelchair_count += 1

            print(
                f"인식 객체: {class_name} | "
                f"신뢰도: {confidence:.1%}"
            )

    # 전체 테스트 결과 출력
    print("\n" + "=" * 50)
    print("V4 모델 테스트 결과")
    print("=" * 50)
    print(f"전체 테스트 이미지: {total_images}장")
    print(f"객체가 탐지된 이미지: {detected_images}장")
    print(f"객체가 탐지되지 않은 이미지: {no_detection}장")
    print(f"전동 킥보드 탐지: {scooter_count}개")
    print(f"전동 휠체어 탐지: {wheelchair_count}개")
    print(f"신뢰도 임계값: {confidence_threshold:.0%}")

    print("\n결과 저장 위치:")
    print(base / "runs" / "custom_test_v4")

    print("\n=== 테스트 완료 ===")


if __name__ == "__main__":
    main()
