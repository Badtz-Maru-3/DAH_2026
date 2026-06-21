# AGENTS.md

## Project Context

This repository is for the DAH 2026 Defense AI Cyber Security Hackathon preliminary round.

The project implements a **software-defined UGV/GCS cybersecurity testbed**.

This testbed is **not** a replica of an actual military UGV platform. It abstracts key operational flows commonly found in defense UGV environments:

* GCS control
* MAVLink-based command and telemetry flow
* Mission upload validation
* GNSS/location input validation
* Anomaly correlation
* Command hold/block response

The correct framing is:

> Defense UGV-inspired software-defined UGV/GCS cybersecurity testbed.

Avoid claiming that this repository implements a real military UGV, military-grade platform, RF-layer system, or physical GNSS receiver integration.

---

## Logical Architecture

Use the following architecture framing consistently across documentation and reports.

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

### Simulation Layer

The Simulation Layer provides visualization, simulated motion, and state feedback.

Components:

* QGroundControl noVNC
* Gazebo / ROSbot simulation
* RViz noVNC
* `/odometry/filtered`
* `/scan`
* `/tf`

### Software-Defined UGV Security Layer

The Software-Defined UGV Security Layer validates and controls the simulated UGV operation flow.

Components:

* MAVLink Bridge
* Mission Audit
* GNSS Integrity
* Correlation Engine
* Command Hold / Block

This is a **logical architecture**, not a physically isolated network architecture.

---

## Repository Structure

Expected high-level structure:

```text
DAH_2026/
├── AGENTS.md
├── README.md
├── compose.webui.yml
├── .env.example
├── Bridge/
├── GCS/
├── UGV/
└── docs/
```

Important directories:

```text
Bridge/
  ros2_mavlink_bridge.py
  mission_audit.py
  gnss_integrity.py
  correlation_engine.py
  tools/

GCS/
  Dockerfile.qgc-novnc
  compose.gcs.novnc.yml

UGV/
  Dockerfile.rviz-novnc
  compose.ugv.novnc.yml
  compose.rviz.novnc.yml

docs/
  architecture/
  day3/
  day4/
  day5/
  day6/
```

---

## Implementation Status

Known implemented flows:

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

Do not rewrite this status unless logs or source code confirm a change.

---

## Development Environment

Primary target environment:

* Ubuntu 22.04 on WSL
* Docker / Docker Compose
* ROS2 Humble
* Python 3
* pymavlink
* QGroundControl noVNC
* Gazebo / ROSbot
* RViz noVNC

Common startup command:

```bash
cd ~/DAH_2026
docker compose --env-file .env -f compose.webui.yml up -d --build
```

Common shutdown command:

```bash
cd ~/DAH_2026
docker compose --env-file .env -f compose.webui.yml down
```

---

## Safety and Scope Rules

Do not perform destructive operations unless explicitly requested.

Forbidden unless explicitly requested:

```bash
rm -rf
docker system prune
git reset --hard
git clean -fd
sudo rm -rf
force push
```

Do not modify files outside this repository.

Do not modify evidence logs unless the task is specifically to regenerate evidence.

Do not invent experimental results.

Do not fabricate screenshots, logs, performance numbers, or test outcomes.

Do not claim that real RF, real GNSS receivers, real military UGV hardware, or encrypted C2 links are implemented unless source code and evidence confirm it.

---

## Security Research Boundaries

This repository is for controlled cybersecurity testbed development and documentation.

Allowed:

* Simulated MAVLink control flow
* Mission upload validation
* GNSS spoofing simulation through test messages
* Defensive anomaly detection
* Correlation and command blocking
* Documentation and report writing
* Evidence organization

Avoid expanding into real-world offensive operations.

Do not add instructions for attacking real vehicles, real RF links, real GNSS receivers, or external systems.

Attack scenarios should remain testbed-bound and framed as simulated or software-defined validation cases.

---

## Coding Guidelines

Prefer small, readable Python modules.

Keep existing module boundaries:

* `ros2_mavlink_bridge.py`: main bridge orchestration
* `mission_audit.py`: mission validation
* `gnss_integrity.py`: GNSS input validation
* `correlation_engine.py`: risk scoring and hold/block logic
* `Bridge/tools/`: test message generators

When changing code:

1. Explain what file is changed and why.
2. Keep behavior compatible with existing Docker Compose setup.
3. Run syntax checks.
4. Preserve existing evidence unless regenerating it intentionally.

