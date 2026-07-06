<div align="right">
  <a href="../agents/README.md">🇺🇸 English</a> | <strong>🇰🇷 한국어</strong>
</div>

# AI 에이전트 아키텍처 - 공격 재현 및 폐루프 방어 오케스트레이션

이 디렉터리는 DAH_2026 **software-defined UGV/GCS cybersecurity testbed**의
**AI 에이전트 계층**을 정의한다. 이 문서는 예선 보고서의
**4.2 공격 관련 AI 에이전트**와 **4.3 방어 관련 AI 에이전트**를 뒷받침하며,
예선 평가 항목 **"AI 에이전트 아키텍처 (25점)"**을 지원한다.

> **설계 문서 전용.** 이 README는 아키텍처, 오케스트레이션, 인터페이스 명세다.
> 오케스트레이터(Claude)가 작성하고 실행자(Codex)가 구현 배치의 기준으로 삼는
> 구현 브리프다. 에이전트 코드는 이 문서에 작성하지 않는다. 자세한 구현 배치는
> [§10 Codex 구현 배치](#10-codex-구현-배치)를 참조한다.

---

## 0. 프레이밍과 안전 경계

- 이 저장소는 **Defense UGV-inspired, software-defined UGV/GCS cybersecurity
  testbed**다. 실제 군용 UGV 복제품이 아니며, RF 계층을 갖지 않고, 물리 GNSS
  수신기를 통합하지 않는다.
- "Attack" 에이전트는 로컬 테스트베드에서 **이미 확인된** 세 가지 시나리오를
  재현하는 **replay / simulation adapter**다. 실제 환경을 대상으로 하는 공격 기능,
  persistence, credential theft, destructive behavior는 포함하지 않는다. 목적은 방어
  파이프라인을 구동하여 탐지, hold, block 동작을 측정하는 것이다.
- 모든 에이전트는 로컬 Docker network / testbed 범위에 묶인다. live injection은
  기존 관례처럼 명시적인 `--confirm-live-testbed-only` 플래그 뒤에서만 허용한다.
- 결정론적 detector를 learned/trained AI model로 설명하지 않는다. **센서와 안전
  reflex는 rule + risk-score logic**이며, learned model이 아니라 결정론적 grounding
  layer로 설명한다.
- 아키텍처는 **LLM-brain + deterministic reflex**다. LLM(`anthropic` SDK)은
  **추론 코어**로서 시나리오 선택, multi-signal correlation reasoning, gap analysis,
  root-cause investigation, mitigation, closed-loop adaptive replanning을 담당한다.
  반면 **deterministic reflex**는 안전상 중요한 단 하나의 실시간 행동인 `/cmd_vel`
  hold/block만 소유한다. UGV command-safety loop는 비결정적이고 수 초가 걸릴 수
  있는 모델 호출을 기다릴 수 없기 때문이다. live mode에서 reflex는
  `--confirm-live-testbed-only`로 게이트되고 시뮬레이션 범위에 묶인 상태에서
  `/cmd_vel`에 hold/block을 능동적으로 발행할 수 있다. 이는 AIxCC에서 검증된
  패턴, 즉 **LLM이 제안하고 추론하며 deterministic oracle이 grounding/enforcement를
  담당하는 구조**를 따른다.

---

## 1. Two-Layer Testbed 안에서의 위치

```text
                         ┌───────────────────────── AI AGENT LAYER ─────────────────────────┐
                         │                                                                  │
                         │   [Orchestrator]  ── selects scenario, drives closed loop ──►    │
                         │        │                                                         │
                         │        ├─► [Attack Replay Agent] ──► scenario adapters A / B / C │
                         │        │                                                         │
                         │        └─► [Defense Orchestration Agents] ─► Command / State /   │
                         │                     Mission-GNSS / Correlation / Response-Report │
                         └───────────────────┬───────────────────────────┬──────────────────┘
                                             │ injects                   │ detect · correlate · hold/block
        ┌───────────── SIMULATION LAYER ─────▼──────┐       ┌────────────▼── SW-DEFINED UGV SECURITY LAYER ──┐
        │ QGC ─ MAVLink ─ ROS2 /cmd_vel ─ ROSbot/   │       │ MAVLink Bridge ─ Mission Audit ─ GNSS Integrity│
        │ Gazebo ─ /odometry/filtered ─ /scan ─ /tf │       │ ─ Correlation Engine ─ Command Hold / Block    │
        │ ─ RViz ─ MAVLink telemetry ─ QGC HUD      │       │ (Bridge/*.py, logs/*.log)                      │
        └───────────────────────────────────────────┘       └────────────────────────────────────────────────┘
```

에이전트 계층은 **Logical Two-Layer Testbed Architecture** 위에 놓이는
**closed-loop defense orchestration module**이다. **시뮬레이션 계층 (Simulation Layer)**의
signals를 관찰/replay하고, **소프트웨어 정의 UGV 보안 계층 (Software-Defined UGV
Security Layer)**의 Mission Audit, GNSS Integrity, Correlation Engine 의미론과 Command
Hold / Block 결정을 grounding한다. replay → detection → correlation → 자체 hold/block
decision → verification → incident report 흐름을 능동적으로 구동하며, 자체 detector와
correlation을 실행한다. Bridge 검증 의미론(Mission Audit / GNSS Integrity)과 로그를
재사용하지만 기존 Bridge 구성요소를 대체하지 않는다.

---

## 2. 확인된 공격 시나리오 (요약 → 표면)

| ID | Scenario | Primary surface | Testbed touchpoint |
| --- | --- | --- | --- |
| **A** | Unauthorized ROS2 DDS domain join + `/cmd_vel` command injection | ROS2 DDS (`ROS_DOMAIN_ID=17`) | `/cmd_vel`에 `Twist`를 publish하고 Bridge와 경쟁하며 `/odometry/filtered`를 recon 목적으로 읽음 |
| **B** | State / visualization topic manipulation | ROS2 state topics | `/odometry/filtered` 또는 `/scan`을 spoof하여 QGC HUD/RViz의 operator situational awareness를 저하시킴 |
| **C** | MAVLink Bridge input manipulation (mission + GNSS + manual) | MAVLink input to Bridge | malicious mission upload, `GPS_INPUT` spoof, abnormal `MANUAL_CONTROL`; hold/block 유도 |

이 세 가지는 **고정**이다. 에이전트 설계는 정확히 이 시나리오들을 replay하는 구조로
작성되어 있다.

---

## 3. 에이전트 구성과 역할

시스템은 하나의 orchestration package 안에서 Python process/thread로 동작하는
**1 LLM-backed main "brain" + deterministic sensor/reflex sub-agents** 구조다. 이 분리는
의도적이다. **LLM은 추론 코어**로서 scenario selection, multi-signal correlation
reasoning, gap analysis, root-cause investigation, mitigation recommendation, closed-loop
adaptive replanning을 담당한다. **deterministic tier는 grounding layer**로서 빠른 sensor
탐지와 실시간 **reflex** enforcement를 담당한다. 안전상 중요한 행동은 비결정적이고
수 초가 걸릴 수 있는 LLM round-trip에 의존할 수 없기 때문이다. LLM-driven path가
primary/default path이며, `--llm-backend none` deterministic fallback도 offline에서
reproducible verdict를 만들고 reflex가 계속 동작하게 한다. 즉 safety reflex는 LLM에
의존하지 않는다. 이는 AIxCC 패턴인 **LLM proposes and reasons; deterministic oracle
grounds and verifies**와 같다.

| Tier | Agent | Backing |
| --- | --- | --- |
| **Main (brain)** | Orchestrator / Supervisor | **LLM-core** (`anthropic` SDK) - scenario selection, gap analysis, adaptive closed-loop control; `--llm-backend none` deterministic fallback |
| Sub 1 | Recon / Discovery (S0) | Deterministic sensor |
| Sub 2 | Attack Replay (A/B/C adapters) | Deterministic; attacks validated live by teammates, thin replay harness |
| Sub 3 | Command Monitor | Deterministic sensor, safety-critical |
| Sub 4 | State Consistency | Deterministic sensor, safety-critical |
| Sub 5 | Mission-GNSS Guard | Deterministic sensor, safety-critical |
| Sub 6 | Correlation + Reflex | Deterministic reflex, safety-critical; 실시간 `hold_engaged` / `command_blocked` 소유 |
| Sub 7 | Reasoning & Report | **LLM-core** (`anthropic` SDK); attack-chain reasoning, root-cause, mitigation, incident report; deterministic template fallback |

> **보고서 프레이밍(§4.2/§4.3):** **LLM은 추론 코어**이고, deterministic
> sensor/reflex layer(rule + risk-score detection 및 실시간 hold/block)가 이를
> grounding한다. deterministic layer는 learned model이 아니라 grounding/oracle로,
> LLM tier는 reasoning brain으로 설명한다.

### 3.1 Orchestrator (`main_orchestrator`) - LLM brain

closed-loop lifecycle을 소유한다: scenario selection → attack dispatch → settle wait →
defense collection → correlation verdict → reasoning/report → verification. Scenario
selection과 gap analysis는 **LLM-driven**이며, `--llm-backend none`에서는 deterministic
fallback을 사용한다. run mode(`dry-run` vs `live`), LLM backend selector, round accounting도
관리한다.

### 3.2 Attack Replay Agent (offensive-side, simulation-bound)

세 가지 scenario adapter를 교체 가능한 형태로 가진 단일 agent다. 새로운 공격을 만들지
않고 A/B/C를 parameterized input으로 replay한다.

| Adapter | Replays | Reuses (existing) | Injection channel |
| --- | --- | --- | --- |
| **Scenario A Adapter** | `/cmd_vel` hijacking | ROS2 `rclpy` publisher on `/cmd_vel`; recon subscribe `/odometry/filtered` | ROS2 DDS, `ROS_DOMAIN_ID=17` |
| **Scenario B Adapter** | odometry / scan spoofing | `rclpy` publisher on `/odometry/filtered`, `/scan` | ROS2 DDS |
| **Scenario C Adapter** | mission / GNSS / manual-control manipulation | `Bridge/tools/send_mission_upload.py`, `send_gps_input.py`, `send_manual_control.py` (existing MAVLink injectors, port 14551) | MAVLink to Bridge |

### 3.3 Defense Orchestration Agents (defensive-side)

다섯 agent가 협력한다. 앞의 네 개는 **deterministic grounding layer**로서 sensor와
reflex를 구성하고, 다섯 번째는 **LLM reasoning core**로서 root-cause, attack-chain
reasoning, mitigation, report를 담당한다. safety reflex(hold/block enforcement)는
deterministic으로 유지되며 LLM에 의존하지 않는다. LLM은 grounded signals와 verdict
위에서 추론하고 orchestrator에서 scenario selection과 gap analysis를 수행하지만,
deterministic block을 **절대 override하지 않는다**.

| Agent | Directly detects / does | Reuses (existing) | Emits |
| --- | --- | --- | --- |
| **Command Monitor Agent** | external `/cmd_vel` publisher set, publish rate, velocity-envelope(linear/angular) anomaly를 직접 탐지 | ROS2 graph introspection, `/cmd_vel` | `AnomalySignal`: unexpected publisher, rate spike, envelope breach |
| **State Consistency Agent** | `/odometry/filtered`, `/tf`, `/scan` 사이의 inconsistency를 직접 탐지 | ROS2 topic subscriptions | `AnomalySignal`: odom jump vs tf, phantom/hidden `/scan` returns |
| **Mission-GNSS Guard Agent** | Bridge Mission Audit / GNSS Integrity 결과를 읽고 signal 생성 | `Bridge/mission_audit.py`, `Bridge/gnss_integrity.py`; `logs/mission_audit.log`, `logs/gnss_integrity.log` tail | `AnomalySignal`: rejected mission, `spoof_jump`, `poor_fix` |
| **Correlation Agent** | 수집된 `AnomalySignal`을 자체 deterministic scoring으로 결합하여 `risk_score`와 `hold_engaged` / `command_blocked` decision 생성 | **new agent-layer aggregation logic**; `logs/correlation_event.log`는 corroborating evidence로만 읽으며 node-coupled `Bridge/correlation_engine.py:CorrelationEngine`을 import하지 않음 | `CorrelationVerdict`; Bridge 없이 dry-run에서 deterministic verdict 생성 |
| **Reasoning & Report Agent** | **LLM-core**: grounded verdict + signals를 바탕으로 attack-chain hypothesis, root-cause, mitigation을 추론하고 incident report 조립 | verdict + timeline + `evidence_refs`; `anthropic` LLM primary path, `--llm-backend none` deterministic template fallback | attack-chain + root-cause reasoning, recovery actions, `IncidentReport` (Markdown/JSON) |

**Command Hold / Block**은 LLM이 아니라 defense controller가 소유하는 deterministic
function이다. Correlation Agent는 매 round마다 `hold_engaged` / `command_blocked`
**decision**을 만든다. **Enforcement는 mode-split**이다. **dry-run**에서는 decision만
기록하고, **live mode**에서는 `--confirm-live-testbed-only` 뒤에서 orchestrator가
active hold/block(`/cmd_vel`에 zero-Twist hold publish)을 발행할 수 있다. 이 active block은
시뮬레이션 범위에 묶이며, `/cmd_vel` publisher라는 점에서 Scenario A와 구조적으로
닮아 있어 Bridge의 inline enforcement 위에 놓이는 **authoritative-override
demonstration**으로 문서화한다.

---

## 4. Orchestration Flow (closed loop, per round)

```text
S0  Discover        : ROS2 topics/publishers + Bridge ports를 enumerate하여 surface mapping
S1  Select scenario : LLM brain이 A / B / C 선택(team scenario files 우선, 없으면 vuln-driven); --llm-backend none deterministic fallback
S2  Plan attack     : adapter parameters(rate, target topic, spoof value, mission/gps payload) binding
S3  Inject          : Attack Replay Agent가 selected adapter 실행(dry-run = simulate; live = gated)
        │
        ▼  (settle wait ~4s)
S4  Detect+Correlate: Defense sensors가 AnomalySignals 수집; Correlation reflex가 자체 deterministic risk_score + hold/block verdict 생성
S5  Gap analysis    : LLM brain이 expected_guard/expected_signal과 observed를 비교하고 missed detection flag
S6  Recommend       : Reasoning & Report Agent(LLM-core)가 attack-chain + root-cause를 추론하고 recovery / mitigation 제안(code auto-apply 없음)
S7  Verify + Report : dry-run은 hold/block decision 기록; gated live mode는 active block(zero-Twist hold)을 발행하고 /cmd_vel hold 확인; incident report 작성
        │
        └──► interactive confirmation gate → next round
```

- **dry-run mode**: adapter는 injection을 *simulate*하고 defense path는 synthetic
  signals로 exercise한다. live testbed가 필요 없는 안전한 기본값이다.
- **live mode**: adapter가 실제 로컬 injection을 수행하고 defense controller가 active
  hold/block(`/cmd_vel` zero-Twist hold)을 enforce할 수 있다. 둘 다
  `--confirm-live-testbed-only`가 필요하고 시뮬레이션 범위에 묶인다. dry-run은 decision만
  기록한다. GNSS/manual-control injector는 이미 동작하지만, mission live-injection은
  실제 MAVLink mission handshake가 필요하고 port auto-discovery는 알려진 gap이다(§9).

---

## 5. Attack ↔ Defense Traceability (1:1, 보고서 4.2/4.3용)

| Attack scenario | Detecting defense agent(s) | Guard mechanism | Expected verdict / evidence |
| --- | --- | --- | --- |
| **A** `/cmd_vel` injection | Command Monitor → Correlation | unexpected-publisher + rate/envelope check → risk score | `hold_engaged`, `command_blocked`, `/cmd_vel` clamped `0.0` in `correlation_event.log` |
| **B** odom/scan spoof | State Consistency → Correlation | odom↔tf / scan consistency check → risk score | inconsistency flagged; operator-awareness degradation reported |
| **C** mission/GNSS/manual | Mission-GNSS Guard → Correlation | Mission Audit reject + GNSS Integrity classify(`spoof_jump`/`poor_fix`) | `mission_audit.log` / `gnss_integrity.log` rejections; `correlation_event.log`의 `risk_score`, `hold_engaged` |

이 표는 보고서 **§4.3**의 backbone이다. 모든 confirmed attack은 named defensive agent와
concrete evidence artifact에 연결된다. **agent-layer Correlation Agent**가
`risk_score` / `hold_engaged` / `command_blocked` verdict를 소유하며,
`correlation_event.log` entries는 이를 **corroborate**할 뿐 source of truth가 아니다.

---

## 6. Agent Interface Contract (개념 - Codex가 코드로 채움)

모든 agent는 orchestrator가 조합할 수 있도록 공통 message shape를 사용한다. 아래는
**Batch 1 dataclass contracts**(`agents/contracts.py`)의 schema 설명이다.

- **AttackAction**: `run_id`, `round_id`, `scenario_id`, `surface`, `adapter`,
  `parameters`, `mode` (`dry-run`|`live`), `created_at`,
  `confirm_live_testbed_only`
- **AnomalySignal**: `run_id`, `round_id`, `scenario_id`, `source_agent`, `surface`,
  `signal_type`, `severity`, `observed_value`, `expected`, `observed_at`,
  `evidence_refs`, `fresh_after`, `confidence`
- **CorrelationVerdict**: `run_id`, `round_id`, `scenario_id`, `risk_score`,
  `hold_engaged`, `command_blocked`, `contributing_signals`, `decided_at`,
  `evidence_refs`, `reason`
- **IncidentReport**: `run_id`, `round_id`, `scenario_id`, `timeline`, `root_cause`,
  `guard_hit`, `recovery_actions`, `evidence_refs`, `llm_backend`, `generated_at`,
  `status`

**Stale-log false-positive protection은 load-bearing 요구사항이다.** 세 Bridge log는
append-only이며 여러 run에 걸쳐 남기 때문에, naive tail은 오래된 event를 현재 round의
결과로 오인할 수 있다. 따라서 모든 signal/verdict는 scoped되어야 한다.

- `run_id` / `round_id`: orchestrator가 run/round 시작 시 발급하며 모든
  `AnomalySignal`과 `CorrelationVerdict`에 stamp한다.
- `fresh_after`: 이 timestamp보다 오래된 log line은 stale로 무시한다.
- `evidence_refs`: 각 signal의 explicit source-log location
  (예: `{ "log": "logs/correlation_event.log", "line": N, "ts": ... }`)을 담아 모든
  claim을 특정 line으로 trace/re-verify할 수 있게 한다.

Evidence contract(원시 log를 재생성하거나 편집하지 말 것):
`logs/mission_audit.log`, `logs/gnss_integrity.log`, `logs/correlation_event.log`는
Mission-GNSS Guard와 Correlation agent의 read-only source of truth다. Agent-produced
artifacts(incident reports, run traces)는 `agents/reports/` 아래 새 JSONL/Markdown으로
작성하고, Bridge evidence logs는 편집하지 않는다.

---

## 7. Technology Stack

| Concern | Choice | Notes |
| --- | --- | --- |
| Language | Python 3.10 | Bridge(`cpython-310`)와 일치 |
| ROS2 interface | `rclpy` (Humble) | `/cmd_vel`, `/odometry/filtered`, `/scan`, `/tf`; `ROS_DOMAIN_ID=17` |
| MAVLink interface | `pymavlink` | `Bridge/tools/send_*.py` injector 재사용(default `--port 14551`, Bridge listens on `BRIDGE_LOCAL_PORT`, default 14551) |
| Defense logic | Bridge reuse + **new agent-layer detectors/correlation** | Mission Audit / GNSS Integrity semantics는 Bridge modules + logs로 재사용. Agent-level correlation, `/cmd_vel` external-publisher detection, state-consistency detection은 **new deterministic agent logic**이며 node-coupled `CorrelationEngine` 재구현이 아님. `logs/correlation_event.log`는 corroborating evidence다. Bridge logic을 무분별하게 재구현하지 않는다. |
| Orchestration | plain Python state machine (`agents/main_orchestrator.py`) | CLI flags: `--rounds`, `--dry-run` / `--live`, `--confirm-live-testbed-only`, `--llm-backend` |
| LLM backend | `anthropic` Python SDK(`pip install anthropic`), pluggable; **LLM-on primary path**, `none`은 deterministic-reflex fallback | `client.messages.create(model=..., max_tokens=..., messages=[...])`. Orchestrator brain(scenario selection, gap analysis)과 Reasoning & Report agent(attack-chain, root-cause, mitigation)를 구동한다. safety reflex는 `--llm-backend none`에서도 완전히 동작해야 한다. Model id는 env `AGENT_LLM_MODEL`, default `claude-haiku-4-5`; demo quality에는 `claude-opus-4-8` / `claude-fable-5`. `claude-fable-5`에서는 `thinking` param을 생략하고, `response.stop_reason == "refusal"`을 content read 전에 guard하며 server-side fallback을 opt-in한다. 무거운 Claude Agent SDK / Managed Agents는 사용하지 않는다. |
| Evidence | JSONL + Markdown under `agents/reports/` | deterministic, reproducible |

---

## 8. Planned Directory Layout (Codex target)

```text
agents/
  README.md                 # this design (do not put code here)
  main_orchestrator.py      # closed-loop state machine (S0-S7)
  attack/
    replay_agent.py         # Attack Replay Agent shell
    adapter_a_cmdvel.py     # Scenario A adapter
    adapter_b_state.py      # Scenario B adapter
    adapter_c_mavlink.py    # Scenario C adapter (wraps Bridge/tools/send_*.py)
  defense/
    command_monitor.py
    state_consistency.py
    mission_gnss_guard.py
    correlation_agent.py    # deterministic aggregation of AnomalySignals -> risk_score + hold/block verdict; log = corroborating evidence
    command_hold_block.py   # deterministic hold/block enforcement; active zero-Twist hold only in gated live mode
    response_report.py
  scenarios/                # team scenario .md files (front matter: scenario_id, surface, expected_guard, expected_signal)
  reports/                  # generated incident reports / run traces (JSONL + Markdown)
```

위 module boundary는 **필수**다. attack과 defense concern을 한 파일로 합치지 않고,
`agents/` 안에서 Bridge logic을 재구현하지 않는다.

---

## 9. Known Gaps / Assumptions (carry forward, 과장 금지)

1. **External ROS2 `/cmd_vel` anomaly detection + agent correlation은 new agent-layer
   logic이다.** MAVLink **MANUAL_CONTROL high-command evaluation path는 Bridge에 이미
   존재**한다(`ros2_mavlink_bridge.py`: `MANUAL_CONTROL` →
   `publish_cmd_vel(source="MANUAL_CONTROL")` → `correlation_engine.evaluate_command`).
   외부 ROS2 `/cmd_vel` publisher/rate/envelope anomaly(Scenario A)에 대한 Bridge path는
   없다. **Command Monitor Agent가 이를 탐지하고 agent-layer Correlation Agent가
   verdict로 scoring한다.** 이는 node-coupled Bridge engine 변경이 아니라 new
   deterministic agent logic이다.
2. **Scenario C mission live-injection**은 proper MAVLink mission handshake가 아직
   필요하다. `Bridge/tools/send_mission_upload.py`는 현재 `MISSION_COUNT`,
   `time.sleep(0.3)`, then items 방식이다. robust handshake client라고 설명하지 않는다.
   `MISSION_REQUEST`/`MISSION_ACK` round-trip은 TODO다. GNSS와 manual-control live
   injection은 이미 동작한다.
3. **Port auto-discovery는 wired되어 있지 않다.** Bridge listen port는
   `BRIDGE_LOCAL_PORT`로 configurable(default `14551`)이고 `tools/send_*.py`도 모두
   `--port 14551`을 default로 둔다. 즉 값은 defaulted이지 hardcoded가 아니다. gap은
   **S0 discovery / environment propagation of the port into the adapters** 미구현이다.
4. **Scenario B** consistency checks(odom↔tf, scan plausibility)는 existing Bridge
   counterpart가 없는 **new logic**이다. detector heuristic으로 범위를 잡고 learned
   model로 설명하지 않는다.
5. **Grounding boundary는 hard rule이다.** **safety reflex**(실시간 `hold_engaged` /
   `command_blocked` enforcement와 모든 sensor)는 deterministic이며 LLM call에
   의존해서는 안 된다. `--llm-backend none`은 reflex와 reproducible verdict를 offline에서
   완전히 동작시켜야 한다. **LLM은 reasoning core**(scenario selection, correlation
   reasoning, gap analysis, root-cause, mitigation)이며 primary path이지만 grounded
   verdict 위에서 추론하고 deterministic block을 **절대 override하지 않는다**.
   LLM = brain; deterministic = reflex/oracle.

불확실한 내용은 code와 docs에 `Assumption` / `Needs human confirmation` / `TODO`로
표시한다. test result, screenshot, log, performance number를 만들어내지 않는다.

---

## 10. Codex 구현 배치

**AGENTS.md two-phase workflow**(Plan Review → Plan Execute)를 따른다. 아래 각 batch는
작고 독립적으로 review 가능해야 한다. **batch를 합치지 않는다.** 각 batch는 수정 전
expected files를 나열하고, 변경 파일에 대해 `python3 -m py_compile`을 실행하며, 기존
env/port/topic behavior를 보존한다.

> **Phase 1(Plan Review) first:** 코드를 작성하기 전에 Codex는 이 설계를 adversarial
> review한다. missing assumptions, unsafe scope, weak detection heuristics, two-layer
> mismatch를 severity 순으로 반환한다. Claude가 보완한 뒤 execution을 시작한다.

Batch order는 **defense-first**다. 시나리오 A/B/C는 teammates가 live validation 중이므로
Attack Replay adapters는 뒤쪽(Batch 7)으로 밀었다. **Correlation Agent는 ROS2 detector보다
먼저** 구축한다. 이는 pure deterministic logic이어서 Batch 2 real Mission-GNSS signals와
synthetic `AnomalySignal`로 offline 검증이 가능하기 때문이다. 반면 Command Monitor /
State Consistency detector는 live ROS2 stack 검증이 필요하다. 이렇게 하면 detect →
correlate → verdict slice를 일찍 시연할 수 있다. Deterministic sensors + reflex(Batches
1-4)는 **grounding layer**이며, **LLM reasoning core는 Batch 5(Reasoning & Report)와
Batch 6(orchestrator brain)**에서 grounded slice 위에 올라간다.

> **Prerequisite(contract patch, before Batch 2):** `agents/contracts.py`에만
> `AnomalySignal` 첫 필드로 `signal_id: str`을 추가하고,
> `CorrelationVerdict.contributing_signals`를 `list[str]`로 바꾼다. 이는 verdict가
> 정확히 어떤 signal에 근거했는지 reference하게 한다.

> **Prerequisite(contract patch, before Batch 5):** `agents/contracts.py`에만
> `IncidentReport` reasoning fields를 additive로 추가한다. 모두 default가 있으며
> backward-compatible이어야 한다: `attack_chain: list[str]`, `llm_rationale: str`,
> `reasoning_source: str` (`"llm"` | `"template"`). 이 필드는 deterministic reflex
> verdict를 바꾸지 않고 LLM reasoning-core output을 담는다.

**Batch 1 - Skeleton + contracts + no-op orchestrator.** Done. 아래 finalized spec 참조.
Expected files: `agents/__init__.py`, `agents/contracts.py`, `agents/main_orchestrator.py`.

**Batch 2 - Mission-GNSS log guard.** Done. `logs/mission_audit.log`와
`logs/gnss_integrity.log`를 read-only로 tail하고(§6의 `fresh_after`/`run_id` scope),
rejected mission, `spoof_jump`, `poor_fix`에 대한 `AnomalySignal`(`signal_id` 포함)을
emit한다. `Bridge/mission_audit.py` / `Bridge/gnss_integrity.py` validation semantics를
재사용하고 재구현하지 않는다. Expected file: `agents/defense/mission_gnss_guard.py`.

**Batch 3 - Correlation Agent + Command Hold/Block decision.** Done. Pure agent-layer risk
scoring, `CorrelationVerdict`, signal-id contribution tracking, deterministic hold/block
decision helper가 landed. 수집된 `AnomalySignal`을 **new deterministic agent-layer
scoring**(module constants의 weights/thresholds)으로 결합하여 `CorrelationVerdict`를
만든다(`risk_score`, `hold_engaged`, `command_blocked`, `reason`,
`contributing_signals` = driving `signal_id`s, `evidence_refs`). Bridge 없이 dry-run에서
deterministic verdict를 생성해야 하며, Batch 2 Mission-GNSS signals와 synthetic
`AnomalySignal`로 offline 검증한다. `logs/correlation_event.log`는 corroborating
evidence로만 읽는다. node-coupled `CorrelationEngine`을 import하지 않는다.
`command_hold_block.py`는 deterministic decision→action mapping을 담는다. Expected files:
`agents/defense/correlation_agent.py`, `agents/defense/command_hold_block.py`.

**Batch 4 - Command Monitor + State Consistency detectors (new deterministic logic).** Done.
Guarded ROS2 imports와 JSONL `AnomalySignal` output을 가진 offline-testable deterministic
`/cmd_vel`, odom/tf, scan anomaly producers가 landed. Command Monitor는 external
`/cmd_vel` publisher/rate/envelope anomaly를 직접 탐지하고, State Consistency는
odom↔tf↔scan inconsistency를 직접 탐지한다. 둘 다 `signal_id`를 가진 `AnomalySignal`을
emit하고 Batch 3 Correlation Agent가 이를 consume한다. deterministic detector heuristic으로
label하고 learned-model claim을 하지 않는다. Offline demo/fixture path가 있으며 live
ROS2 stack validation은 deferred 상태다. Expected files:
`agents/defense/command_monitor.py`, `agents/defense/state_consistency.py`.

**Batch 5 - Reasoning & Report agent (LLM-core).** Done. `IncidentReport` reasoning fields,
untrusted-evidence prompt boundary, Anthropic optional path, deterministic template fallback,
`agents/reports/` JSONL/Markdown report writing이 landed. verdict + timeline +
`evidence_refs`를 consume하고, grounded evidence 위에서 `anthropic` LLM을 **primary** path로
사용해 attack-chain hypothesis, root-cause, mitigation을 추론한 뒤 `IncidentReport`를
조립한다. `--llm-backend none`에서도 deterministic template fallback은 완전히 동작해야
하고, 어떤 path도 deterministic reflex verdict를 override할 수 없다. Expected file:
`agents/defense/response_report.py`.

**Batch 6 - Orchestrator wiring (dry-run loop) + LLM brain + gated live active-block.**
Done. Single-command closed-loop dry-run orchestration, LLM/default-model selection with
deterministic fallback, gap analysis, run traces, gated live enforcement attempts가 landed.
Real defense agents를 S0-S7에 연결하고 `agents/reports/` 아래 reproducible dry-run trace를
생성한다. **LLM brain**을 wired하여 backend가 설정되면 S1 scenario selection과 S5 gap
analysis를 LLM-driven으로 수행하고, `--llm-backend none`에서는 deterministic fallback을
사용한다. 매 round마다 gated live-enforcement decision을 기록한다. `--live` +
`--confirm-live-testbed-only` mode에서는 orchestrator가 enforcement-attempt event를
기록하고, `rclpy`/`geometry_msgs`가 없으면 `deferred` event를 남긴다. 실제 zero-Twist
`/cmd_vel` publish는 Batch 7로 이동했다. Dry-run은 publish 없이 decision만 기록한다.
Deterministic reflex verdict가 authoritative이며 LLM은 이를 override하지 않는다. Default
`--llm-backend`는 env-configured model(`AGENT_LLM_MODEL`, default `claude-haiku-4-5`)이고,
`--llm-backend none`은 explicit deterministic-reflex fallback이다. `Bridge/logs/*.log`는
편집하지 않는다. **Single-command requirement:** `python3 -m agents.main_orchestrator
--rounds N --dry-run`(LLM primary) 및 offline fallback `--llm-backend none`으로 전체 closed
loop가 manual pre-step 없이 실행된다. Expected files: `agents/main_orchestrator.py`,
`agents/defense/response_report.py`.

**Batch 7 - Thin Attack Replay adapters + active `/cmd_vel` hold publisher.** Done.
Deterministic replay adapters, self-contained dry-run Scenario C evidence, gated live adapter
paths, safe allowlisted Adapter C subprocess wrapping, `--live --confirm-live-testbed-only`
뒤의 active zero-Twist hold publishing이 landed. `agents/attack/replay_agent.py`와 adapters;
Adapter C는 `Bridge/tools/send_*.py`를 wrap한다(dry-run simulate, live gated). Adapters A/B는
`rclpy` publishers다. Batch 6의 gated live-enforcement path가 호출하는 active zero-Twist
`/cmd_vel` hold publisher도 구현한다. 이 기능은 `rclpy` publisher infra를 공유하고 live
stack validation이 필요하므로 Batch 7에 묶었다. Teammates가 live attack validation을
소유하므로 thin하게 유지한다.

**Batch 8 - Docs sync / Korean mirror.** 이 documentation batch에서 진행 중이다. 이
README status section을 갱신하고 `docs/agents_KR.md`를 Korean mirror로 작성한다.
Mirror는 **LLM-brain + deterministic-reflex** framing을 유지한다. LLM reasoning core는
scenario selection / correlation reasoning / gap analysis / root-cause / mitigation을
담당하고, deterministic sensors + real-time hold/block reflex가 safety-critical decision을
소유하며 LLM은 이를 override하지 않는다. Gated live active-block도 이 범위에 포함한다.
AGENTS.md terminology(Simulation Layer, Software-Defined UGV Security Layer, Mission Audit,
GNSS Integrity, Correlation Engine, Command Hold / Block)와 맞춘다.

### Implementation Status (after Batches 1-7)

Deterministic closed loop와 LLM-brain fallback은 다음 single command dry-run으로
시연되어 있다: `python3 -m agents.main_orchestrator --rounds N --dry-run`, 그리고 offline
fallback `--llm-backend none`. Stable dry-run core는 다음과 같다:
**A(1.0, block) · B(0.48, none) · C(1.0, block)**.

Live ROS2/MAVLink injection paths와 active zero-Twist `/cmd_vel` hold는
`--live --confirm-live-testbed-only` 뒤에서만 동작하도록 구현되어 있으며,
`rclpy`/message-package dependency guard와 기존 Bridge MAVLink tools를 위한 safe subprocess
wrapping을 갖는다. 이 환경에서는 검증을 주장하지 않으며, team's live stack validation이
대기 상태다.
이 상태는 **Logical Two-Layer Testbed Architecture**를 유지한다. 즉 **시뮬레이션 계층
(Simulation Layer)** signals를 관찰/replay하고, **소프트웨어 정의 UGV 보안 계층
(Software-Defined UGV Security Layer)**이 Mission Audit, GNSS Integrity, Correlation
Engine semantics, Command Hold / Block decisions를 소유한다.

### Batch 1 - finalized spec

**Expected files:** `agents/__init__.py`, `agents/contracts.py`, `agents/main_orchestrator.py`.

**Constraints:**
- **`Bridge` import, `rclpy`/ROS2 import, `pymavlink` import, `anthropic` import 금지.**
- live injection 없음; `Bridge/logs/*.log` read/write 없음.
- `contracts.py`는 §6의 네 dataclass를 정확히 정의한다.
- `main_orchestrator.py`는 **S0-S7 with stubs**를 걷고 deterministic **no-op**
  `CorrelationVerdict`(`risk_score=0.0`, `hold_engaged=False`, `command_blocked=False`)와
  no-op `IncidentReport`를 생성한다.
- CLI defaults: `--dry-run` default(`--live` 아님); `--llm-backend none` default;
  `--live`는 `--confirm-live-testbed-only` 없으면 error로 종료한다.
- `--rounds N`은 per-round `run_id`/`round_id`와 함께 stub S0-S7을 N회 반복한다.

**Validation(둘 다 통과해야 함):**
```bash
python3 -m py_compile agents/__init__.py agents/contracts.py agents/main_orchestrator.py
python3 -m agents.main_orchestrator --rounds 1 --dry-run --llm-backend none
```

---

## 11. Definition of Done (contest criterion "AI 에이전트 아키텍처, 25점")

- Agent **roles**, **cooperation structure**, **tech stack**, **diagram**이 문서화되어
  있고(이 README) 보고서 §4.2 / §4.3에 반영된다.
- Attack ↔ Defense traceability table(§5)이 real evidence artifacts로 뒷받침된다.
- **Prototype**은 dry-run에서 end-to-end로 실행된다. **LLM reasoning core**(scenario
  selection, gap analysis, attack-chain/root-cause report)는 primary path에서 시연되고,
  deterministic `--llm-backend none` fallback도 offline에서 reflex verdict를 생성한다.
  Live ROS2/MAVLink injection과 active `/cmd_vel` hold는 gated 및 dependency-guarded이며,
  live-stack validation은 deferred 상태다.
- **Single-command execution:** 전체 closed-loop pipeline은 manual pre-step 없이 하나의
  command(`python3 -m agents.main_orchestrator …`)로 실행된다. 기본은 LLM-driven이고,
  `--llm-backend none`은 deterministic reflex path다. live enforcement는
  `--live --confirm-live-testbed-only` 뒤에서만 가능하다.
- No overclaiming: **LLM은 reasoning core**이고 deterministic sensor/reflex layer(rule +
  risk-scoring)에 의해 grounded된다. learned model이라고 주장하지 않는다. safety reflex가
  block을 enforce하며 LLM은 이를 override하지 않는다. testbed는 software-defined 및
  simulation-bound로 설명한다.
