# Day4 - Mission Audit Evidence

## Goal

Validate Mission audit mode for the UGV/GCS testbed after Day3's bridge MVP.

Day4 validation passed. The bridge accepted a normal mission, rejected malicious missions, and wrote matching audit logs.

## Scope

Mission audit v1 validates uploaded MAVLink mission items before execution. It is implemented in `Bridge/mission_audit.py` and is called from `Bridge/ros2_mavlink_bridge.py` before command handling, without breaking the Day3 `MANUAL_CONTROL -> /cmd_vel` path.

Expected MAVLink flow:

```text
QGroundControl mission upload
  -> MISSION_COUNT
  -> dah-bridge requests items with MISSION_REQUEST_INT
  -> MISSION_ITEM_INT entries are audited
  -> MISSION_ACK accepted or rejected
  -> mission_audit.log evidence
```

## Checks

- Mission uploader sysid consistency
- Mission sequence integrity
- Mission item count limit
- Supported mission command allowlist
- Global coordinate frame check
- Geofence radius check
- Waypoint jump distance check
- Altitude range check

Thresholds such as geofence radius and waypoint jump distance come from `.env`/compose runtime configuration. Current captured values are `MISSION_GEOFENCE_RADIUS_M=300` and `MISSION_MAX_JUMP_M=120`.

## Evidence

- `mission_audit.log`: structured JSONL audit log
- `bridge_mission_audit.log`: Bridge runtime log
- `bridge_mission_audit_clean.log`: condensed bridge runtime log
- `docker_ps_mission_audit.txt`: container status snapshot

Each audit entry should record at least:

| Field | Meaning |
| --- | --- |
| `timestamp` | When the bridge made the decision. |
| `sysid` | MAVLink uploader system ID. |
| `seq` | Mission item sequence number. |
| `lat`, `lon`, `alt` | Uploaded waypoint position. |
| `command` | MAVLink mission command. |
| `verdict` | `accepted` or `rejected`. |
| `reason` | Rule that passed or failed. |
| `recovery` | Rollback, retain previous mission, hold, or no-op action. |

## Interpretation

Day4 proves the second attack-defense surface: mission command tampering. The evidence set shows a normal mission accepted, a geofence or waypoint-jump violation rejected, and the bridge preserving the last valid mission state.

## Key Observations

Normal mission accepted:

```text
event=mission_audit_result, result=accepted, count=2
MISSION_ACK result=0 reason=mission accepted
```

Malicious mission rejected:

```text
event=mission_audit_result, result=rejected
seq=0: geofence violation distance=2837.65m limit=300.00m
seq=0: waypoint jump=2837.65m limit=120.00m
MISSION_ACK result=14
```

## Does Not Yet Prove

Day4 does not prove actual mission execution by an autopilot. It proves upload audit and reject/accept handling. GNSS integrity and correlation response are covered by Day5 and Day6.
