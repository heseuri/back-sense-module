"""애플리케이션 설정 및 런타임 상태."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "monitor.db"

# 프로젝트 명세 7절의 타임스탬프 예시가 +09:00(KST)이므로,
# 저장/통계/표시의 날짜 경계를 KST로 통일한다.
# (UTC 저장 시 통계의 "오늘" 경계가 로컬 날짜와 어긋나는 문제를 방지.)
KST = timezone(timedelta(hours=9))


def now_kst() -> datetime:
    """현재 시각을 KST(+09:00) 타임존 정보를 포함해 반환한다."""
    return datetime.now(KST)


class ServerConfig(BaseSettings):
    """환경 변수로 덮어쓸 수 있는 서버 설정."""

    model_config = SettingsConfigDict(env_prefix="RAM_", env_file=".env")

    # CORS 허용 오리진 (프론트엔드 개발 서버)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 실시간 상태 브로드캐스트 주기 (초)
    broadcast_interval_sec: float = 0.5

    # 데이터가 이 시간(초) 이상 수신되지 않으면 연결 끊김으로 간주
    stale_timeout_sec: float = 3.0

    # Raspberry Pi 5 실제 장치 API 주소 (6단계에서 사용 — 현재 미연동)
    device_api_base: str = "http://raspberrypi5.local:8080"

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


config = ServerConfig()
