# DAH 2026 Evidence

Korean version: [`README_KR.md`](README_KR.md).

This directory stores day-by-day evidence for the DAH 2026 Docker software-defined UGV/GCS cybersecurity testbed.

The evidence should be read with the Logical Two-Layer Testbed Architecture in mind: the Simulation Layer provides QGroundControl, Gazebo/ROSbot, RViz, and odometry feedback, while the Software-Defined UGV Security Layer provides the bridge, mission audit, GNSS integrity, correlation, and command hold/block behavior.

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
| `day4/` | Mission audit mode. | Captured normal mission accepted and malicious mission rejected evidence. |
| `day5/` | GNSS integrity adapter. | Captured normal GPS_INPUT accepted and spoof/poor-fix rejected evidence. |
| `day6/` | Correlation engine. | Captured hold engagement and MANUAL_CONTROL blocking after mission/GNSS anomalies. |

## Day Roles

The day folders are cumulative rather than independent.

| Day | Role in the final plan |
| --- | --- |
| Day1 | Establishes a known-good simulation and ROS2 topic baseline. Later attack evidence should be compared against this normal state. |
| Day2 | Establishes the operator and visualization layer. Future mission upload, alert, and screenshot evidence should be captured through this layer. |
| Day3 | Establishes the first active command path. Future C2-style command injection, blocking, and recovery experiments should preserve this baseline path. |
| Day4 | Establishes mission upload audit: normal mission accepted and malicious geofence/jump mission rejected. |
| Day5 | Establishes GNSS integrity: normal GPS_INPUT accepted and spoof/poor-fix inputs rejected. |
| Day6 | Establishes correlation response: mission/GNSS rejection produces hold and blocks manual-control commands. |

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
2. Read `architecture/two_layer_architecture.md` for the logical two-layer architecture and Day3-Day6 evidence mapping.
3. Read `day1/README.md` for the simulation baseline.
4. Read `day2/README.md` for the web UI integration layer.
5. Read `day3/README.md` for the bridge MVP result.
6. Read `day3/evidence_summary.md` for the detailed Day3 evidence interpretation.
7. Read `day4/README.md` for mission audit implementation and evidence.
8. Read `day5/README.md` for GNSS integrity implementation and evidence.
9. Read `day6/README.md` for correlation hold/blocking evidence.

## Evidence Policy

Evidence files should stay close to the command or observation that produced them. Prefer plain text logs and small Markdown summaries so the result can be reviewed without rebuilding the whole environment.
