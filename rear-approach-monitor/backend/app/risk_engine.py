"""
위험도 판단 엔진.

설정값(거리/속도 임계값)과 감지 데이터를 기반으로 위험도를 계산한다.
이 로직은 향후 Raspberry Pi 5의 위험도 판단 로직과 동일한 기준을 공유하도록
설계되었다 (설정값이 백엔드에 저장되고 양쪽에서 참조 가능).

⚠️ 속도 부호 규칙 주의:
mmWave 레이더(C4001 등)의 radial velocity 부호는 센서/펌웨어 설정에 따라 다르다.
따라서 이 모듈은 접근/이탈을 '임의로 확정하지 않는다'.
- 센서가 `movement` 값을 제공하면 그 값을 그대로 신뢰한다.
- `movement`가 없을 때만 아래 가정 규칙으로 보정한다 (실측 검증 필요).
"""

from __future__ import annotations

from typing import Optional

from .models import AppSettings, Movement, RiskLevel

# 속도 부호 가정 규칙 (실제 센서 연동 시 검증 필요):
#   speed < -STATIONARY_EPS  -> approaching (거리 감소)
#   speed >  STATIONARY_EPS  -> receding    (거리 증가)
#   |speed| <= STATIONARY_EPS -> stationary
STATIONARY_EPS = 0.2  # m/s


def infer_movement(
    speed: Optional[float],
    provided: Optional[Movement] = None,
) -> Movement:
    """
    이동 상태를 결정한다.

    센서가 제공한 movement가 있으면 그대로 신뢰하고,
    없을 때만 속도 부호(가정 규칙)로 보정한다.
    """
    if provided is not None:
        return provided
    if speed is None:
        return Movement.STATIONARY
    if speed < -STATIONARY_EPS:
        return Movement.APPROACHING
    if speed > STATIONARY_EPS:
        return Movement.RECEDING
    return Movement.STATIONARY


def assess_risk(
    distance: Optional[float],
    speed: Optional[float],
    movement: Movement,
    settings: AppSettings,
) -> RiskLevel:
    """
    위험도를 계산한다.

    판단 기준:
    - 멀어지거나 정지한 객체는 거리가 가까워도 위험도를 낮춘다.
    - 접근 중이고 거리가 위험 임계값 이하 -> DANGER
    - 접근 속도가 위험 속도 임계값 이상 -> DANGER 상향
    - 접근 중이고 거리가 주의 임계값 이하 -> WARNING
    - 그 외 -> SAFE
    """
    if distance is None:
        # 거리 정보가 없으면 보수적으로 SAFE (단, 접근 명시면 WARNING)
        return RiskLevel.WARNING if movement == Movement.APPROACHING else RiskLevel.SAFE

    approaching = movement == Movement.APPROACHING
    speed_abs = abs(speed) if speed is not None else 0.0

    if not approaching:
        # 멀어지거나 정지: 매우 근접(위험거리 절반)한 경우만 주의
        if distance <= settings.danger_distance_m * 0.5:
            return RiskLevel.WARNING
        return RiskLevel.SAFE

    # 접근 중
    if distance <= settings.danger_distance_m:
        return RiskLevel.DANGER
    if speed_abs >= settings.danger_speed_mps and distance <= settings.warning_distance_m:
        return RiskLevel.DANGER
    if distance <= settings.warning_distance_m:
        return RiskLevel.WARNING
    return RiskLevel.SAFE


def highest_risk(levels: list[RiskLevel]) -> RiskLevel:
    """여러 위험도 중 최고 위험도를 반환한다."""
    order = {RiskLevel.SAFE: 0, RiskLevel.WARNING: 1, RiskLevel.DANGER: 2}
    if not levels:
        return RiskLevel.SAFE
    return max(levels, key=lambda r: order[r])
