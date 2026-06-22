<div align="right">
  <a href="../AGENTS.md">🇺🇸 English</a> | <strong>🇰🇷 한국어</strong>
</div>

# AGENTS.md 한국어 참고 요약

원본 실행 지침: `AGENTS.md`

이 파일은 한국어 참고용 요약입니다. 에이전트 실행 지침의 기준은 항상 `AGENTS.md`입니다.

## Project Context

이 저장소는 DAH 2026 Defense AI Cyber Security Hackathon 예선용 **software-defined UGV/GCS cybersecurity testbed**입니다.

이 testbed는 실제 군용 UGV 플랫폼의 복제물이 아닙니다. 다음 운용 흐름을 소프트웨어 계층에서 추상화합니다.

- GCS control
- MAVLink-based command and telemetry flow
- Mission upload validation
- GNSS/location input validation
- Anomaly correlation
- Command hold/block response

권장 표현:

```text
Defense UGV-inspired software-defined UGV/GCS cybersecurity testbed.
```

피해야 할 표현:

- real military UGV replica
- military-grade platform
- RF-layer system
- physical GNSS receiver integration

## Logical Architecture

```text
[Simulation Layer]
QGC 화면 / Gazebo / RViz / ROSbot 이동 / odometry

[Software-Defined UGV Security Layer]
MAVLink Bridge
Mission Audit
GNSS Integrity
Correlation Engine
Command Hold / Block
```

이 구조는 물리적으로 격리된 network architecture가 아니라 logical architecture입니다.

## Implemented Flows

```text
Day3:
QGC joystick
-> MAVLink MANUAL_CONTROL
-> Bridge
-> ROS2 /cmd_vel
-> ROSbot movement
-> /odometry/filtered telemetry

Day4:
Mission upload
-> Mission Audit
-> geofence / waypoint jump validation
-> MISSION_ACK accepted or rejected

Day5:
GPS_INPUT
-> GNSS Integrity
-> normal / spoof_jump / poor_fix classification

Day6:
Mission/GNSS/Command anomaly signal
-> Correlation Engine
-> risk score
-> hold_engaged
-> command_blocked
```

이 상태는 source code나 logs가 확인하기 전에는 임의로 바꾸지 않습니다.

## Safety and Scope

명시 요청 없이는 destructive operation을 수행하지 않습니다.

금지 예:

```bash
rm -rf
docker system prune
git reset --hard
git clean -fd
sudo rm -rf
force push
```

Evidence log, screenshot, captured terminal output은 재생성 요청이 있을 때만 수정합니다.

## Documentation Guidelines

선호 표현:

- software-defined UGV/GCS cybersecurity testbed
- Logical Two-Layer Testbed Architecture
- Simulation Layer
- Software-Defined UGV Security Layer
- defense UGV-inspired
- UGV/GCS cybersecurity validation
- software-layer abstraction
- ROSbot-based surrogate platform

Architecture documentation 순서:

1. Defense UGV operational risk
2. Simulated testbed abstraction
3. Two-layer architecture
4. Attack surface
5. Defense module
6. Evidence logs
7. Limitations

## Markdown Work Rules

Markdown 문서 수정 시:

- 기존 Markdown을 먼저 확인합니다.
- project-owned Markdown만 수정합니다.
- third-party/vendor Markdown은 수정하지 않습니다.
- evidence values를 보존합니다.
- raw logs, screenshots, JSONL evidence는 건드리지 않습니다.
- 필요한 경우 cross-link를 추가합니다.

Documentation-only 작업의 기대 결과:

```text
Only .md files should be modified or added.
```

## Reporting Style

보고서 문체는 formal but clear가 좋습니다.

권장 표현:

- This testbed validates...
- The prototype demonstrates...
- The software-defined layer detects...
- The simulated environment abstracts...

피해야 할 표현:

- This completely protects...
- This guarantees...
- This is a real military UGV...
- This perfectly reproduces...

중요 기술 주장은 source code, runtime log, screenshot, documented test result, official external reference 중 하나로 뒷받침해야 합니다.
