"""
시뮬레이션 데이터 생성기.

실제 하드웨어가 없어도 애플리케이션을 테스트할 수 있도록
가상의 후방 접근 시나리오를 생성한다.

핵심 원칙:
- 생성되는 모든 데이터는 source="simulation" 으로 명확히 표시된다.
- 거리/속도는 물리적으로 일관되게 변한다 (접근 객체는 거리가 줄고 속도는 음수).
- track_id를 부여해 동일 객체 추적 및 중복 알림 쿨다운을 지원한다.
"""

from __future__ import annotations

import random
import uuid
from typing import Optional

from .config import now_kst
from .models import (
    DataSource,
    DetectionEvent,
    Module,
    Movement,
    ObjectType,
)

# 객체 종류별 전형적인 접근 속도 범위 (m/s, 절대값)
_SPEED_PROFILE = {
    ObjectType.PERSON: (0.8, 1.6),
    ObjectType.BICYCLE: (2.0, 5.0),
    ObjectType.MOTORCYCLE: (5.0, 12.0),
    ObjectType.CAR: (6.0, 15.0),
}


class VirtualObject:
    """
    가상의 접근 객체.

    하나의 객체는 생성 시점의 거리에서 시작해 설정된 속도로 접근/이탈하며,
    거리가 범위를 벗어나면 소멸한다.
    """

    def __init__(self) -> None:
        self.track_id = str(uuid.uuid4())[:8]
        self.module = random.choice([Module.LEFT, Module.RIGHT])
        self.object_type = random.choice(list(_SPEED_PROFILE.keys()))

        # 시나리오: 대부분 접근, 일부는 이탈/정지
        self.scenario = random.choices(
            ["approaching", "receding", "stationary"],
            weights=[0.7, 0.2, 0.1],
        )[0]

        lo, hi = _SPEED_PROFILE[self.object_type]
        self.speed_abs = random.uniform(lo, hi)

        if self.scenario == "approaching":
            self.distance = random.uniform(8.0, 15.0)  # 멀리서 시작
        elif self.scenario == "receding":
            self.distance = random.uniform(1.5, 4.0)  # 가까이서 시작해 멀어짐
        else:  # stationary
            self.distance = random.uniform(3.0, 8.0)
            self.speed_abs = random.uniform(0.0, 0.15)

        self.confidence = random.uniform(0.6, 0.98)
        self.alive = True

    def step(self, dt: float) -> None:
        """dt(초)만큼 시간 진행 — 거리를 갱신한다."""
        if self.scenario == "approaching":
            self.distance -= self.speed_abs * dt
            if self.distance <= 0.3:
                self.alive = False  # 지나감
        elif self.scenario == "receding":
            self.distance += self.speed_abs * dt
            if self.distance >= 15.0:
                self.alive = False  # 시야 밖
        # stationary: 거리 거의 변화 없음 (약간의 노이즈)
        else:
            self.distance += random.uniform(-0.05, 0.05)

        self.confidence = max(0.5, min(0.99, self.confidence + random.uniform(-0.03, 0.03)))

    @property
    def movement(self) -> Movement:
        if self.scenario == "approaching":
            return Movement.APPROACHING
        if self.scenario == "receding":
            return Movement.RECEDING
        return Movement.STATIONARY

    @property
    def signed_speed(self) -> float:
        """
        속도 부호 규칙(가정): 접근=음수, 이탈=양수.
        실제 센서 연동 시 검증 필요.
        """
        if self.scenario == "approaching":
            return -round(self.speed_abs, 2)
        if self.scenario == "receding":
            return round(self.speed_abs, 2)
        return 0.0

    def to_event(self) -> DetectionEvent:
        """현재 상태를 DetectionEvent로 변환 (risk_level은 엔진에서 채움)."""
        return DetectionEvent(
            timestamp=now_kst(),
            module=self.module,
            detected=True,
            object_type=self.object_type,
            confidence=round(self.confidence, 2),
            distance=round(max(0.0, self.distance), 2),
            speed=self.signed_speed,
            movement=self.movement,
            track_id=self.track_id,
            source=DataSource.SIMULATION,
        )


class Simulator:
    """
    여러 가상 객체를 관리하며 주기적으로 상태를 진행시킨다.
    """

    def __init__(self, max_objects: int = 4) -> None:
        self.max_objects = max_objects
        self.objects: list[VirtualObject] = []
        self.running = True

    def tick(self, dt: float) -> list[DetectionEvent]:
        """
        한 틱(dt초) 진행 후 현재 살아있는 객체들의 이벤트 목록을 반환한다.
        """
        if not self.running:
            return []

        # 기존 객체 진행
        for obj in self.objects:
            obj.step(dt)
        self.objects = [o for o in self.objects if o.alive]

        # 확률적으로 새 객체 생성
        if len(self.objects) < self.max_objects and random.random() < 0.15:
            self.objects.append(VirtualObject())

        return [o.to_event() for o in self.objects]

    def trigger_scenario(self, scenario: str) -> None:
        """
        특정 테스트 시나리오를 강제로 생성한다 (알림/위험도 테스트용).
        scenario: "danger_left" | "danger_right" | "clear"
        """
        if scenario == "clear":
            self.objects.clear()
            return

        obj = VirtualObject()
        obj.scenario = "approaching"
        obj.module = Module.LEFT if scenario == "danger_left" else Module.RIGHT
        obj.object_type = ObjectType.CAR
        obj.distance = random.uniform(2.5, 4.0)
        obj.speed_abs = random.uniform(6.0, 10.0)
        obj.confidence = 0.95
        self.objects.append(obj)
