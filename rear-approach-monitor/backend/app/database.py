"""
SQLite 데이터베이스 계층.

- 감지 기록 저장/조회
- 설정 저장/조회

간단한 표준 라이브러리 sqlite3를 사용한다 (별도 ORM 없이 의존성 최소화).
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from .config import DB_PATH, now_kst
from .models import AppSettings, DetectionRecord, Stats

# sqlite3 연결은 스레드 안전하지 않으므로 Lock으로 보호한다.
_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


_conn = _connect()


def init_db() -> None:
    """테이블 생성 및 기본 설정 초기화."""
    with _lock:
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                module TEXT NOT NULL,
                object_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                distance REAL,
                speed REAL,
                movement TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                track_id TEXT,
                source TEXT NOT NULL,
                duration_ms INTEGER
            );
            CREATE INDEX IF NOT EXISTS idx_detections_ts ON detections(timestamp);
            CREATE INDEX IF NOT EXISTS idx_detections_risk ON detections(risk_level);
            CREATE INDEX IF NOT EXISTS idx_detections_type ON detections(object_type);

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        _conn.commit()

    # 설정 기본값이 없으면 저장
    if get_settings_raw() is None:
        save_settings(AppSettings())


# ---------------------------------------------------------------------------
# 감지 기록
# ---------------------------------------------------------------------------
def insert_detection(event_dict: dict[str, Any], duration_ms: Optional[int] = None) -> int:
    """감지 이벤트를 기록한다. 반환: 생성된 row id."""
    with _lock:
        cur = _conn.execute(
            """
            INSERT INTO detections
            (timestamp, module, object_type, confidence, distance, speed,
             movement, risk_level, track_id, source, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _iso(event_dict["timestamp"]),
                event_dict["module"],
                event_dict["object_type"],
                event_dict["confidence"],
                event_dict.get("distance"),
                event_dict.get("speed"),
                event_dict["movement"],
                event_dict["risk_level"],
                event_dict.get("track_id"),
                event_dict["source"],
                duration_ms,
            ),
        )
        _conn.commit()
        return int(cur.lastrowid)


def query_detections(
    date: Optional[str] = None,
    object_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    limit: int = 200,
) -> list[DetectionRecord]:
    """
    감지 기록 조회. 날짜(YYYY-MM-DD) / 객체 종류 / 위험도로 필터링한다.
    """
    clauses: list[str] = []
    params: list[Any] = []

    if date:
        clauses.append("substr(timestamp, 1, 10) = ?")
        params.append(date)
    if object_type:
        clauses.append("object_type = ?")
        params.append(object_type)
    if risk_level:
        clauses.append("risk_level = ?")
        params.append(risk_level)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM detections {where} ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with _lock:
        rows = _conn.execute(sql, params).fetchall()

    return [_row_to_record(r) for r in rows]


def compute_stats() -> Stats:
    """오늘(KST 날짜) 기준 통계를 계산한다. 저장 타임스탬프와 날짜 경계를 일치시킨다."""
    today = now_kst().strftime("%Y-%m-%d")
    with _lock:
        total = _conn.execute(
            "SELECT COUNT(*) AS c FROM detections WHERE substr(timestamp,1,10)=?",
            (today,),
        ).fetchone()["c"]

        danger = _conn.execute(
            "SELECT COUNT(*) AS c FROM detections "
            "WHERE substr(timestamp,1,10)=? AND risk_level='danger'",
            (today,),
        ).fetchone()["c"]

        type_rows = _conn.execute(
            "SELECT object_type, COUNT(*) AS c FROM detections "
            "WHERE substr(timestamp,1,10)=? GROUP BY object_type",
            (today,),
        ).fetchall()

        hour_rows = _conn.execute(
            "SELECT substr(timestamp,12,2) AS h, COUNT(*) AS c FROM detections "
            "WHERE substr(timestamp,1,10)=? GROUP BY h",
            (today,),
        ).fetchall()

        left = _conn.execute(
            "SELECT COUNT(*) AS c FROM detections "
            "WHERE substr(timestamp,1,10)=? AND module='left'",
            (today,),
        ).fetchone()["c"]

        right = _conn.execute(
            "SELECT COUNT(*) AS c FROM detections "
            "WHERE substr(timestamp,1,10)=? AND module='right'",
            (today,),
        ).fetchone()["c"]

    by_hour = {f"{h:02d}": 0 for h in range(24)}
    for r in hour_rows:
        by_hour[r["h"]] = r["c"]

    return Stats(
        today_detections=total,
        today_danger_alerts=danger,
        by_object_type={r["object_type"]: r["c"] for r in type_rows},
        by_hour=by_hour,
        left_count=left,
        right_count=right,
    )


# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------
def get_settings_raw() -> Optional[str]:
    with _lock:
        row = _conn.execute(
            "SELECT value FROM settings WHERE key='app'"
        ).fetchone()
    return row["value"] if row else None


def get_settings() -> AppSettings:
    raw = get_settings_raw()
    if raw is None:
        return AppSettings()
    return AppSettings.model_validate_json(raw)


def save_settings(settings: AppSettings) -> None:
    with _lock:
        _conn.execute(
            "INSERT INTO settings(key, value) VALUES('app', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (settings.model_dump_json(),),
        )
        _conn.commit()


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------
def _iso(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _row_to_record(r: sqlite3.Row) -> DetectionRecord:
    return DetectionRecord(
        id=r["id"],
        timestamp=datetime.fromisoformat(r["timestamp"]),
        module=r["module"],
        detected=True,
        object_type=r["object_type"],
        confidence=r["confidence"],
        distance=r["distance"],
        speed=r["speed"],
        movement=r["movement"],
        risk_level=r["risk_level"],
        track_id=r["track_id"],
        source=r["source"],
        duration_ms=r["duration_ms"],
    )
