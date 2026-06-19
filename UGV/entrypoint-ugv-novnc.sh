#!/usr/bin/env bash
set -eo pipefail

export DISPLAY=:2
export QT_X11_NO_MITSHM=1
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-17}"
export ROBOT_MODEL="${ROBOT_MODEL:-rosbot}"
export XDG_RUNTIME_DIR=/tmp/runtime-ugv

mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

Xvfb :2 -screen 0 1280x800x24 -ac +extension GLX +render -noreset &
sleep 1

openbox &
sleep 1

x11vnc \
  -display :2 \
  -forever \
  -shared \
  -nopw \
  -listen 127.0.0.1 \
  -rfbport 5901 &

websockify \
  --web=/usr/share/novnc \
  127.0.0.1:6081 \
  127.0.0.1:5901 &

sleep 2

source /opt/ros/humble/setup.bash

if [ -f /ros2_ws/install/setup.bash ]; then
  source /ros2_ws/install/setup.bash
fi

exec ros2 launch rosbot_gazebo simulation.launch.py \
  robot_model:=${ROBOT_MODEL} \
  gz_headless_mode:=False \
  use_rviz:=False
