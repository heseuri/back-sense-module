"""감지 기록 및 통계 REST API."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from .. import database as db
from ..models import DetectionRecord, Stats

router = APIRouter(prefix="/api", tags=["detections"])


@router.get("/detections", response_model=list[DetectionRecord])
def list_detections(
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    object_type: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    limit: int = Query(200, le=1000),
):
    """감지 기록을 날짜/객체종류/위험도로 필터링해 조회한다."""
    return db.query_detections(
        date=date, object_type=object_type, risk_level=risk_level, limit=limit
    )


@router.get("/stats", response_model=Stats)
def get_stats():
    """오늘 기준 감지 통계."""
    return db.compute_stats()
