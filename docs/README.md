# DAH 2026 Evidence

This directory stores day-by-day evidence for the DAH 2026 Docker robotics simulation stack.

The evidence is meant to answer three questions:

- Which containers were running?
- Which ROS2 topics and nodes were visible?
- Did the expected control or visualization behavior actually happen?

## Index

| Day | Focus | Status |
| --- | --- | --- |
| `day1/` | ROSbot Gazebo simulation baseline. | Captured container, ROS2 topic, and simulation logs. |
| `day2/` | Web UI stack with QGroundControl, Gazebo, and RViz through noVNC. | Captured service logs and ROS2 topic state. |
| `day3/` | ROS2-MAVLink bridge MVP. | Captured end-to-end QGC-to-ROSbot control evidence. |

## Reading Order

1. Start with the project root `README.md` for the system architecture.
2. Read `day1/README.md` for the simulation baseline.
3. Read `day2/README.md` for the web UI integration layer.
4. Read `day3/README.md` for the bridge MVP result.
5. Read `day3/evidence_summary.md` for the detailed Day3 evidence interpretation.

## Evidence Policy

Evidence files should stay close to the command or observation that produced them. Prefer plain text logs and small Markdown summaries so the result can be reviewed without rebuilding the whole environment.
