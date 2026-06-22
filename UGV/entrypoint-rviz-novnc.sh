#!/usr/bin/env bash
set -eo pipefail

export DISPLAY=:3
export QT_X11_NO_MITSHM=1
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-17}"
export XDG_RUNTIME_DIR=/tmp/runtime-rviz

mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

Xvfb :3 -screen 0 1280x800x24 -ac +extension GLX +render -noreset &
sleep 1

openbox &
sleep 1

x11vnc \
  -display :3 \
  -forever \
  -shared \
  -nopw \
  -noshm \
  -listen 127.0.0.1 \
  -rfbport 5902 \
  -noxdamage \
  -nowf \
  -noscr &

websockify \
  --web=/usr/share/novnc \
  127.0.0.1:6082 \
  127.0.0.1:5902 &

sleep 2

source /opt/ros/humble/setup.bash

if [ -f /ros2_ws/install/setup.bash ]; then
  source /ros2_ws/install/setup.bash
fi

exec rviz2 -d /opt/dah/rviz/dah_default.rviz --ros-args -p use_sim_time:=true
