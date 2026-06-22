<div align="right">
  <strong>🇺🇸 English</strong> | <a href="AGENTS_KR.md">🇰🇷 한국어</a>
</div>

# AGENTS.md

This file defines how Claude Code, Codex, and the user should collaborate inside the DAH_2026 repository.

The workflow adapts the Claude-GPT collaboration model from `longranger2/claude-gpt-workflow`: Claude orchestrates and reviews, Codex critiques plans and executes implementation batches, and major work moves through iterative plan review, batch execution, code review, and fix loops.

## 1. Project Purpose

This repository implements a **software-defined UGV/GCS cybersecurity testbed** for the DAH 2026 Defense AI Cyber Security Hackathon preliminary round.

The testbed abstracts military UGV/GCS security-relevant control flows at the software layer. It is a simulation-based validation environment for GCS control, MAVLink command and telemetry flow, mission upload validation, GNSS/location input validation, anomaly correlation, and command hold/block response.

Do **not** describe this repository as a real military UGV replica, a military-grade platform, a real RF-layer implementation, or a physical GNSS receiver integration. The correct framing is:

```text
Defense UGV-inspired software-defined UGV/GCS cybersecurity testbed.
```

## 2. Architecture Overview

Use the Logical Two-Layer Testbed Architecture consistently across code comments, documentation, reports, reviews, and task plans.

### Simulation Layer

The Simulation Layer provides visualization, simulated motion, and state feedback.

Components:

- QGroundControl / QGC noVNC
- Gazebo
- RViz
- ROSbot / ROSbot XL simulation
- ROS2 `/cmd_vel`
- ROS2 `/odometry/filtered`
- ROS2 `/scan` and `/tf` where the selected robot configuration provides them

### Software-Defined UGV Security Layer

The Software-Defined UGV Security Layer validates and constrains the simulated UGV operation flow.

Components:

- MAVLink Bridge
- Mission Audit
- GNSS Integrity
- Correlation Engine
- Command Hold / Block

This is a logical architecture, not a physically isolated network architecture.

Core inter-layer data flow:

```text
QGC joystick
-> MAVLink MANUAL_CONTROL
-> ROS2-MAVLink Bridge
-> ROS2 /cmd_vel
-> Gazebo ROSbot
-> /odometry/filtered
-> Bridge
-> MAVLink telemetry
-> QGC HUD
```

Known implemented evidence-backed flows:

```text
Day3:
QGC joystick -> MAVLink MANUAL_CONTROL -> Bridge -> ROS2 /cmd_vel
-> ROSbot movement -> /odometry/filtered telemetry

Day4:
Mission upload -> Mission Audit -> geofence / waypoint jump validation
-> MISSION_ACK accepted or rejected

Day5:
GPS_INPUT -> GNSS Integrity -> normal / spoof_jump / poor_fix classification

Day6:
Mission/GNSS/Command anomaly signal -> Correlation Engine -> risk score
-> hold_engaged -> command_blocked
```

Do not rewrite implementation status unless source code, runtime logs, or documented evidence confirm the change.

## 3. Claude and Codex Roles

| Agent | Responsibilities |
| --- | --- |
| Claude | Owns planning, breaks work into batches, checks architectural consistency, reviews diffs, checks documentation alignment, and decides whether a batch is approved or needs fixes. |
| Codex | Performs adversarial plan review, identifies missing assumptions, unsafe changes, weak tests, vague requirements, and architectural inconsistencies; implements assigned batches; fixes issues found during Claude review; does not silently expand scope. |
| User | Defines the goal, approves major direction, and provides project intent when ambiguity remains. |

Claude is the orchestrator, reviewer, and planner. Codex is the implementation executor and adversarial reviewer. The workflow must not be one-shot for major changes.

## 4. Workflow

Major work should use two phases.

### Phase 1: Plan Review

```text
User or Claude writes a plan
-> Claude sends the plan to Codex for adversarial review
-> Codex returns issues ranked by severity
-> Claude refines the plan
-> if the plan still needs revision, repeat
-> if approved or mostly good, proceed to execution
```

Codex should review as a critical nitpicker, not as a rubber stamp. Reviews should call out missing assumptions, risky file scope, weak validation, unsupported claims, and mismatches with the two-layer architecture.

### Phase 2: Plan Execute

```text
Claude dispatches one implementation batch to Codex
-> Codex modifies code/docs
-> Claude reviews the diff in read-only mode
-> Claude writes a review
-> if issues exist, Codex fixes them
-> if approved, move to the next batch
-> repeat until all batches are complete
```

Each batch should be small enough to review. Do not combine Docker, compose, bridge behavior, test tooling, and documentation rewrites in one large batch unless the plan explicitly requires it.

## 5. Required Loops

### Loop A: Plan Refinement

- Plan review finds issues.
- Claude revises the plan.
- Codex reviews again.
- Repeat until the plan is approved or the remaining risks are explicitly accepted.

### Loop B: Code Fixing

- Codex implements a batch.
- Claude reviews the diff.
- Codex fixes review findings.
- Claude re-reviews.
- Repeat until the batch is approved.

### Loop C: Batch Processing

- Large work is split into small batches.
- Each batch must pass review before the next batch starts.
- Completion requires all batches to be reviewed, fixed, and either approved or explicitly documented with remaining limitations.

## 6. Batch Rules

