import serial
import time

PORT = "/dev/ttyAMA0"
BAUD = 9600

with serial.Serial(PORT, BAUD, timeout=0.5) as ser:
    time.sleep(1)
    ser.reset_input_buffer()

    commands = [
        "sensorStop",
        "setRunApp 1",
        "getRunApp",
        "sensorStart"
    ]

    for command in commands:
        print(f"\n[명령 전송] {command}")
        ser.write((command + "\r\n").encode())
        ser.flush()

        end = time.monotonic() + 2
        while time.monotonic() < end:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                print("[응답]", repr(data))
            time.sleep(0.05)

    print("\n실시간 데이터 확인 중...")

    try:
        while True:
            data = ser.readline()
            if data:
                print(data.decode("utf-8", errors="replace").strip())
    except KeyboardInterrupt:
        print("\n종료")
