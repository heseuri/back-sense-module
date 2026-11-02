
import serial
import time

PORT = "/dev/serial0"
BAUD = 9600

try:
    radar = serial.Serial(
        port=PORT,
        baudrate=BAUD,
        timeout=1
    )

    print("C4001 레이더 UART 연결 완료")
    print("센서 응답 확인 중... (Ctrl+C 종료)")

    # 통신 확인용 명령
    radar.reset_input_buffer()
    radar.write(b"getUart\r\n")

    last_query = time.monotonic()

    while True:
        if radar.in_waiting:
            data = radar.readline()
            if data:
                print("수신:", data.decode(
                    "utf-8", errors="replace"
                ).strip())

        # 주기적으로 통신 상태 확인
        if time.monotonic() - last_query >= 5:
            radar.write(b"getUart\r\n")
            last_query = time.monotonic()

        time.sleep(0.05)

except serial.SerialException as e:
    print("UART 오류:", e)
    print("포트 및 UART 활성화 상태를 확인하세요.")

except KeyboardInterrupt:
    print("\n테스트 종료")

finally:
    if "radar" in locals() and radar.is_open:
        radar.close()
