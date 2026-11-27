
import math

# 기존 팀 프로젝트 임계값
WARNING_DISTANCE = 5.0
DANGER_DISTANCE = 2.0
DANGER_SPEED = 3.0
STATIONARY_EPS = 0.2

# 신규 TTC 임계값
WARNING_TTC = 3.0
DANGER_TTC = 1.5


def calculate_ttc(distance, speed, movement):
    # 접근 중인 객체만 TTC 계산
    if movement != "approaching":
        return math.inf

    approach_speed = abs(speed)

    if approach_speed <= STATIONARY_EPS:
        return math.inf

    return distance / approach_speed


def assess_risk(distance, speed, movement=None):

    # 비정상 센서값 확인
    if not math.isfinite(distance):
        return math.inf, "INVALID"

    if not math.isfinite(speed) or distance <= 0:
        return math.inf, "INVALID"

    # 이동 상태 판단
    # 팀 코드의 속도 부호 가정 적용
    # 음수: 접근 / 양수: 이탈
    if movement not in (
        "approaching", "receding", "stationary"
    ):
        if speed < -STATIONARY_EPS:
            movement = "approaching"
        elif speed > STATIONARY_EPS:
            movement = "receding"
        else:
            movement = "stationary"

    ttc = calculate_ttc(
        distance, speed, movement
    )

    # 정지 또는 멀어지는 객체
    if movement != "approaching":

        if distance <= DANGER_DISTANCE * 0.5:
            return ttc, "WARNING"

        return ttc, "SAFE"

    # 위험 조건
    if distance <= DANGER_DISTANCE:
        return ttc, "DANGER"

    if (
        abs(speed) >= DANGER_SPEED
        and distance <= WARNING_DISTANCE
    ):
        return ttc, "DANGER"

    if ttc <= DANGER_TTC:
        return ttc, "DANGER"

    # 주의 조건
    if distance <= WARNING_DISTANCE:
        return ttc, "WARNING"

    if ttc <= WARNING_TTC:
        return ttc, "WARNING"

    return ttc, "SAFE"


def main():

    scenarios = [
        ("먼 거리 저속 접근", 10.0, -1.0, "SAFE"),
        ("주의 거리 접근", 4.0, -1.0, "WARNING"),
        ("위험 거리 접근", 1.5, -1.0, "DANGER"),
        ("고속 접근", 4.0, -3.5, "DANGER"),
        ("TTC 기반 주의", 8.0, -3.0, "WARNING"),
        ("TTC 기반 위험", 6.0, -4.0, "DANGER"),
        ("멀어지는 객체", 3.0, 2.0, "SAFE"),
        ("정지 객체", 3.0, 0.0, "SAFE"),
        ("매우 가까운 정지 객체", 0.8, 0.0, "WARNING"),
        ("비정상 거리", -1.0, -2.0, "INVALID"),
        ("센서값 오류", float("nan"), -2.0, "INVALID"),
        ("주의 거리 경계값", 5.0, -1.0, "WARNING"),
        ("위험 거리 경계값", 2.0, -1.0, "DANGER"),
        ("주의 TTC 경계값", 9.0, -3.0, "WARNING"),
        ("위험 TTC 경계값", 9.0, -6.0, "DANGER")
    ]

    passed = 0

    print("=" * 65)
    print("거리·속도·TTC 위험도 임계값 테스트")
    print("=" * 65)

    for name, distance, speed, expected in scenarios:

        ttc, risk = assess_risk(distance, speed)

        success = risk == expected

        if success:
            passed += 1

        ttc_text = (
            f"{ttc:.2f}s"
            if math.isfinite(ttc)
            else "N/A"
        )

        print(f"\n시나리오: {name}")
        print(f"거리: {distance:.2f}m")
        print(f"상대속도: {speed:.2f}m/s")
        print(f"TTC: {ttc_text}")
        print(f"예상 위험도: {expected}")
        print(f"실제 위험도: {risk}")
        print("결과:", "PASS" if success else "FAIL")

    print("\n" + "=" * 65)
    print(f"전체 테스트: {len(scenarios)}개")
    print(f"성공: {passed}개")
    print(f"실패: {len(scenarios) - passed}개")
    print("=" * 65)


if __name__ == "__main__":
    main()
