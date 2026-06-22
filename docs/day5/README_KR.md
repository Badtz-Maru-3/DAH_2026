# Day5 - GNSS Integrity Evidence

원본: `docs/day5/README.md`

Day5는 Mission Audit mode 이후 추가된 GNSS Integrity adapter를 검증합니다.

목적은 MAVLink `GPS_INPUT`을 position-input attack surface로 다룰 수 있음을 보여주는 것입니다. Bridge는 incoming GNSS coordinate를 current odometry-derived expected position과 비교하고, implausible jump 또는 poor-quality fix를 reject합니다.

## Result

GNSS integrity validation passed.

Captured evidence:

- `BASE_LAT`/`BASE_LON` 근처의 normal `GPS_INPUT` accepted
- 약 `2837.65 m` spoofed coordinate jump rejected
- poor fix는 `fix_type`, satellite count, horizontal accuracy threshold 위반으로 rejected

## Layer Mapping

- Simulation Layer: odometry-derived expected UGV position
- Software-Defined UGV Security Layer: GNSS Integrity, GPS_INPUT validation, spoof jump detection, poor-fix detection

## Implementation

| File | Role |
| --- | --- |
| `Bridge/gnss_integrity.py` | `GPS_INPUT` 처리, odometry 기반 expected position 계산, JSONL audit record 작성 |
| `Bridge/ros2_mavlink_bridge.py` | MAVLink message를 command handling 전에 `GnssIntegrity`로 route |
| `Bridge/tools/send_gps_input.py` | `normal`, `spoof_jump`, `poor_fix` GPS_INPUT test case 전송 |

## Main Environment Values

| Variable | Current default | Meaning |
| --- | --- | --- |
| `GNSS_MAX_RESIDUAL_M` | `30` | odometry-derived expected position과 GNSS input 사이의 최대 거리 |
| `GNSS_MIN_FIX_TYPE` | `3` | minimum acceptable MAVLink GPS fix type |
| `GNSS_MIN_SATELLITES` | `6` | minimum visible satellite count |
| `GNSS_MAX_HACC_M` | `15` | maximum horizontal accuracy in meters |

## Evidence Files

| File | Meaning |
| --- | --- |
| `gnss_integrity.log` | normal, spoofed, poor-fix GPS_INPUT JSONL audit log |
| `bridge_gnss_integrity.log` | GNSS integrity test 중 bridge runtime log |
| `bridge_gnss_integrity_clean.log` | Reserved/cleaned bridge log; 현재 evidence set에서는 empty |
| `docker_ps_gnss_integrity.txt` | test run container status snapshot |

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

Day5는 세 번째 attack-defense surface인 position-input integrity를 검증합니다. Long-duration navigation fallback이나 sensor fusion을 증명하지는 않습니다. Bridge가 odometry-based short-term position expectation과 맞지 않는 GNSS input을 detect and log할 수 있음을 증명합니다.
