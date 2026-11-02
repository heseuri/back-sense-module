import serial
import time

PORT = "/dev/ttyAMA0"
BAUD = 9600

def send_command(ser, command):
    ser.write((command + "\r\n").encode())
    ser.flush()

def parse_radar(line):
    if not line.startswith("$DFDMD,"):
        return

    parts = line.split(",")

    try:
        count = int(parts[1].strip())

        if count == 0:
            print("감지 대상 없음")
            return

        distance = float(parts[3].strip())
        speed = float(parts[4].strip())
        energy = int(parts[5].strip())

        # 속도 방향 판단
        if speed < -0.05:
            status = "접근 중"
        elif speed > 0.05:
            status = "멀어지는 중"
        else:
            status = "정지 또는 저속"

        # 임시 위험도 판단
        if status == "접근 중" and distance < 1.0:
            risk = "위험"
        elif status == "접근 중" and distance < 2.0:
            risk = "주의"
        else:
            risk = "안전"

        print(
            f"[{status}] "
            f"거리: {distance:.2f}m | "
            f"속도: {speed:.3f}m/s | "
            f"신호: {energy} | "
            f"위험도: {risk}"
        )

    except (ValueError, IndexError):
        print("데이터 해석 실패:", line)


def main():
    with serial.Serial(PORT, BAUD, timeout=1) as ser:
        time.sleep(1)

        send_command(ser, "sensorStop")
        time.sleep(1)

        send_command(ser, "setRunApp 1")
        time.sleep(2)

        send_command(ser, "sensorStart")
        time.sleep(1)

        print("C4001 접근 감지 시작")
        print("Ctrl+C 종료\n")

        while True:
            raw = ser.readline()

            if raw:
                line = raw.decode(
                    "utf-8", errors="replace"
                ).strip()

                parse_radar(line)


try:
    main()

except KeyboardInterrupt:
    print("\n측정 종료")
