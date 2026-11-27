
from pathlib import Path
from ultralytics import YOLO

BASE = Path(__file__).resolve().parent

MODEL = BASE / "runs" / "rear_safety_v4" / "weights" / "best.pt"
IMAGES = BASE / "dataset_v4" / "test" / "images"
LABELS = BASE / "dataset_v4" / "test" / "labels"

THRESHOLDS = [0.35]

CLASSES = {
    0: "electric_scooter",
    1: "electric_wheelchair"
}


# 바운딩 박스 일치 정도 계산
def iou(a, b):
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])

    inter = max(0, x2 - x1) * max(0, y2 - y1)

    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])

    union = area_a + area_b - inter
    return inter / union if union > 0 else 0


def main():
    model = YOLO(str(MODEL))

    results = model.predict(
        source=str(IMAGES),
        conf=0.05,
        imgsz=640,
        device="cpu",
        verbose=False
    )

    samples = []

    for result in results:
        label_path = LABELS / (
            Path(result.path).stem + ".txt"
        )

        if not label_path.exists():
            raise FileNotFoundError(label_path)

        ground_truth = []

        for line in label_path.read_text().splitlines():
            if not line.strip():
                continue

            c, x, y, w, h = map(float, line.split())

            ground_truth.append((
                int(c),
                [x-w/2, y-h/2, x+w/2, y+h/2]
            ))

        predictions = []

        for box in result.boxes:
            predictions.append((
                int(box.cls.item()),
                float(box.conf.item()),
                box.xyxyn[0].tolist()
            ))

        samples.append((ground_truth, predictions))

    print("\n=== V4 임계값 비교 테스트 ===")
    print("검증 이미지:", len(samples))

    for class_id, class_name in CLASSES.items():
        print("\n객체:", class_name)
        print("-" * 65)
        print("Conf     TP    FP    FN    Precision  Recall     F1")

        best_f1 = -1
        best_conf = None

        for threshold in THRESHOLDS:
            tp = fp = fn = 0

            for gt, pred in samples:
                targets = [
                    b for c, b in gt if c == class_id
                ]

                detections = sorted(
                    [(s, b) for c, s, b in pred
                     if c == class_id and s >= threshold],
                    reverse=True,
                    key=lambda x: x[0]
                )

                matched = set()

                for score, box in detections:
                    best_iou = 0
                    best_index = -1

                    for idx, target in enumerate(targets):
                        if idx in matched:
                            continue

                        value = iou(box, target)

                        if value > best_iou:
                            best_iou = value
                            best_index = idx

                    if best_index != -1 and best_iou >= 0.5:
                        tp += 1
                        matched.add(best_index)
                    else:
                        fp += 1

                fn += len(targets) - len(matched)

            p = tp / (tp + fp) if tp + fp else 0
            r = tp / (tp + fn) if tp + fn else 0
            f1 = 2*p*r / (p+r) if p+r else 0

            print(
                f"{threshold:.2f}     "
                f"{tp:2d}    {fp:2d}    {fn:2d}    "
                f"{p:8.1%}   {r:8.1%}   {f1:.3f}"
            )

            if f1 > best_f1:
                best_f1 = f1
                best_conf = threshold

        print(f"최고 F1 임계값 후보: {best_conf}")
        print(f"최고 F1-score: {best_f1:.3f}")


if __name__ == "__main__":
    main()
