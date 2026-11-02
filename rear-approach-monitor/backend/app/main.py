"""
FastAPI 진입점.

- REST API: /api/*
- WebSocket: /ws/stream (실시간 LiveState + alert 브로드캐스트)
- 동작 모드 전환 및 테스트 시나리오 트리거 API

실행:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from . import database as db
from .config import config
from .connection_manager import manager
from .models import DataSource, ModeRequest
from .routers import detections, devices, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시: DB 초기화 + 실시간 브로드캐스트 루프 시작
    db.init_db()
    manager.start()
    yield
    # 종료 시: 루프 정리
    await manager.stop()


app = FastAPI(
    title="후방 접근 감지 모니터링 API",
    version="0.3.0",
    description="1~3단계 구현: 구조/대시보드/시각화/시뮬레이션+WebSocket",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # 개발 중에는 PC/폰 등 LAN의 임의 오리진(localhost, 192.168.x.x 등)을 허용한다.
    # 운영 배포 시에는 config.cors_origin_list()의 명시 목록으로 제한할 것.
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|(\d{1,3}\.){3}\d{1,3})(:\d+)?",
    allow_origins=config.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST 라우터 등록
app.include_router(detections.router)
app.include_router(settings.router)
app.include_router(devices.router)


@app.get("/api/health")
def health():
    """헬스 체크 및 현재 모드 확인."""
    return {"status": "ok", "mode": manager.mode.value}


@app.get("/api/mode")
def get_mode():
    return {"mode": manager.mode.value}


@app.post("/api/mode")
async def set_mode(req: ModeRequest):
    """
    동작 모드 전환.
    - simulation: 시뮬레이션 데이터 생성
    - device: 실제 장치 모드 (현재 미연동 — 데이터 없음)
    """
    mode = DataSource.SIMULATION if req.mode == "simulation" else DataSource.DEVICE
    await manager.set_mode(mode)
    return {"mode": manager.mode.value}


@app.post("/api/simulate/{scenario}")
async def trigger_scenario(scenario: str):
    """
    테스트 시나리오 강제 트리거 (알림/위험도 테스트용).
    scenario: danger_left | danger_right | clear
    """
    if manager.mode != DataSource.SIMULATION:
        return {"ok": False, "reason": "시뮬레이션 모드에서만 사용 가능합니다."}
    manager.simulator.trigger_scenario(scenario)
    return {"ok": True, "scenario": scenario}


@app.websocket("/ws/stream")
async def ws_stream(ws: WebSocket):
    """
    실시간 스트림 WebSocket.
    - 서버 -> 클라이언트: live_state, alert, device_status, mode_changed
    - 클라이언트 -> 서버: {"type": "ping"} (연결 유지), {"type":"set_mode","mode":...}
    """
    await manager.connect(ws)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            mtype = msg.get("type")
            if mtype == "ping":
                await ws.send_text(json.dumps({"type": "pong", "data": {}}))
            elif mtype == "set_mode":
                mode = (
                    DataSource.SIMULATION
                    if msg.get("mode") == "simulation"
                    else DataSource.DEVICE
                )
                await manager.set_mode(mode)
    except WebSocketDisconnect:
        manager.disconnect(ws)
    except Exception:
        manager.disconnect(ws)
