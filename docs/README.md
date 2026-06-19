# DAH 2026 Evidence

This directory stores day-by-day evidence for the DAH 2026 Docker unmanned-systems cyber-defense testbed.

The evidence is meant to answer five questions:

- Which containers were running?
- Which ROS2 topics and nodes were visible?
- Did the expected control or visualization behavior actually happen?
- Where is the attack or abnormal-input injection point?
- What log, topic, or telemetry record proves detection, blocking, recovery, or the remaining gap?

## Index

| Day | Focus | Status |
| --- | --- | --- |
| `day1/` | ROSbot Gazebo simulation baseline. | Captured container, ROS2 topic, and simulation logs. |
| `day2/` | Web UI stack with QGroundControl, Gazebo, and RViz through noVNC. | Captured service logs and ROS2 topic state. |
| `day3/` | ROS2-MAVLink bridge MVP. | Captured end-to-end QGC-to-ROSbot control evidence. |

## Day Roles

The day folders are cumulative rather than independent.

| Day | Role in the final plan |
| --- | --- |
| Day1 | Establishes a known-good simulation and ROS2 topic baseline. Later attack evidence should be compared against this normal state. |
| Day2 | Establishes the operator and visualization layer. Future mission upload, alert, and screenshot evidence should be captured through this layer. |
| Day3 | Establishes the first active command path. Future C2-style command injection, blocking, and recovery experiments should preserve this baseline path. |

## Evidence Model

For future DayN work, each attack surface should be documented as a 4-tuple:

| Item | Meaning |
| --- | --- |
| Injection point | Where the attack or abnormal input enters the system. |
| Symptom | What abnormal command, mission, position, or telemetry behavior appears. |
| Response | What the defense logic detected, blocked, rolled back, or recovered. |
| Log proof | Which file proves the event and the response. |

This convention keeps the repository aligned with the report goal: the report body explains the defense logic, and `docs/` provides compact supporting evidence.

## Reading Order

1. Start with the project root `README.md` for the system architecture.
2. Read `day1/README.md` for the simulation baseline.
3. Read `day2/README.md` for the web UI integration layer.
4. Read `day3/README.md` for the bridge MVP result.
5. Read `day3/evidence_summary.md` for the detailed Day3 evidence interpretation.

## Evidence Policy

Evidence files should stay close to the command or observation that produced them. Prefer plain text logs and small Markdown summaries so the result can be reviewed without rebuilding the whole environment.