Recommended syntax check:

```bash
python3 -m py_compile \
  Bridge/ros2_mavlink_bridge.py \
  Bridge/mission_audit.py \
  Bridge/gnss_integrity.py \
  Bridge/correlation_engine.py \
  Bridge/tools/send_manual_control.py \
  Bridge/tools/send_gps_input.py \
  Bridge/tools/send_mission_upload.py
```

---

## Documentation Guidelines

Use precise wording.

Preferred terms:

```text
software-defined UGV/GCS cybersecurity testbed
Logical Two-Layer Testbed Architecture
Simulation Layer
Software-Defined UGV Security Layer
defense UGV-inspired
UGV/GCS cybersecurity validation
software-layer abstraction
ROSbot-based surrogate platform
```

Avoid:

```text
real military UGV replica
actual military UGV implementation
military-grade UGV
physical UGV system
real RF-layer implementation
real GNSS receiver integration
```

When writing architecture documentation, use this order:

```text
1. Defense UGV operational risk
2. Simulated testbed abstraction
3. Two-layer architecture
4. Attack surface
5. Defense module
6. Evidence logs
7. Limitations
```

Do not present implementation details before explaining the threat model and operational relevance.

---

## Evidence Handling

Evidence files are important and should be preserved.

Do not edit:

```text
*.log
*.txt
JSONL runtime logs
screenshots
captured terminal outputs
```

Unless the user explicitly asks to regenerate or clean evidence.

Evidence directories:

```text
docs/day3/
docs/day4/
docs/day5/
docs/day6/
```

Expected evidence meaning:

```text
docs/day3:
Bridge MVP and UGV movement evidence

docs/day4:
Mission Audit accept/reject evidence

docs/day5:
GNSS Integrity normal/spoof/poor-fix evidence

docs/day6:
Correlation Engine hold/block evidence
```

Markdown summaries may be edited, but raw evidence should remain intact.

---

## Git Guidelines

Before modifying files:

```bash
git status --short
```

After modifying files:

```bash
git status --short
git diff
```

Do not commit automatically unless explicitly asked.

If asked to commit, use focused commits.

Good commit examples:

```text
Update documentation for two-layer testbed architecture
Add Mission Audit evidence summary
Add GNSS integrity validation evidence
Add correlation engine hold block evidence
```

Avoid vague commits:

```text
update
fix
stuff
final
```

---

## Markdown Update Tasks

When asked to update Markdown documentation:

1. Inspect existing Markdown files first.
2. Update only project-owned Markdown files.
3. Do not rewrite third-party/vendor Markdown files.
4. Preserve evidence values.
5. Add cross-links where useful.
6. Do not modify source code unless explicitly requested.

Useful commands:

```bash
find . -name "*.md" \
  -not -path "./.git/*" \
  -not -path "./UGV/husarion-ugv-autonomy/*" \
  -print | sort

git diff -- '*.md'
git status --short
```

Expected result for documentation-only work:

```text
Only .md files should be modified or added.
```

---

## Reporting Style

For DAH report-related writing, prefer a formal but clear style.

Use cautious claims:

```text
This testbed validates...
The prototype demonstrates...
The software-defined layer detects...
The simulated environment abstracts...
```

Avoid overclaiming:

```text
This completely protects...
This guarantees...
This is a real military UGV...
This perfectly reproduces...
```

Every major technical claim should be backed by:

* source code
* runtime log
* screenshot
* documented test result
* official external reference, if applicable

---

## Current Project Narrative

Use this narrative unless the user changes the project direction:

```text
This project builds a defense UGV-inspired software-defined cybersecurity testbed.
The Simulation Layer provides QGC, Gazebo/ROSbot, RViz, and odometry feedback.
The Software-Defined UGV Security Layer provides MAVLink bridging, mission validation,
GNSS input validation, anomaly correlation, and command hold/block behavior.

The objective is to demonstrate how GCS control, mission upload, GNSS input, and telemetry flows
can be monitored and constrained before unsafe UGV behavior occurs in a simulated environment.
```

---

## Final Check Before Responding

Before finishing a task, verify:

* Did you modify only the requested files?
* Did you avoid changing raw logs or screenshots?
* Did you preserve the two-layer architecture framing?
* Did you avoid claiming real military UGV replication?
* Did you run relevant checks?
* Did you show a concise summary of changed files?
