import asyncio
import json
from bleak import BleakScanner, BleakClient

DEVICE_NAME = "RearSensor_ESP32"

CHARACTERISTIC_UUID = (
    "87654321-4321-4321-4321-cba987654321"
)

def notification_handler(sender, data):
    try:
        sensor = json.loads(data.decode("utf-8"))
        print(
            f"거리: {sensor['distance']}m | "
            f"속도: {sensor['speed']}m/s"
        )
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError) as e:
        print("데이터 처리 오류:", e)

async def main():
    print("ESP32 검색 중...")

    device = await BleakScanner.find_device_by_name(
        DEVICE_NAME,
        timeout=15.0
    )

    if device is None:
        print("ESP32를 찾지 못했습니다.")
        return

    print("ESP32 발견:", device.address)

    async with BleakClient(device) as client:
        print("BLE 연결 성공!")

        await client.start_notify(
            CHARACTERISTIC_UUID,
            notification_handler
        )

        while True:
            await asyncio.sleep(1)

asyncio.run(main())

