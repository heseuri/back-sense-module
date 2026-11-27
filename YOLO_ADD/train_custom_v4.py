
from pathlib import Path
from ultralytics import YOLO


def main():
    # 프로젝트 경로 설정
    base = Path(__file__).resolve().parent
    dataset = base / "dataset_v4"

    # 데이터셋 폴더 확인
    for split in ("train", "valid", "test"):
        for folder in ("images", "labels"):
            path = dataset / split / folder

            if not path.is_dir():
                raise FileNotFoundError(
                    f"폴더가 없습니다: {path}"
                )

    # 학습용 YAML 파일 생성
    yaml_path = base / "local_data_v4.yaml"

    yaml_path.write_text(
        f'path: "{dataset.as_posix()}"\n'
        'train: train/images\n'
        'val: valid/images\n'
        'test: test/images\n'
        'nc: 2\n'
        'names:\n'
        '  0: electric_scooter\n'
        '  1: electric_wheelchair\n',
        encoding="utf-8"
    )

    print("=== YOLO V4 모델 튜닝 시작 ===")

    # 기존 사전학습 모델 불러오기
    model = YOLO(str(base / "yolo11n.pt"))

    # 모델 파인튜닝
    model.train(
        data=str(yaml_path),
        epochs=50,
        imgsz=640,
        batch=4,
        workers=0,
        device="cpu",

        # 튜닝 파라미터
        patience=15,
        mosaic=0.5,
        close_mosaic=10,
        seed=42,

        # 결과 저장 경로
        project=str(base / "runs"),
        name="rear_safety_v4",
        exist_ok=False,
        plots=True
    )

    # 실제 모델 저장 위치 출력
    save_dir = Path(model.trainer.save_dir)

    print("\n=== 모델 튜닝 완료 ===")
    print("결과 폴더:", save_dir)
    print("최적 모델:", save_dir / "weights" / "best.pt")


if __name__ == "__main__":
    main()
