# Day4 — Mission Audit Evidence

## Goal

Validate Mission audit mode for the UGV/GCS testbed.

## Scope

Mission audit v1 validates uploaded MAVLink mission items before execution.

## Checks

- Mission item count limit
- Supported mission command allowlist
- Global coordinate frame check
- Geofence radius check
- Waypoint jump distance check
- Altitude range check

## Evidence

- `mission_audit.log`: structured JSONL audit log
- `bridge_mission_audit.log`: Bridge runtime log
- `docker_ps_mission_audit.txt`: container status snapshot

## Interpretation

The Mission audit layer accepts normal mission uploads and rejects mission uploads that violate geofence or waypoint-jump constraints.
