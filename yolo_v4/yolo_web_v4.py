
from picamera2 import Picamera2
from flask import Flask, Response
from detector import CombinedDetector
import cv2
import time
import threading

app = Flask(__name__)

detector = None
picam2 = None

camera_lock = threading.Lock()


def initialize():
    global detector, picam2

    # 기존 및 신규 YOLO 모델 초기화
    detector = CombinedDetector()

    # 라즈베리파이 카메라 설정
    picam2 = Picamera2(0)

    config = picam2.create_video_configuration(
        main={
            "size": (640, 480),
            "format": "RGB888"
        },
        buffer_count=3
    )

    picam2.configure(config)
    picam2.start()

    time.sleep(2)

    print("카메라 초기화 완료")
    print("기존 YOLO 임계값: 0.40")
    print("신규 YOLO 임계값: 0.35")
    print("중복 탐지 IoU: 0.50")


def generate_frames():

    while True:

        with camera_lock:

            # 카메라 영상 수신
            frame = picam2.capture_array()

            # 기존 및 신규 객체 인식
            detections, fps = detector.detect(frame)

            # 바운딩 박스 표시
            annotated = detector.draw(
                frame,
                detections,
                fps
            )

        # JPEG 이미지 변환
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
        <title>Rear Detection V4</title>

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

            .base {
                color: #22c55e;
            }

            .custom {
                color: #60a5fa;
            }
        </style>
    </head>

    <body>

        <h2>Raspberry Pi 5 - YOLO V4</h2>
        <p>인체부착형 후방감지 모듈</p>

        <p class="base">
            기존 객체: 사람, 자동차, 자전거,
            오토바이, 버스, 트럭
        </p>

        <p class="custom">
            신규 객체: 전동 킥보드, 전동 휠체어
        </p>

        <p>
            기존 임계값: 40% |
            신규 임계값: 35%
        </p>

        <img src="/video_feed">

    </body>
    </html>
    """


@app.route("/video_feed")
def video_feed():

    return Response(
        generate_frames(),
        mimetype=(
            "multipart/x-mixed-replace;"
            " boundary=frame"
        )
    )


if __name__ == "__main__":

    try:
        initialize()

        print("YOLO V4 웹 카메라 서버 시작")
        print("포트: 5000")

        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            threaded=True
        )

    finally:

        if picam2 is not None:
            picam2.stop()
            picam2.close()
