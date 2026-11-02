"""
데이터 모델 정의 (Pydantic).

프론트엔드와 공유되는 데이터 스키마의 "단일 진실 원천(single source of truth)".
TypeScript 타입(frontend/src/types)과 필드명을 일치시킨다.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enum 정의
# ---------------------------------------------------------------------------
class Module(str, Enum):
    """감지 모듈 위치 (사용자 기준 좌/우)."""

    LEFT = "left"
    RIGHT = "right"


class ObjectType(str, Enum):
    """YOLO11n으로 인식하는 객체 종류."""

    PERSON = "person"
    BICYCLE = "bicycle"
    CAR = "car"
    MOTORCYCLE = "motorcycle"
    BUS = "bus"
    TRUCK = "truck"
    UNKNOWN = "unknown"


class Movement(str, Enum):
    """객체의 상대 이동 상태."""

    APPROACHING = "approaching"  # 접근 중 (거리 감소)
    RECEDING = "receding"  # 멀어지는 중 (거리 증가)
    STATIONARY = "stationary"  # 정지


class RiskLevel(str, Enum):
    """위험도."""

    SAFE = "safe"  # 안전 (초록)
    WARNING = "warning"  # 주의 (노랑)
    DANGER = "danger"  # 위험 (빨강)


class DataSource(str, Enum):
    """데이터 출처 — 시뮬레이션 데이터와 실제 데이터를 명확히 구분한다."""

    SIMULATION = "simulation"
    DEVICE = "device"


# ---------------------------------------------------------------------------
# 감지 이벤트 (Raspberry Pi 5 → 백엔드 전송 가정 스키마)
# ---------------------------------------------------------------------------
class DetectionEvent(BaseModel):
    """
    단일 감지 이벤트.

    프로젝트 명세 7절의 JSON 구조를 기반으로 하며,
    데이터 출처(source)와 추적 ID(track_id)를 확장 필드로 추가했다.
    """

    timestamp: datetime = Field(..., description="감지 시각 (ISO8601, 타임존 포함)")
    module: Module = Field(..., description="감지 모듈 (left/right)")
    detected: bool = Field(..., description="객체 감지 여부")

    object_type: ObjectType = Field(ObjectType.UNKNOWN, description="객체 종류")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="YOLO 인식 신뢰도")

    distance: Optional[float] = Field(None, ge=0.0, description="객체와의 거리 (m)")
    # 속도 부호 규칙(가정): 음수=접근(거리감소), 양수=이탈(거리증가).
    # 실제 센서 연동 시 실측 검증 필요.
    speed: Optional[float] = Field(None, description="상대 이동 속도 (m/s)")

    movement: Movement = Field(Movement.STATIONARY, description="이동 상태")
    risk_level: RiskLevel = Field(RiskLevel.SAFE, description="위험도")

    # 확장 필드
    track_id: Optional[str] = Field(None, description="동일 객체 추적 ID (중복 알림 쿨다운용)")
    source: DataSource = Field(DataSource.SIMULATION, description="데이터 출처")


class DetectionRecord(DetectionEvent):
    """DB에 저장된 감지 기록 (id, 지속시간 포함)."""

    id: int
    duration_ms: Optional[int] = Field(None, description="이벤트 지속 시간 (ms)")


# ---------------------------------------------------------------------------
# 실시간 상태 스냅샷 (WebSocket으로 브로드캐스트)
# ---------------------------------------------------------------------------
class SystemStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    DEGRADED = "degraded"  # 일부 장치 연결 끊김


class LiveState(BaseModel):
    """대시보드/시각화를 위한 실시간 상태 스냅샷."""

    system_status: SystemStatus
    source: DataSource
    left_connected: bool
    right_connected: bool
    object_count: int
    detections: list[DetectionEvent]
    highest_risk: RiskLevel
    last_update: datetime
    server_time: datetime


# ---------------------------------------------------------------------------
# 장치 상태
# ---------------------------------------------------------------------------
class DeviceStatus(BaseModel):
    """개별 하드웨어 장치의 연결 상태."""

    device_id: str
    name: str
    kind: Literal["central", "sensor_module", "alert_module", "camera", "radar"]
    connected: bool
    battery_percent: Optional[int] = Field(
        None, ge=0, le=100, description="배터리 잔량 (측정 가능한 장치만)"
    )
    last_seen: Optional[datetime] = None
    note: Optional[str] = None  # 미구현/시뮬레이션 등 상태 설명


# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
class AppSettings(BaseModel):
    """
    위험도 판단 및 알림 설정.

    설정값은 백엔드에 저장되며, 향후 Raspberry Pi 5 위험도 판단 로직과
    연동할 수 있도록 설계되었다.
    """

    # 위험도 임계값
    danger_distance_m: float = Field(2.0, gt=0, description="위험 거리 임계값 (m)")
    warning_distance_m: float = Field(5.0, gt=0, description="주의 거리 임계값 (m)")
    danger_speed_mps: float = Field(
        3.0, gt=0, description="위험 접근 속도 임계값 (m/s, 절대값)"
    )

    # 알림
    notifications_enabled: bool = True
    sound_enabled: bool = True
    vibration_enabled: bool = True  # ESP32 진동
    led_enabled: bool = True  # ESP32 LED
    alert_cooldown_sec: float = Field(
        5.0, ge=0, description="동일 객체 중복 알림 쿨다운 (초)"
    )

    # 객체 종류별 감지 활성화
    detect_person: bool = True
    detect_bicycle: bool = True
    detect_car: bool = True
    detect_motorcycle: bool = True

    # 카메라 영상 표시
    show_camera: bool = True

    def enabled_object_types(self) -> set[str]:
        """감지 활성화된 객체 종류 집합."""
        result: set[str] = set()
        if self.detect_person:
            result.add(ObjectType.PERSON.value)
        if self.detect_bicycle:
            result.add(ObjectType.BICYCLE.value)
        if self.detect_car:
            result.add(ObjectType.CAR.value)
            result.add(ObjectType.BUS.value)
            result.add(ObjectType.TRUCK.value)
        if self.detect_motorcycle:
            result.add(ObjectType.MOTORCYCLE.value)
        return result


# ---------------------------------------------------------------------------
# 통계
# ---------------------------------------------------------------------------
class Stats(BaseModel):
    today_detections: int
    today_danger_alerts: int
    by_object_type: dict[str, int]
    by_hour: dict[str, int]  # "00".."23" -> count
    left_count: int
    right_count: int


# ---------------------------------------------------------------------------
# WebSocket 메시지 래퍼
# ---------------------------------------------------------------------------
class WsMessage(BaseModel):
    """WebSocket으로 주고받는 메시지 공통 포맷."""

    type: Literal["live_state", "alert", "device_status", "pong", "mode_changed"]
    data: dict


class ModeRequest(BaseModel):
    """동작 모드 전환 요청."""

    mode: Literal["simulation", "device"]
