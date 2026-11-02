"""
WebSocket 연결 관리 및 실시간 상태 브로드캐스트.

- 여러 클라이언트 연결을 관리한다.
- 주기적으로 시뮬레이터를 진행시켜 LiveState를 브로드캐스트한다.
- 위험(DANGER) 이벤트 발생 시 쿨다운을 적용해 alert 메시지를 전송한다.
- 감지 이벤트를 DB에 기록한다.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime

from typing import Optional

from fastapi import WebSocket

from . import database as db
from . import risk_engine
from .config import config, now_kst
from .models import (
    DataSource,
    DetectionEvent,
    LiveState,
    RiskLevel,
    SystemStatus,
)
from .simulator import Simulator

# track이 이 시간(초) 동안 갱신되지 않으면 소멸한 것으로 보고 기록을 확정한다.
TRACK_EXPIRE_SEC = 1.5


def _json_default(o):
    if isinstance(o, datetime):
        return o.isoformat()
    return str(o)


@dataclass
class TrackState:
    """
    진행 중인 하나의 감지 대상(track)의 누적 상태.

    감지 기록을 '스냅샷마다'가 아니라 'track 1건'으로 저장하기 위해
    track의 생명주기 동안 최고 위험도/최근 스냅샷/최초·최종 시각을 누적한다.
    track이 소멸할 때 단 하나의 요약 레코드를 DB에 기록한다.
    """

    track_id: str
    first_seen: float  # epoch 초
    last_seen: float
    peak_risk: RiskLevel
    alerted: bool = False  # 이 track에 대해 위험 알림을 이미 보냈는지
    # 최고 위험도에 도달한 시점의 대표 스냅샷 (기록 저장용)
    representative: Optional[DetectionEvent] = None
    history: list[DetectionEvent] = field(default_factory=list)


class Manager:
    """애플리케이션 전역 실시간 상태 관리자."""

    def __init__(self) -> None:
        self.active: set[WebSocket] = set()
        self.simulator = Simulator()
        self.mode: DataSource = DataSource.SIMULATION  # 기본: 시뮬레이션
        self.last_update: datetime = now_kst()
        self.left_connected = False
        self.right_connected = False

        # 쿨다운: track_id -> 마지막 알림 시각(epoch 초)
        self._alert_cooldown: dict[str, float] = {}
        # 진행 중인 track 상태: track_id -> TrackState
        self._tracks: dict[str, TrackState] = {}
        self._broadcast_task: Optional[asyncio.Task] = None

    # -- 연결 관리 ----------------------------------------------------------
    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.add(ws)
        # 접속 즉시 현재 상태 1회 전송
        await self._send(ws, "live_state", self.build_live_state().model_dump())

    def disconnect(self, ws: WebSocket) -> None:
        self.active.discard(ws)

    async def _send(self, ws: WebSocket, msg_type: str, data: dict) -> None:
        try:
            await ws.send_text(
                json.dumps({"type": msg_type, "data": data}, default=_json_default)
            )
        except Exception:
            self.disconnect(ws)

    async def broadcast(self, msg_type: str, data: dict) -> None:
        dead: list[WebSocket] = []
        payload = json.dumps({"type": msg_type, "data": data}, default=_json_default)
        for ws in list(self.active):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    # -- 모드 전환 ----------------------------------------------------------
    async def set_mode(self, mode: DataSource) -> None:
        self.mode = mode
        if mode == DataSource.SIMULATION:
            self.simulator.running = True
        else:
            # 실제 장치 모드: 아직 실제 연동 미구현.
            # 실제 데이터가 없으므로 연결된 것처럼 표시하지 않는다.
            self.simulator.running = False
            self.simulator.objects.clear()
            self.left_connected = False
            self.right_connected = False
            # 진행 중이던 track/쿨다운 상태 정리 (시뮬 데이터가 실제로 넘어오지 않도록)
            self._tracks.clear()
            self._alert_cooldown.clear()
        await self.broadcast("mode_changed", {"mode": mode.value})

    # -- 실시간 루프 --------------------------------------------------------
    def start(self) -> None:
        if self._broadcast_task is None:
            self._broadcast_task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._broadcast_task:
            self._broadcast_task.cancel()
            self._broadcast_task = None

    async def _loop(self) -> None:
        interval = config.broadcast_interval_sec
        while True:
            try:
                await self._step(interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:  # 루프가 죽지 않도록 방어
                print(f"[manager] loop error: {exc}")
            await asyncio.sleep(interval)

    async def _step(self, dt: float) -> None:
        now = now_kst()
        now_epoch = now.timestamp()

        if self.mode == DataSource.SIMULATION:
            events = self.simulator.tick(dt)
            # 시뮬레이션 모드에서는 좌/우 모듈이 가상으로 "연결됨"
            self.left_connected = True
            self.right_connected = True
        else:
            # 실제 장치 모드 — 미연동. 실제 데이터 없음.
            events = []

        settings = db.get_settings()
        enabled_types = settings.enabled_object_types()

        processed: list[DetectionEvent] = []
        seen_ids: set[str] = set()

        for ev in events:
            # 설정에서 비활성화된 객체 종류는 제외
            if ev.object_type.value not in enabled_types:
                continue

            # 위험도 재계산 (백엔드 엔진이 최종 판단)
            ev.movement = risk_engine.infer_movement(ev.speed, ev.movement)
            ev.risk_level = risk_engine.assess_risk(
                ev.distance, ev.speed, ev.movement, settings
            )
            processed.append(ev)

            # track 상태 누적
            if ev.track_id:
                seen_ids.add(ev.track_id)
                self._update_track(ev, now_epoch)

            # 위험 이벤트 알림 (쿨다운 적용)
            if ev.risk_level == RiskLevel.DANGER and settings.notifications_enabled:
                await self._maybe_alert(ev, now_epoch, settings)

        self.last_update = now if processed else self.last_update

        # 더 이상 감지되지 않는 track을 확정(소멸) 처리하고 요약 1건을 기록
        self._expire_tracks(seen_ids, now_epoch)

        state = self.build_live_state(processed)
        await self.broadcast("live_state", state.model_dump())

    def _update_track(self, ev: DetectionEvent, now_epoch: float) -> None:
        """현재 틱의 이벤트로 track 누적 상태를 갱신한다."""
        t = self._tracks.get(ev.track_id)  # type: ignore[arg-type]
        if t is None:
            t = TrackState(
                track_id=ev.track_id,  # type: ignore[arg-type]
                first_seen=now_epoch,
                last_seen=now_epoch,
                peak_risk=ev.risk_level,
                representative=ev,
            )
            self._tracks[ev.track_id] = t  # type: ignore[index]
            return

        t.last_seen = now_epoch
        # 최고 위험도 갱신 + 그 시점 스냅샷을 대표로 보관
        if risk_engine.highest_risk([t.peak_risk, ev.risk_level]) != t.peak_risk:
            t.peak_risk = ev.risk_level
            t.representative = ev
        elif t.peak_risk == ev.risk_level:
            # 같은 최고 위험도면 최신(가장 가까운) 스냅샷을 대표로
            t.representative = ev

    def _expire_tracks(self, seen_ids: set[str], now_epoch: float) -> None:
        """
        이번 틱에 감지되지 않고 만료 시간이 지난 track을 확정한다.
        확정 시: 지속시간/최고위험도를 담은 요약 레코드 1건을 기록한다.
        (WARNING 이상 도달한 track만 기록해 노이즈를 줄인다.)
        """
        expired: list[str] = []
        for tid, t in self._tracks.items():
            if tid in seen_ids:
                continue
            if now_epoch - t.last_seen < TRACK_EXPIRE_SEC:
                continue
            expired.append(tid)

            if t.representative and t.peak_risk in (
                RiskLevel.WARNING,
                RiskLevel.DANGER,
            ):
                duration_ms = int((t.last_seen - t.first_seen) * 1000)
                rec = t.representative.model_copy()
                rec.risk_level = t.peak_risk  # 생애 최고 위험도로 기록
                db.insert_detection(rec.model_dump(mode="json"), duration_ms=duration_ms)

        for tid in expired:
            self._tracks.pop(tid, None)
            self._alert_cooldown.pop(tid, None)

    async def _maybe_alert(
        self, ev: DetectionEvent, now_epoch: float, settings
    ) -> None:
        """동일 객체에 대한 중복 알림을 쿨다운으로 억제한다 (명세 3.4)."""
        key = ev.track_id or f"{ev.module.value}:{ev.object_type.value}"
        last = self._alert_cooldown.get(key, 0.0)
        if now_epoch - last < settings.alert_cooldown_sec:
            return
        self._alert_cooldown[key] = now_epoch
        if ev.track_id and ev.track_id in self._tracks:
            self._tracks[ev.track_id].alerted = True
        await self.broadcast("alert", ev.model_dump())

    # -- 상태 스냅샷 --------------------------------------------------------
    def build_live_state(
        self, detections: Optional[list[DetectionEvent]] = None
    ) -> LiveState:
        dets = detections if detections is not None else []
        risks = [d.risk_level for d in dets]
        highest = risk_engine.highest_risk(risks)

        now = now_kst()
        stale = (now - self.last_update).total_seconds() > config.stale_timeout_sec

        if self.mode == DataSource.DEVICE and not (
            self.left_connected or self.right_connected
        ):
            status = SystemStatus.STOPPED
        elif stale or not (self.left_connected and self.right_connected):
            status = SystemStatus.DEGRADED
        else:
            status = SystemStatus.RUNNING

        return LiveState(
            system_status=status,
            source=self.mode,
            left_connected=self.left_connected,
            right_connected=self.right_connected,
            object_count=len(dets),
            detections=dets,
            highest_risk=highest,
            last_update=self.last_update,
            server_time=now,
        )


manager = Manager()
