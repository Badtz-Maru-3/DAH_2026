# Day4 - Mission Audit Evidence

원본: `docs/day4/README.md`

## Goal

Day3 bridge MVP 이후 UGV/GCS testbed의 Mission Audit mode를 검증합니다.

Day4 validation passed. Bridge는 normal mission을 accepted 처리했고, malicious mission을 rejected 처리했으며, matching audit log를 남겼습니다.

## Layer Mapping

- Simulation Layer: QGC mission upload context and simulated UGV operational boundary
- Software-Defined UGV Security Layer: Mission Audit, geofence validation, waypoint jump validation, MISSION_ACK accept/reject decision

## Scope

Mission audit v1은 실행 전 MAVLink mission item을 검증합니다. 구현은 `Bridge/mission_audit.py`에 있고, `Bridge/ros2_mavlink_bridge.py`에서 command handling 전에 호출됩니다. Day3의 `MANUAL_CONTROL -> /cmd_vel` path는 유지됩니다.

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

Current captured values:

- `MISSION_GEOFENCE_RADIUS_M=300`
- `MISSION_MAX_JUMP_M=120`

## Evidence

| File | Meaning |
| --- | --- |
| `mission_audit.log` | structured JSONL audit log |
| `bridge_mission_audit.log` | Bridge runtime log |
| `bridge_mission_audit_clean.log` | condensed bridge runtime log |
| `docker_ps_mission_audit.txt` | container status snapshot |

Audit entry는 최소한 다음 정보를 담아야 합니다.

| Field | Meaning |
| --- | --- |
| `timestamp` | bridge decision time |
| `sysid` | MAVLink uploader system ID |
| `seq` | mission item sequence number |
| `lat`, `lon`, `alt` | uploaded waypoint position |
| `command` | MAVLink mission command |
| `verdict` | `accepted` or `rejected` |
| `reason` | passed/failed rule |
| `recovery` | rollback, retain previous mission, hold, or no-op action |

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

## Interpretation

Day4는 두 번째 attack-defense surface인 mission command tampering을 검증합니다. Evidence set은 normal mission accepted, geofence/waypoint-jump violation rejected, last valid mission state preservation을 보여줍니다.

## Does Not Yet Prove

Day4는 autopilot의 actual mission execution을 증명하지 않습니다. upload audit과 reject/accept handling을 증명합니다. GNSS integrity와 correlation response는 Day5와 Day6에서 다룹니다.
