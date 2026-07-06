# demo/ — 리포트 §6 부록 라이브 데모 스크립트

이 디렉터리의 5개 파일은 `DAH_REPORT_ver_1.7.pdf` §6.2.1 ~ §6.2.5에 bash heredoc
형태로 삽입되어 있던 스크립트를 **원문 그대로(verbatim)** 저장소로 옮긴 것이다.

| 파일 | 리포트 위치 | 시나리오 |
| --- | --- | --- |
| `hijack_nav.py` | §6.2.1 | A 공격 — odometry 기반 폐루프 유도 탈취 데모 |
| `kill_switch_sentinel.py` | §6.2.2 | A 방어 — `/cmd_vel` 능동 감시·차단 데모 |
| `spoof_scan.py` | §6.2.3 | B 공격 — 가짜 LaserScan 주입 데모 |
| `scan_sentinel_secure.py` | §6.2.4 | B 방어 — `/scan` 싱크홀·정화 데모 |
| `mavlink_sentinel.py` | §6.2.5 | C 방어 — MAVLink 프록시 방화벽 데모 |

## 중요 — 이 스크립트들의 성격

- **thresholds는 의도적으로 원문 그대로 두었다.** 임의로 정합화하지 않았다.
  - `kill_switch_sentinel.py`: `MAX_LINEAR=0.5`, `MAX_ANGULAR=1.2`,
    `TIMEOUT_DURATION=15.0`, 2000Hz(0.0005s) 무효화 루프 — 이 값들은
    `.env.example`/`Bridge/ros2_mavlink_bridge.py`의 실제 값과 우연히 일치한다.
  - `mavlink_sentinel.py`: `MAX_GPS_JUMP=100.0`, `MAX_GEOFENCE_RADIUS=300.0` —
    geofence 반경은 **실제 `Bridge`의 `MISSION_GEOFENCE_RADIUS_M=300` 및 리포트
    §4.1.4 표(geofence 300m)와 정합**하도록 맞춰져 있다(코드 주석에도 그렇게
    명시되어 있다). 반면 `MAX_GPS_JUMP=100.0`은 데모용 GPS 점프 임계값으로, 리포트의
    mission waypoint jump 값(120m)이나 Bridge GNSS residual 검사
    (`GNSS_MAX_RESIDUAL_M=30`)와는 다른 별개의 illustrative 수치다. `agents/defense/`
    계층의 correlation threshold(hold 0.5 / block 0.8)는 또 다른 scoring 계층의
    값이라 위 두 수치와 직접 비교 대상이 아니다.
- **이 스크립트들은 `agents/` 오케스트레이션의 일부가 아니다.** `agents/attack/`,
  `agents/defense/`와 이름·구조·클래스가 겹치지 않는 완전히 별개의 단일 파일
  ROS2/MAVLink 노드다. `agents/main_orchestrator.py`는 이 파일들을 import하거나
  호출하지 않는다.
- **저장소에 커밋된 적이 없던 코드다.** 리포트 원문은 `cat > file <<'EOF' ... EOF`
  형태의 라이브 터미널 데모로 제시되어 있었고, 실행 후 파일이 남는 위치도
  스크립트마다 다르다(`/tmp/kill_switch_sentinel.py`, `/tmp/scan_sentinel_secure.py`
  는 `/tmp/`에, 나머지 3개는 현재 작업 디렉터리에 쓰도록 되어 있었다). 이번 작업은
  그 heredoc 본문만 추출하여 `demo/`에 고정한 것이며, 실행 경로나 동작을 새로
  검증한 것은 아니다.
- PDF에서 텍스트를 추출하는 과정에서 공백 간격이 다단으로 벌어지는 layout 손상과
  이모지/특수기호 깨짐(mojibake)이 있었다. 코드의 값·로직·제어 흐름은 그대로 두고
  들여쓰기·공백·깨진 기호만 정규화했다. `mavlink_sentinel.py`의 `if`/`elif` 블록은
  추출 과정에서 들여쓰기가 어긋나 있어 `while True:` 블록 바로 아래 동일 들여쓰기로
  맞췄다(로직 변경 없음, 블록 정렬만 수정).

## 실행 방법 (원문 그대로)

리포트가 제시한 실행 방법을 그대로 옮기면 다음과 같다. 이 저장소에서 실제로
재검증하지는 않았다.

```bash
python3 demo/hijack_nav.py
python3 demo/kill_switch_sentinel.py
python3 demo/spoof_scan.py
python3 demo/scan_sentinel_secure.py
python3 demo/mavlink_sentinel.py
```

각 파일은 `python3 -m py_compile`을 통과하는 것만 확인했다. `rclpy`/`pymavlink`
등 실제 런타임 의존성이 있는 노드로서의 동작(ROS2 그래프 참여, MAVLink 포트
바인딩 등)은 검증하지 않았다.
