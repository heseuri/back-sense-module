
import socket
import json
from datetime import datetime

HOST = "0.0.0.0"
PORT = 5005

sock = socket.socket(
    socket.AF_INET,
    socket.SOCK_DGRAM
)

sock.bind((HOST, PORT))

print("=" * 45)
print("Raspberry Pi 5 레이더 수신 + RTT 서버")
print(f"UDP 포트: {PORT}")
print("=" * 45)

try:
    while True:
        raw_data, address = sock.recvfrom(4096)

        # =================================
        # 1. RTT 측정용 PING 처리
        # =================================
        if raw_data.startswith(b"PING:"):
            sequence = raw_data[5:]

            # 숫자 형태인지 검사
            if sequence.isdigit():
                response = b"PONG:" + sequence

                # 수신한 주소로 즉시 응답
                sock.sendto(response, address)

            continue

        # =================================
        # 2. 기존 레이더 JSON 수신
        # =================================
        try:
            data = json.loads(
                raw_data.decode("utf-8")
            )

            module = data.get("module", "unknown")
            detected = data.get("detected", False)
            sequence = data.get("seq", "?")

            if not detected:
                print(f"[{module}] 감지 대상 없음")
                continue

            distance = float(data["distance"])
            speed = float(data["speed"])
            energy = int(data["energy"])

            movement = data.get(
                "movement", "unknown"
            )

            status = {
                "approaching": "접근 중",
                "receding": "멀어지는 중",
                "stationary": "정지 또는 저속"
            }.get(movement, "알 수 없음")

            received_at = datetime.now().strftime(
                "%H:%M:%S.%f"
            )[:-3]

            print(
                f"[{received_at}] "
                f"[{module}] [{status}] "
                f"거리: {distance:.2f}m | "
                f"속도: {speed:.3f}m/s | "
                f"에너지: {energy} | "
                f"순번: {sequence}"
            )

        except (
            ValueError,
            KeyError,
            TypeError,
            UnicodeDecodeError
        ) as e:
            print("[ERROR]", e)

except KeyboardInterrupt:
    print("\n수신 종료")

finally:
    sock.close()

