# Day6 - Correlation Engine Evidence

원본: `docs/day6/README.md`

Day6는 mission audit, GNSS integrity, command blocking을 연결하는 correlation layer를 검증합니다.

목적은 isolated check를 넘어서는 것입니다. Rejected mission 또는 GNSS spoof는 correlation signal로 변환됩니다. Risk score가 threshold에 도달하면 bridge는 hold를 engage하고, zero `/cmd_vel`을 publish하며, hold active 동안 subsequent manual-control command를 block합니다.

## Result

Correlation validation passed.

Captured evidence:

- GNSS spoof rejection이 `gnss_integrity/rejected` signal로 기록됨
- malicious mission rejection이 `mission_audit/rejected` signal로 기록됨
- 각 signal의 default weight `0.75`가 `CORRELATION_RISK_THRESHOLD=0.75`에 도달함
- correlation engine이 `5`초 동안 hold engage
- hold 중 `MANUAL_CONTROL` input이 blocked 되고 `command_blocked`로 log됨

## Layer Mapping

- Simulation Layer: simulated command execution target and odometry feedback
- Software-Defined UGV Security Layer: Correlation Engine, risk score calculation, hold engagement, command block

## Implementation

| File | Role |
| --- | --- |
| `Bridge/correlation_engine.py` | recent signal 유지, risk score 계산, hold engage, command blocking log |
| `Bridge/mission_audit.py` | mission audit reject 시 correlation signal 기록 |
| `Bridge/gnss_integrity.py` | GPS_INPUT reject 시 correlation signal 기록 |
| `Bridge/ros2_mavlink_bridge.py` | `/cmd_vel` publish 전 `evaluate_command()` 호출 |
| `Bridge/tools/send_manual_control.py` | command blocking 증명용 manual-control input 전송 |

## Main Environment Values

| Variable | Current default | Meaning |
| --- | --- | --- |
| `CORRELATION_SIGNAL_TTL_S` | `20` | active anomaly signal time window |
| `CORRELATION_RISK_THRESHOLD` | `0.75` | hold engage 기준 score |
| `CORRELATION_HOLD_SECONDS` | `5` | threshold crossing 이후 hold duration |
| `CORRELATION_WEIGHT_MISSION_REJECTED` | `0.75` | mission audit rejection risk weight |
| `CORRELATION_WEIGHT_GNSS_REJECTED` | `0.75` | GNSS integrity rejection risk weight |
| `CORRELATION_WEIGHT_HIGH_COMMAND` | `0.35` | high manual command risk weight |
| `COMMAND_HIGH_LINEAR_MPS` | `0.45` | command-guard linear threshold |
| `COMMAND_HIGH_ANGULAR_RADPS` | `1.0` | command-guard angular threshold |

## Evidence Files

| File | Meaning |
| --- | --- |
| `correlation_gnss_spoof.log` | GNSS spoof rejection 이후 correlation signal, hold, command-block evidence |
| `correlation_mission_malicious.log` | malicious mission rejection 이후 correlation signal, hold, command-block evidence |
| `bridge_correlation_clean.log` | hold와 blocked manual-control message를 보여주는 condensed bridge runtime log |
| `bridge_correlation.log` | correlation test full bridge runtime log |
| `gnss_normal_integrity.log` | normal GNSS accepted evidence |
| `gnss_spoof_integrity.log` | correlation에 사용된 GNSS spoof rejected evidence |
| `mission_audit.log` | correlation test에 사용된 mission audit evidence |
| `mission_malicious_audit.log` | correlation에 사용된 malicious mission rejection |
| `correlation_event.log` | default correlation log path; scenario-specific log 저장으로 captured set에서는 empty |
| `docker_ps_correlation.txt` | test run container status snapshot |

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

Day6는 현재 AI-defense orchestration skeleton을 검증합니다. Independent mission/GNSS anomaly detector가 correlation engine에 signal을 제공하고, response path가 zero `/cmd_vel` 및 command block으로 robot command를 억제할 수 있음을 보여줍니다.

이는 learned AI model, full mission execution, long-duration autonomous recovery를 증명하지 않습니다. Abnormal input, detection, hold/block response, evidence logging이라는 report-critical loop를 증명합니다.
