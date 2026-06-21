# Day6 - Correlation Engine Evidence

Day6 validates the correlation layer that connects mission audit, GNSS integrity, and command blocking.

The purpose is to move beyond isolated checks. A rejected mission or GNSS spoof is converted into a correlation signal. If the risk score reaches the configured threshold, the bridge engages hold, publishes zero `/cmd_vel`, and blocks subsequent manual-control commands while the hold is active.

## Result

Correlation validation passed.

The captured evidence shows:

- GNSS spoof rejection recorded a `gnss_integrity/rejected` signal.
- Malicious mission rejection recorded a `mission_audit/rejected` signal.
- Either signal with default weight `0.75` reached `CORRELATION_RISK_THRESHOLD=0.75`.
- The correlation engine engaged hold for `5` seconds.
- `MANUAL_CONTROL` inputs during hold were blocked and logged as `command_blocked`.

## Layer Mapping

- Simulation Layer: simulated command execution target and odometry feedback
- Software-Defined UGV Security Layer: Correlation Engine, risk score calculation, hold engagement, command block

## Implementation

| File | Role |
| --- | --- |
| `Bridge/correlation_engine.py` | Maintains recent signals, computes risk score, engages hold, and logs command blocking. |
| `Bridge/mission_audit.py` | Records a correlation signal when mission audit rejects an upload. |
| `Bridge/gnss_integrity.py` | Records a correlation signal when GPS_INPUT is rejected. |
| `Bridge/ros2_mavlink_bridge.py` | Calls `evaluate_command()` before publishing `/cmd_vel`. |
| `Bridge/tools/send_manual_control.py` | Sends manual-control input used to prove command blocking. |

Main environment values:

| Variable | Current default | Meaning |
| --- | --- | --- |
| `CORRELATION_SIGNAL_TTL_S` | `20` | Time window for active anomaly signals. |
| `CORRELATION_RISK_THRESHOLD` | `0.75` | Score required to engage hold. |
| `CORRELATION_HOLD_SECONDS` | `5` | Hold duration after threshold crossing. |
| `CORRELATION_WEIGHT_MISSION_REJECTED` | `0.75` | Risk weight for mission audit rejection. |
| `CORRELATION_WEIGHT_GNSS_REJECTED` | `0.75` | Risk weight for GNSS integrity rejection. |
| `CORRELATION_WEIGHT_HIGH_COMMAND` | `0.35` | Risk weight for high manual command. |
| `COMMAND_HIGH_LINEAR_MPS` | `0.45` | Linear command threshold for command-guard signal. |
| `COMMAND_HIGH_ANGULAR_RADPS` | `1.0` | Angular command threshold for command-guard signal. |

## Evidence Files

| File | Meaning |
| --- | --- |
| `correlation_gnss_spoof.log` | Correlation signal, hold, and command-block evidence after GNSS spoof rejection. |
| `correlation_mission_malicious.log` | Correlation signal, hold, and command-block evidence after malicious mission rejection. |
| `bridge_correlation_clean.log` | Condensed bridge runtime log showing hold and blocked manual-control messages. |
| `bridge_correlation.log` | Full bridge runtime log for correlation tests. |
| `gnss_normal_integrity.log` | Normal GNSS accepted evidence. |
| `gnss_spoof_integrity.log` | GNSS spoof rejected evidence used by correlation. |
| `mission_audit.log` | Mission audit evidence used in correlation tests. |
| `mission_malicious_audit.log` | Malicious mission rejection used by correlation. |
| `correlation_event.log` | Default correlation log path; empty in this captured set because scenario-specific logs were saved separately. |
| `docker_ps_correlation.txt` | Container status snapshot for the test run. |

## Key Observations

GNSS spoof correlation:

```text
source=gnss_integrity, kind=rejected, risk_score=0.75
event=hold_engaged, hold_seconds=5.0
event=command_blocked, source=MANUAL_CONTROL, reasons=["correlation hold active"]
```

Mission rejection correlation:

```text
source=mission_audit, kind=rejected, risk_score=0.75
event=hold_engaged, hold_seconds=5.0
event=command_blocked, source=MANUAL_CONTROL, reasons=["correlation hold active"]
```

Bridge runtime evidence:

```text
[correlation] hold engaged: risk_score=0.75, reason=risk_score 0.75 >= threshold 0.75
MANUAL_CONTROL blocked by correlation engine: risk_score=0.75, reasons=['correlation hold active']
```

## Interpretation

Day6 proves the current AI-defense orchestration skeleton: independent mission/GNSS anomaly detectors feed a correlation engine, and the response path can actively suppress robot commands by publishing zero `/cmd_vel`.

This does not yet prove a learned AI model, full mission execution, or long-duration autonomous recovery. It does prove the report-critical loop of abnormal input, detection, hold/block response, and evidence logging.
