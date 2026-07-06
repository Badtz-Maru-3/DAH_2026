#!/usr/bin/env bash
set -euo pipefail

# One-command live run of the AI agent closed loop against the running testbed.
#
# Prereq: the integrated stack is up:
#   docker compose --env-file .env -f compose.webui.yml up -d
# compose.webui.yml bind-mounts ./agents and ./Bridge into the dah-bridge
# container (under /workspace), so the agent package is importable there with
# rclpy and the live ROS2/MAVLink graph. Run traces and incident reports are
# written back to ./agents/reports on the host.
#
# Usage:
#   ./agents/run_live.sh                 # scenario A, deterministic (--llm-backend none)
#   ./agents/run_live.sh B               # scenario B
#   ./agents/run_live.sh C --llm-backend openai:gpt-4o-mini
#   ./agents/run_live.sh A --rounds 1 --settle-seconds 1
#
# The first non-flag argument selects the scenario (A/B/C). Any remaining
# arguments are appended to the orchestrator; because argparse takes the last
# occurrence of a repeated flag, you can override the defaults below (e.g. pass
# --llm-backend or --rounds again).

CONTAINER="${DAH_BRIDGE_CONTAINER:-dah-bridge}"

SCENARIO="A"
if [ "$#" -gt 0 ] && [[ "$1" != -* ]]; then
  SCENARIO="$1"
  shift
fi

# Scenario A drives the robot to the attacker target (3, 2). Both the Gazebo pose
# and the EKF estimate persist across runs, so a re-run finds the robot already
# there and the hijack does nothing (defender sees only the 'hold', not the
# envelope-breach 'block'). Reset the robot to the origin first so every A run
# reproduces the full block + visible hijack. Set DAH_SKIP_RESET=1 to opt out.
if [ "$SCENARIO" = "A" ] && [ "${DAH_SKIP_RESET:-0}" != "1" ]; then
  "$(dirname "$0")/../demo/reset_robot_pose.sh" \
    || echo "[run_live] pose reset skipped (reset failed; continuing)" >&2
fi

exec docker exec -e PYTHONDONTWRITEBYTECODE=1 -w /workspace "$CONTAINER" bash -lc \
  "source /opt/ros/humble/setup.bash && \
   python3 -m agents.main_orchestrator \
     --live --confirm-live-testbed-only \
     --scenario-id '${SCENARIO}' --rounds 1 --llm-backend none $*"
