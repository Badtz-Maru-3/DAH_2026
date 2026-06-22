# DAH 2026 Evidence

원본: `docs/README.md`

이 디렉터리는 DAH 2026 software-defined UGV/GCS cybersecurity testbed의 일자별 evidence를 보관합니다.

Evidence는 Logical Two-Layer Testbed Architecture 기준으로 읽어야 합니다. Simulation Layer는 QGroundControl, Gazebo/ROSbot, RViz, odometry feedback을 제공하고, Software-Defined UGV Security Layer는 bridge, mission audit, GNSS integrity, correlation, command hold/block behavior를 제공합니다.

## Evidence가 답해야 하는 질문

- 어떤 container가 실행 중이었는가?
- 어떤 ROS2 topic과 node가 보였는가?
- 예상한 control 또는 visualization 동작이 실제로 발생했는가?
- attack 또는 abnormal input injection point는 어디인가?
- detection, blocking, recovery 또는 remaining gap을 증명하는 log/topic/telemetry record는 무엇인가?

## Index

| Day | Focus | Status |
| --- | --- | --- |
| `day1/` | ROSbot Gazebo simulation baseline | container, ROS2 topic, simulation log captured |
| `day2/` | QGC, Gazebo, RViz noVNC web UI stack | service log 및 ROS2 topic state captured |
| `day3/` | ROS2-MAVLink bridge MVP | QGC-to-ROSbot control evidence captured |
| `day4/` | Mission audit mode | normal mission accepted, malicious mission rejected evidence captured |
| `day5/` | GNSS integrity adapter | normal GPS_INPUT accepted, spoof/poor-fix rejected evidence captured |
| `day6/` | Correlation engine | hold engagement 및 MANUAL_CONTROL blocking evidence captured |

## Day 역할

| Day | 최종 계획에서의 역할 |
| --- | --- |
| Day1 | known-good simulation과 ROS2 topic baseline을 세웁니다. |
| Day2 | operator-facing UI와 visualization layer를 세웁니다. |
| Day3 | 첫 active command path를 검증합니다. |
| Day4 | normal/malicious mission upload audit를 검증합니다. |
| Day5 | normal/spoof/poor-fix GNSS input validation을 검증합니다. |
| Day6 | mission/GNSS rejection 이후 hold 및 command block response를 검증합니다. |

## Evidence Model

각 attack surface는 가능하면 다음 4-tuple로 정리합니다.

| Item | Meaning |
| --- | --- |
| Injection point | attack 또는 abnormal input이 들어오는 지점 |
| Symptom | 비정상 command, mission, position, telemetry 증상 |
| Response | defense logic이 탐지, 차단, rollback, recovery한 내용 |
| Log proof | event와 response를 증명하는 파일 |

## Reading Order

1. root `README_KR.md`
2. `architecture/two_layer_architecture_KR.md`
3. `day1/README_KR.md`
4. `day2/README_KR.md`
5. `day3/README_KR.md`
6. `day3/evidence_summary_KR.md`
7. `day4/README_KR.md`
8. `day5/README_KR.md`
9. `day6/README_KR.md`

## Evidence Policy

Raw evidence 파일은 보존합니다. 로그, 캡처, JSONL runtime log는 재생성 요청이 있을 때만 수정합니다. Markdown summary는 보고서 프레이밍에 맞춰 정리할 수 있습니다.
