# Day5 - GNSS Integrity Evidence

Day5 validates the GNSS integrity adapter added after mission audit mode.

The purpose is to show that MAVLink `GPS_INPUT` can be treated as a position-input attack surface. The bridge compares incoming GNSS coordinates with the current odometry-derived expected position and rejects implausible jumps or poor-quality fixes.

## Result

GNSS integrity validation passed.

The captured evidence shows:

- Normal `GPS_INPUT` near `BASE_LAT`/`BASE_LON` was accepted.
- A spoofed coordinate jump of about `2837.65 m` was rejected against `GNSS_MAX_RESIDUAL_M=30`.
- A poor fix was rejected because `fix_type`, satellite count, and horizontal accuracy violated thresholds.

## Implementation

| File | Role |
| --- | --- |
| `Bridge/gnss_integrity.py` | Handles `GPS_INPUT`, computes expected position from odometry, and writes JSONL audit records. |
| `Bridge/ros2_mavlink_bridge.py` | Routes MAVLink messages to `GnssIntegrity` before command handling. |
| `Bridge/tools/send_gps_input.py` | Sends `normal`, `spoof_jump`, or `poor_fix` GPS_INPUT test cases. |

Main environment values:

| Variable | Current default | Meaning |
| --- | --- | --- |
| `GNSS_MAX_RESIDUAL_M` | `30` | Maximum distance between odometry-derived expected position and GNSS input. |
| `GNSS_MIN_FIX_TYPE` | `3` | Minimum acceptable MAVLink GPS fix type. |
| `GNSS_MIN_SATELLITES` | `6` | Minimum visible satellite count. |
| `GNSS_MAX_HACC_M` | `15` | Maximum horizontal accuracy in meters. |

## Evidence Files

| File | Meaning |
| --- | --- |
| `gnss_integrity.log` | JSONL audit log for normal, spoofed, and poor-fix GPS_INPUT cases. |
| `bridge_gnss_integrity.log` | Bridge runtime log during GNSS integrity tests. |
| `bridge_gnss_integrity_clean.log` | Reserved/cleaned bridge log; currently empty in this evidence set. |
| `docker_ps_gnss_integrity.txt` | Container status snapshot for the test run. |

## Key Observations

Accepted normal GNSS:

```text
result=accepted, residual_m=2.3921871668825445, fix_type=3, satellites_visible=12, horiz_accuracy=1.5
```

Rejected spoof jump:

```text
result=rejected, residual_m=2837.645170222998, reasons=["position residual 2837.65m > limit 30.00m"]
```

Rejected poor fix:

```text
result=rejected, fix_type=1, satellites_visible=3, horiz_accuracy=50.0
```

## Interpretation

Day5 proves the third attack-defense surface: position-input integrity. It does not yet prove long-duration navigation fallback or sensor fusion. It proves that the bridge can detect and log GNSS inputs that disagree with the odometry-based short-term position expectation.
