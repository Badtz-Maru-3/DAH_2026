#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:1
export QT_QPA_PLATFORM=xcb
export QT_X11_NO_MITSHM=1
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export XDG_RUNTIME_DIR=/tmp/runtime-qgc

mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

Xvfb :1 -screen 0 1280x800x24 -ac +extension GLX +render -noreset &
sleep 1

openbox &
sleep 1

x11vnc \
  -display :1 \
  -forever \
  -shared \
  -nopw \
  -listen 127.0.0.1 \
  -rfbport 5900 &

websockify \
  --web=/usr/share/novnc \
  127.0.0.1:6080 \
  127.0.0.1:5900 &

sleep 2

exec /opt/qgc/QGroundControl.AppImage --appimage-extract-and-run
