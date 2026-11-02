"""설정 REST API."""

from __future__ import annotations

from fastapi import APIRouter

from .. import database as db
from ..models import AppSettings

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=AppSettings)
def get_settings():
    """현재 저장된 설정을 반환한다."""
    return db.get_settings()


@router.put("/settings", response_model=AppSettings)
def update_settings(settings: AppSettings):
    """
    설정을 저장한다.

    저장된 값은 백엔드 위험도 엔진이 즉시 참조하며,
    향후 Raspberry Pi 5 위험도 판단 로직과 연동될 수 있다.
    """
    db.save_settings(settings)
    return settings
