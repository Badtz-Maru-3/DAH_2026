<div align="right">
  <a href="README.md">🇺🇸 English</a> | <strong>🇰🇷 한국어</strong>
</div>

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

Evidence 캡처는 `evidence/` 아래에 있으며 `Bridge/tools/run_evidence.sh`로 생성됩니다
(`evidence/README.md`가 정식 index). `bash Bridge/tools/run_evidence.sh`로 재생성합니다.

| Directory | Day | Focus |
| --- | --- | --- |
| `evidence/00_environment/` | — | Docker stack 상태, Bridge env vars |
| `evidence/03_manual_control/` | Day3 | MANUAL_CONTROL → /cmd_vel → odometry (bridge MVP control path) |
| `evidence/04_mission_audit/` | Day4 | Mission upload: normal accepted, malicious far/jump rejected |
| `evidence/05_gnss_integrity/` | Day5 | GPS_INPUT: normal accepted, spoof_jump / poor_fix rejected |
| `evidence/06_correlation_hold/` | Day6 | Correlation hold engaged, command blocked, hold released |

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
3. `evidence/README.md` (evidence directory index)
4. `bash Bridge/tools/run_evidence.sh`로 캡처를 재생성한 뒤 `evidence/03_manual_control/` (bridge MVP control path), `evidence/04_mission_audit/`, `evidence/05_gnss_integrity/`, `evidence/06_correlation_hold/` 순서로 확인
5. 원시 Bridge 로그 대조: `Bridge/logs/mission_audit.log`, `Bridge/logs/gnss_integrity.log`, `Bridge/logs/correlation_event.log`

## Evidence Policy

Raw evidence 파일은 보존합니다. 로그, 캡처, JSONL runtime log는 재생성 요청이 있을 때만 수정합니다. Markdown summary는 보고서 프레이밍에 맞춰 정리할 수 있습니다.