- Do not modify unrelated files.
- Prefer small, reviewable changes.
- Each batch must have a clear goal.
- Each batch should list expected files before modification.
- For risky behavior changes, update relevant docs and tests together.
- Preserve existing environment variable behavior unless the batch explicitly changes it.
- Avoid broad refactors unless requested.
- Avoid changing Docker, compose, bridge logic, and test scripts in one huge batch unless the plan explicitly requires it.
- Do not silently regenerate evidence logs or screenshots.

## 7. Safety and Scope Rules

- Do not introduce real-world offensive functionality.
- Do not add malware, persistence, credential theft, destructive behavior, or unauthorized access logic.
- Keep attack/test scenarios simulation-bound and defensive.
- Security modules should focus on validation, detection, rejection, logging, hold, and block behavior.
- Do not claim real military operational equivalence.
- Do not claim real RF, real GNSS receivers, real military UGV hardware, or encrypted C2 links are implemented unless source code and evidence confirm it.
- Use wording such as `software-defined testbed`, `simulation-based validation`, `military UGV-inspired control-flow abstraction`, and `ROSbot-based surrogate platform`.

Forbidden unless explicitly requested:

```bash
rm -rf
docker system prune
git reset --hard
git clean -fd
sudo rm -rf
force push
```

## 8. Coding Rules

- Keep Python code readable and explicit.
- Preserve the current module boundaries:
  - `Bridge/ros2_mavlink_bridge.py`: main bridge orchestration
  - `Bridge/mission_audit.py`: mission validation
  - `Bridge/gnss_integrity.py`: GNSS input validation
  - `Bridge/correlation_engine.py`: risk scoring and hold/block logic
  - `Bridge/tools/`: test message generators
- Prefer deterministic logs.
- Use JSONL logs for test evidence when appropriate.
- Preserve existing environment variable behavior unless the task explicitly changes it.
- Do not break existing Docker Compose flows.
- Keep ROS2 topic names consistent.
- Keep MAVLink/ROS2 bridge behavior documented when changed.
- Avoid broad refactors unless requested.
- Run syntax checks for Python changes when practical.

Recommended Python syntax check:

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

## 9. Documentation Rules

- README and AGENTS.md must stay aligned.
- Architecture docs must preserve the two-layer model.
- If behavior changes, update relevant docs under `docs/`.
- Evidence logs should remain reproducible.
- Markdown summaries may be edited, but raw evidence should remain intact unless the user explicitly asks to regenerate or clean evidence.
- Do not invent experimental results, screenshots, logs, performance numbers, or test outcomes.
- Do not present implementation details before explaining threat model and operational relevance in report-facing architecture docs.

Use clear terminology:

- Mission Audit
- GNSS Integrity
- Correlation Engine
- Command Hold / Block
- Simulation Layer
- Software-Defined UGV Security Layer
- software-defined UGV/GCS cybersecurity testbed
- Logical Two-Layer Testbed Architecture

Avoid:

- real military UGV replica
- actual military UGV implementation
- military-grade UGV
- physical UGV system
- real RF-layer implementation
- real GNSS receiver integration

Evidence files are important. Do not edit `*.log`, raw `*.txt` evidence, JSONL runtime logs, screenshots, or captured terminal outputs unless the task is specifically to regenerate them.

## 10. Review Checklist

Claude should use this checklist after Codex modifies files:

- Does the change match the requested batch?
- Were unrelated files modified?
- Does the architecture still match the two-layer model?
- Are Docker/compose assumptions still valid?
- Are topic names and ports consistent?
- Are logs/tests/docs updated where needed?
- Does the change avoid unsupported military-equivalence claims?
- Is the change reproducible from README instructions?
- Were raw evidence files preserved unless regeneration was explicitly requested?
- Are remaining limitations documented?

## Contest Guide Awareness

Before making major changes to README files, report drafts, architecture documentation, evaluation evidence, demo scripts, or security scenario descriptions, agents should read:

```text
docs/contest/preliminary_guide_summary.md
```

Use that summary to align work with the DAH preliminary round guide. Do not duplicate the full guide in this file, and do not invent contest requirements when the summary marks an item as ambiguous or missing.

## 11. Recommended Commands

Use commands that are safe and generally applicable. Prefer read-only checks before edits.

Repository inspection:

```bash
git status --short
git diff --stat
git diff
find . -name "*.md" -not -path "./.git/*" -print | sort
grep -R "Mission Audit" docs README.md AGENTS.md
```

Python checks:

```bash
python3 -m py_compile Bridge/ros2_mavlink_bridge.py Bridge/mission_audit.py Bridge/gnss_integrity.py Bridge/correlation_engine.py
```

Docker/Compose checks:

```bash
docker compose --env-file .env -f compose.webui.yml config
docker ps
```

ROS2 checks, when the runtime stack is running:

```bash
ros2 topic list -t
ros2 topic info /cmd_vel -v
ros2 topic echo /odometry/filtered --once
```

If unsure whether a command applies, write it as an example pattern rather than a guaranteed command.

## 12. Completion Criteria

A task is complete only when:

- the requested files are updated
- unrelated changes are avoided
- review issues are resolved or explicitly documented
- docs match implementation
- commands/tests/checks have been run when practical
- remaining limitations are clearly listed
- the final response summarizes changed files, assumptions, checks run, and any residual risk
