"""
장치 관리 REST API.

현재 실제 하드웨어 통신은 미구현(6단계)이다.
- 시뮬레이션 모드: 좌/우 센서 모듈과 중앙 모듈을 가상 "연결됨"으로 표시한다.
- 실제 장치 모드: 연결 확인이 안 되므로 "연결 끊김"으로 정직하게 표시한다.

실제 데이터가 없는데 연결된 것처럼 표시하지 않는다 (명세 8절).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from ..connection_manager import manager
from ..models import DataSource, DeviceStatus

router = APIRouter(prefix="/api", tags=["devices"])


@router.get("/devices", response_model=list[DeviceStatus])
def list_devices():
    """연결된 하드웨어 장치들의 상태를 반환한다."""
    sim = manager.mode == DataSource.SIMULATION
    last = manager.last_update if sim else None

    note_sim = "시뮬레이션 모드 (가상 연결)"
    note_real = "실제 장치 미연동 — 연결 확인 불가"

    return [
        DeviceStatus(
            device_id="rpi5",
            name="Raspberry Pi 5 (중앙 처리)",
            kind="central",
            connected=sim,
            battery_percent=None,  # 유선 전원 — 측정 불가
            last_seen=last,
            note=note_sim if sim else note_real,
        ),
        DeviceStatus(
            device_id="zero2w-left",
            name="좌측 Zero 2 W (감지 모듈)",
            kind="sensor_module",
            connected=sim and manager.left_connected,
            battery_percent=82 if sim else None,  # 시뮬레이션 값
            last_seen=last,
            note=note_sim if sim else note_real,
        ),
        DeviceStatus(
            device_id="zero2w-right",
            name="우측 Zero 2 W (감지 모듈)",
            kind="sensor_module",
            connected=sim and manager.right_connected,
            battery_percent=77 if sim else None,
            last_seen=last,
            note=note_sim if sim else note_real,
        ),
        DeviceStatus(
            device_id="esp32s3",
            name="XIAO ESP32-S3 (알림 모듈)",
            kind="alert_module",
            connected=sim,
            battery_percent=64 if sim else None,
            last_seen=last,
            note=note_sim if sim else note_real,
        ),
        DeviceStatus(
            device_id="cam-left",
            name="좌측 카메라 (OV5647)",
            kind="camera",
            connected=sim,
            last_seen=last,
            note="스트리밍 미연동 (7단계)" if sim else note_real,
        ),
        DeviceStatus(
            device_id="cam-right",
            name="우측 카메라 (OV5647)",
            kind="camera",
            connected=sim,
            last_seen=last,
            note="스트리밍 미연동 (7단계)" if sim else note_real,
        ),
        DeviceStatus(
            device_id="radar-left",
            name="좌측 레이더 (C4001)",
            kind="radar",
            connected=sim and manager.left_connected,
            last_seen=last,
            note=note_sim if sim else note_real,
        ),
        DeviceStatus(
            device_id="radar-right",
            name="우측 레이더 (C4001)",
            kind="radar",
            connected=sim and manager.right_connected,
            last_seen=last,
            note=note_sim if sim else note_real,
        ),
    ]
