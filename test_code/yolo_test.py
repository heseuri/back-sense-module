
from picamera2 import Picamera2
from ultralytics import YOLO
import cv2
import time

# YOLO11n 모델 불러오기
model = YOLO("yolo11n.pt")

# 카메라 설정
picam2 = Picamera2(0)

config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "RGB888"},
    buffer_count=3
)

picam2.configure(config)
picam2.start()

time.sleep(2)

print("실시간 카메라 및 YOLO 객체 인식 시작")
print("종료하려면 영상 창에서 Q를 누르세요.")

try:
    while True:
        # 실시간 카메라 프레임 가져오기
        frame = picam2.capture_array()

        # 객체 인식 시작 시간
        start = time.perf_counter()

        results = model.predict(
            source=frame,
            imgsz=640,
            conf=0.4,
            classes=[0, 1, 2, 3, 5, 7],
            verbose=False
        )

        elapsed = time.perf_counter() - start
        fps = 1 / elapsed if elapsed > 0 else 0

        # 인식 결과에 박스와 객체 이름 표시
        annotated = results[0].plot()

        # FPS 화면 표시
        cv2.putText(
            annotated,
            f"YOLO FPS: {fps:.2f}",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        # 실시간 영상 출력
        cv2.imshow("YOLO11n Live Camera", annotated)

        # Q를 누르면 종료
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    print("\n사용자가 종료했습니다.")

finally:
    picam2.stop()
    picam2.close()
    cv2.destroyAllWindows()
    print("카메라 종료")
