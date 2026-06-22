#!/usr/bin/env bash
set -e

BRIDGE_CONTAINER="${BRIDGE_CONTAINER:-dah-bridge}"
LOG_DIR="${LOG_DIR:-Bridge/logs}"
EVIDENCE_DIR="${EVIDENCE_DIR:-docs/evidence}"
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_LOG="${LOG_DIR}/evidence_run_${RUN_ID}.log"

mkdir -p "${LOG_DIR}"
mkdir -p "${EVIDENCE_DIR}/00_environment"
mkdir -p "${EVIDENCE_DIR}/03_manual_control"
mkdir -p "${EVIDENCE_DIR}/04_mission_audit"
mkdir -p "${EVIDENCE_DIR}/05_gnss_integrity"
mkdir -p "${EVIDENCE_DIR}/06_correlation_hold"

run_tool() {
  echo "+ docker exec ${BRIDGE_CONTAINER} python3 /app/tools/$*"
  docker exec "${BRIDGE_CONTAINER}" python3 "/app/tools/$@"
}

{
  echo "DAH evidence run started at ${RUN_ID}"
  echo "BRIDGE_CONTAINER=${BRIDGE_CONTAINER}"
  echo "EVIDENCE_DIR=${EVIDENCE_DIR}"

  echo "[Day 3] manual control forward"
  run_tool send_manual_control.py forward --duration 3.0

  echo "[Day 3] manual control turn"
  run_tool send_manual_control.py turn --duration 2.0

  echo "[Day 3] manual control stop"
  run_tool send_manual_control.py stop

  docker exec "${BRIDGE_CONTAINER}" cat /logs/correlation_event.log \
    > "${EVIDENCE_DIR}/03_manual_control/correlation_event_snapshot.log" 2>/dev/null || true

  echo "[Day 4] mission upload normal"
  run_tool send_mission_upload.py normal

  sleep 2

  echo "[Day 4] mission upload malicious_far"
  run_tool send_mission_upload.py malicious_far

  echo "[Day 4] mission upload malicious_jump"
  run_tool send_mission_upload.py malicious_jump

  sleep 2

  docker exec "${BRIDGE_CONTAINER}" cat /logs/mission_audit.log \
    > "${EVIDENCE_DIR}/04_mission_audit/mission_audit_snapshot.log" 2>/dev/null || true

  echo "[Day 5] GPS_INPUT normal"
  run_tool send_gps_input.py normal

  sleep 1

  echo "[Day 5] GPS_INPUT spoof_jump"
  run_tool send_gps_input.py spoof_jump

  sleep 1

  echo "[Day 5] GPS_INPUT poor_fix"
  run_tool send_gps_input.py poor_fix

  docker exec "${BRIDGE_CONTAINER}" cat /logs/gnss_integrity.log \
    > "${EVIDENCE_DIR}/05_gnss_integrity/gnss_integrity_snapshot.log" 2>/dev/null || true

  echo "[Day 6] GNSS spoof then manual control during hold"
  run_tool send_gps_input.py spoof_jump
  run_tool send_manual_control.py forward --duration 3.0

  docker exec "${BRIDGE_CONTAINER}" cat /logs/correlation_event.log \
    > "${EVIDENCE_DIR}/06_correlation_hold/correlation_event_snapshot.log" 2>/dev/null || true

  docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" \
    > "${EVIDENCE_DIR}/00_environment/docker_ps.txt" 2>/dev/null || true
  docker exec "${BRIDGE_CONTAINER}" env | sort \
    > "${EVIDENCE_DIR}/00_environment/bridge_env.txt" 2>/dev/null || true

  echo "Bridge logs:"
  ls -la "${LOG_DIR}"

  echo "Evidence files:"
  find "${EVIDENCE_DIR}" -maxdepth 2 -type f | sort
} | tee "${RUN_LOG}"
