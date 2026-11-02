
from picamera2 import Picamera2
from ultralytics import YOLO
from flask import Flask, Response
import cv2
import time
import threading

app = Flask(__name__)

# YOLO 모델
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

# 여러 요청이 카메라를 동시에 사용하지 않도록 보호
camera_lock = threading.Lock()

def generate_frames():
    while True:
        with camera_lock:
            frame = picam2.capture_array()

            start = time.perf_counter()

            results = model.predict(
                source=frame,
                imgsz=416,
                conf=0.4,
                classes=[0, 1, 2, 3, 5, 7],
                verbose=False
            )

            elapsed = time.perf_counter() - start
            fps = 1 / elapsed if elapsed > 0 else 0

            annotated = results[0].plot()

        cv2.putText(
            annotated,
            f"YOLO FPS: {fps:.2f}",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        success, buffer = cv2.imencode(
            ".jpg",
            annotated,
            [cv2.IMWRITE_JPEG_QUALITY, 75]
        )

        if not success:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + buffer.tobytes()
            + b"\r\n"
        )


@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>Rear Detection Camera</title>
        <style>
            body {
                background: #111827;
                color: white;
                text-align: center;
                font-family: Arial, sans-serif;
                padding: 30px;
            }
            img {
                width: 100%;
                max-width: 960px;
                border-radius: 12px;
            }
        </style>
    </head>
    <body>
        <h2>Raspberry Pi 5 - YOLO11n Live</h2>
        <p>실시간 객체 인식 영상</p>
        <img src="/video_feed">
    </body>
    </html>
    """


@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    try:
        print("웹 카메라 서버 시작")
        print("포트: 5000")
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            threaded=True
        )
    finally:
        picam2.stop()
        picam2.close()
