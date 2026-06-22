#!/usr/bin/env bash
set -e

BRIDGE_CONTAINER="${BRIDGE_CONTAINER:-dah-bridge}"
LOG_DIR="${LOG_DIR:-Bridge/logs}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_LOG="${LOG_DIR}/evidence_run_${RUN_ID}.log"

mkdir -p "${LOG_DIR}"

run_tool() {
  echo "+ docker exec ${BRIDGE_CONTAINER} python3 /app/tools/$*"
  docker exec "${BRIDGE_CONTAINER}" python3 "/app/tools/$@"
}

{
  echo "DAH evidence run started at ${RUN_ID}"
  echo "BRIDGE_CONTAINER=${BRIDGE_CONTAINER}"

  echo "[Day 3] manual control forward"
  run_tool send_manual_control.py forward --duration 3.0

  echo "[Day 3] manual control turn"
  run_tool send_manual_control.py turn --duration 2.0

  echo "[Day 3] manual control stop"
  run_tool send_manual_control.py stop

  echo "[Day 4] mission upload normal"
  run_tool send_mission_upload.py normal

  sleep 2

  echo "[Day 4] mission upload malicious_far"
  run_tool send_mission_upload.py malicious_far

  echo "[Day 5] GPS_INPUT normal"
  run_tool send_gps_input.py normal

  sleep 1

  echo "[Day 5] GPS_INPUT spoof_jump"
  run_tool send_gps_input.py spoof_jump

  sleep 1

  echo "[Day 5] GPS_INPUT poor_fix"
  run_tool send_gps_input.py poor_fix

  echo "[Day 6] GNSS spoof then manual control during hold"
  run_tool send_gps_input.py spoof_jump
  run_tool send_manual_control.py forward --duration 3.0

  echo "Bridge logs:"
  ls -la "${LOG_DIR}"
} | tee "${RUN_LOG}"
