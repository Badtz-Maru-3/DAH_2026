#!/usr/bin/env bash
# Reset the ROSbot to a known pose for repeatable Scenario A live demos.
#
# Scenario A's hijack (demo/hijack_nav.py) drives the robot to the attacker
# target (3, 2) using /odometry/filtered. Both the EKF estimate AND the Gazebo
# ground-truth pose persist across runs, so a second run finds the robot already
# at the target: the hijack then does nothing and the defender only sees the
# unexpected-publisher "hold", never the envelope-breach "block".
#
# This script restores BOTH frames to the origin so every run reproduces the
# full "block + visible hijack":
#   1. Gazebo physical/visual pose       -> ign transport /world/<world>/set_pose
#   2. EKF estimate (/odometry/filtered) -> robot_localization /set_pose
#
# The two frames are decoupled: teleporting the Gazebo model does NOT move
# /odometry/filtered (wheel odometry is continuous), and resetting the EKF does
# NOT move the model. hijack_nav navigates by the EKF estimate, so #2 is what
# makes the attack fire again; #1 is what makes the GUI visibly reset.
#
# Both services live inside the simulator container, so we docker-exec there.
#
# Usage:
#   ./demo/reset_robot_pose.sh            # reset to origin (0, 0)
#   ./demo/reset_robot_pose.sh 1.0 -2.0   # reset to a custom (x, y)
#
# Env overrides: DAH_SIM_CONTAINER, DAH_GZ_WORLD, DAH_ROBOT_MODEL.
set -euo pipefail

SIM_CONTAINER="${DAH_SIM_CONTAINER:-dah-rosbot-sim-novnc}"
WORLD="${DAH_GZ_WORLD:-dah_outdoor}"
MODEL="${DAH_ROBOT_MODEL:-rosbot}"
X="${1:-0.0}"
Y="${2:-0.0}"
Z="${3:-0.2}"

docker exec "$SIM_CONTAINER" bash -lc "
  source /opt/ros/humble/setup.bash
  # 1) Teleport the Gazebo model (ground truth / what the GUI shows).
  ign service -s /world/${WORLD}/set_pose \
    --reqtype ignition.msgs.Pose --reptype ignition.msgs.Boolean \
    --timeout 3000 \
    --req 'name: \"${MODEL}\", position: {x: ${X}, y: ${Y}, z: ${Z}}, orientation: {w: 1.0}' \
    >/dev/null
  # 2) Reset the EKF estimate that hijack_nav navigates by. The ros2 service CLI
  #    can hang after a successful call, so bound it and ignore the exit status;
  #    the pose still takes effect (verified against /odometry/filtered).
  timeout 8 ros2 service call /set_pose robot_localization/srv/SetPose \
    \"{pose: {header: {frame_id: odom}, pose: {pose: {position: {x: ${X}, y: ${Y}, z: 0.0}, orientation: {w: 1.0}}}}}\" \
    >/dev/null 2>&1 || true
"

echo "[reset] robot pose reset to (${X}, ${Y}) in ${SIM_CONTAINER}"
