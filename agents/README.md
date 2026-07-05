<div align="right">
  <strong>🇺🇸 English</strong> | <a href="../docs/agents_KR.md">🇰🇷 한국어</a>
</div>

# AI Agent Architecture — Attack Replay & Closed-Loop Defense Orchestration

This directory defines the **AI agent layer** of the DAH_2026 software-defined UGV/GCS
cybersecurity testbed. It backs report sections **4.2 (Attack-related AI Agent)** and
**4.3 (Defense-related AI Agent)**, and supports the preliminary evaluation criterion
**"AI 에이전트 아키텍처 (25점)"**.

> **Design document only.** This README is the architecture, orchestration, and
> interface specification. It is written by the orchestrator (Claude) and is the
> implementation brief for the executor (Codex). No agent code is authored here —
> see [§10 Codex Implementation Batches](#10-codex-implementation-batches).

---

## 0. Framing and Safety Boundaries

- This is a **Defense UGV-inspired, software-defined UGV/GCS cybersecurity testbed**.
  It is **not** a real military UGV replica, has **no RF layer**, and integrates
  **no physical GNSS receiver**.
- The "Attack" agents are **replay / simulation adapters** that reproduce three
  **already-confirmed** scenarios against the local testbed only. They contain **no**
  real-world offensive capability, no persistence, no credential theft, no destructive
  behavior. They exist to **exercise the defense pipeline** so its detection, hold, and
  block behavior can be measured.
- All agents are bound to the local Docker network / testbed. Live injection must be
  gated behind an explicit `--confirm-live-testbed-only` flag (existing convention).
- Do not describe the deterministic detectors as learned/trained AI models. The **sensors
  and the safety reflex are rule + risk-score logic**; describe them as the deterministic
  grounding layer, not "learned models".
- The architecture is **LLM-brain + deterministic reflex**. The LLM (via the `anthropic`
  SDK) is the **reasoning core**: it drives scenario selection, multi-signal correlation
  reasoning, gap analysis, root-cause investigation, mitigation, and adaptive replanning of
  the closed loop. A **deterministic reflex** owns only the one safety-critical action — the
  real-time hold/block on `/cmd_vel` — because a UGV command-safety loop cannot wait on a
  non-deterministic, multi-second model call. In live mode the reflex can **actively** issue
  the hold/block on `/cmd_vel`, gated behind `--confirm-live-testbed-only` and
  simulation-bound. This mirrors the AIxCC-proven pattern: the **LLM proposes and reasons; a
  deterministic oracle grounds and enforces.**

---

## 1. Position in the Two-Layer Testbed

```
                         ┌───────────────────────── AI AGENT LAYER ─────────────────────────┐
                         │                                                                   │
                         │   [Orchestrator]  ── selects scenario, drives closed loop ──►     │
                         │        │                                                          │
                         │        ├─► [Attack Replay Agent] ──► scenario adapters A / B / C  │
                         │        │                                                          │
                         │        └─► [Defense Orchestration Agents] ─► Command / State /      │
                         │                     Mission-GNSS / Correlation / Response-Report   │
                         └───────────────────┬───────────────────────────┬──────────────────┘
                                             │ injects                    │ detect · correlate · hold/block
        ┌───────────── SIMULATION LAYER ─────▼──────┐        ┌────────────▼── SW-DEFINED UGV SECURITY LAYER ──┐
        │ QGC ─ MAVLink ─ ROS2 /cmd_vel ─ ROSbot/   │        │ MAVLink Bridge ─ Mission Audit ─ GNSS Integrity │
        │ Gazebo ─ /odometry/filtered ─ /scan ─ /tf │        │ ─ Correlation Engine ─ Command Hold / Block     │
        │ ─ RViz ─ MAVLink telemetry ─ QGC HUD      │        │ (Bridge/*.py, logs/*.log)                        │
        └────────────────────────────────────────────┘        └─────────────────────────────────────────────────┘
```

The agent layer is a **closed-loop defense orchestration module** layered **on top of** the
Bridge security layer. It actively drives the defense loop — replay → detection → correlation
→ **its own** hold/block decision → verification → incident report — and runs its own
detectors and correlation. It **reuses** Bridge validation semantics (Mission Audit / GNSS
Integrity) and logs rather than reimplementing them, and does not replace any existing Bridge
component.

---

## 2. Confirmed Attack Scenarios (recap → surfaces)

| ID | Scenario | Primary surface | Testbed touchpoint |
| --- | --- | --- | --- |
| **A** | Unauthorized ROS2 DDS domain join + `/cmd_vel` command injection | ROS2 DDS (`ROS_DOMAIN_ID=17`) | Publishes `Twist` to `/cmd_vel`, competes with Bridge; reads `/odometry/filtered` for recon |
| **B** | State / visualization topic manipulation | ROS2 state topics | Spoofs `/odometry/filtered` and/or `/scan` to degrade operator situational awareness (QGC HUD, RViz) |
| **C** | MAVLink Bridge input manipulation (mission + GNSS + manual) | MAVLink input to Bridge | Malicious mission upload, `GPS_INPUT` spoof, abnormal `MANUAL_CONTROL`; drives hold/block |

These three are **fixed**. The agent design is built around replaying exactly these.

---

## 3. Agent Roster and Roles

The system is **1 LLM-backed main "brain" + deterministic sensor/reflex sub-agents**, run as
Python processes/threads inside one orchestration package. This split is deliberate. The
**LLM is the reasoning core**: scenario selection, multi-signal correlation reasoning, gap
analysis, root-cause investigation, mitigation recommendation, and adaptive replanning of the
closed loop are where judgment adds real value, and the LLM (via the `anthropic` Python SDK)
owns them. The **deterministic tier is the grounding layer** — fast sensors that detect
anomalies and a real-time **reflex** that enforces the hold/block — because the one
safety-critical action cannot depend on a non-deterministic, multi-second LLM round-trip.
The LLM-driven path is the **primary, default path**; a deterministic fallback
(`--llm-backend none`) still produces a reproducible verdict and keeps the reflex working
offline, so the safety reflex never depends on the LLM. This is the AIxCC pattern: **the LLM
proposes and reasons; a deterministic oracle grounds and verifies.**

| Tier | Agent | Backing |
| --- | --- | --- |
| **Main (brain)** | Orchestrator / Supervisor | **LLM-core** (`anthropic` SDK) — scenario selection, gap analysis, adaptive closed-loop control; deterministic fallback with `--llm-backend none` |
| Sub 1 | Recon / Discovery (S0) | Deterministic sensor |
| Sub 2 | Attack Replay (A/B/C adapters) | Deterministic (attacks validated **live by teammates**; thin replay harness) |
| Sub 3 | Command Monitor | Deterministic sensor (safety-critical) |
| Sub 4 | State Consistency | Deterministic sensor (safety-critical) |
| Sub 5 | Mission-GNSS Guard | Deterministic sensor (safety-critical) |
| Sub 6 | Correlation + Reflex | Deterministic reflex (safety-critical — owns real-time `hold_engaged` / `command_blocked`) |
| Sub 7 | Reasoning & Report | **LLM-core** (`anthropic` SDK) — attack-chain reasoning, root-cause, mitigation, incident report; deterministic template fallback |

> **Report framing (§4.2/§4.3):** the **LLM is the reasoning core** (scenario selection,
> correlation reasoning, gap analysis, root-cause, mitigation) grounded by a **deterministic
> sensor/reflex layer** (rule + risk-score detection and the real-time hold/block). Describe
> the deterministic layer as the grounding/oracle, not a learned model, and the LLM tier as
> the reasoning brain — the same **LLM-proposes / oracle-verifies** pattern used by AIxCC CRSs.

### 3.1 Orchestrator (`main_orchestrator`) — LLM brain
Owns the closed-loop lifecycle: scenario selection → attack dispatch → settle wait →
defense collection → correlation verdict → reasoning/report → verification. Scenario
selection and gap analysis are **LLM-driven** (deterministic fallback with `--llm-backend
none`). Holds the run mode (`dry-run` vs `live`), the LLM backend selector, and round
accounting.

### 3.2 Attack Replay Agent (offensive-side, simulation-bound)
A single agent with **three interchangeable scenario adapters**. It never invents new
attacks; it replays A/B/C with parameterized inputs.

| Adapter | Replays | Reuses (existing) | Injection channel |
| --- | --- | --- | --- |
| **Scenario A Adapter** | `/cmd_vel` hijacking | ROS2 `rclpy` publisher on `/cmd_vel`; recon subscribe `/odometry/filtered` | ROS2 DDS, `ROS_DOMAIN_ID=17` |
| **Scenario B Adapter** | odometry / scan spoofing | `rclpy` publisher on `/odometry/filtered`, `/scan` | ROS2 DDS |
| **Scenario C Adapter** | mission / GNSS / manual-control manipulation | `Bridge/tools/send_mission_upload.py`, `send_gps_input.py`, `send_manual_control.py` (existing MAVLink injectors, port 14551) | MAVLink to Bridge |

### 3.3 Defense Orchestration Agents (defensive-side)
Five cooperating agents. The first four are the **deterministic grounding layer** — sensors
that detect and a reflex that decides the real-time hold/block; the fifth is the **LLM
reasoning core** (root-cause, attack-chain reasoning, mitigation, report). The safety reflex
(hold/block enforcement) stays deterministic and never depends on the LLM; the LLM reasons
*over* the grounded signals and verdict — and, in the orchestrator, selects scenarios and runs
gap analysis — but it can **never override** the deterministic block.

| Agent | Directly detects / does | Reuses (existing) | Emits |
| --- | --- | --- | --- |
| **Command Monitor Agent** | **directly detects** external `/cmd_vel` publisher set, publish rate, and velocity-envelope (linear/angular) anomalies | ROS2 graph introspection, `/cmd_vel` | `AnomalySignal`: unexpected publisher, rate spike, envelope breach |
| **State Consistency Agent** | **directly detects** inconsistency among `/odometry/filtered`, `/tf`, `/scan` | ROS2 topic subscriptions | `AnomalySignal`: odom jump vs tf, phantom/hidden `/scan` returns |
| **Mission-GNSS Guard Agent** | reads Bridge Mission Audit / GNSS Integrity results and builds signals | `Bridge/mission_audit.py`, `Bridge/gnss_integrity.py`; tails `logs/mission_audit.log`, `logs/gnss_integrity.log` | `AnomalySignal`: rejected mission, `spoof_jump`, `poor_fix` |
| **Correlation Agent** | **combines the collected `AnomalySignal`s** with its own deterministic scoring into a `risk_score` and the `hold_engaged` / `command_blocked` decision | **new agent-layer aggregation logic** (weights/thresholds as module constants); reads `logs/correlation_event.log` as **corroborating evidence** only — does **not** import the node-coupled `Bridge/correlation_engine.py:CorrelationEngine` | `CorrelationVerdict`; produces a deterministic verdict in dry-run **without** the Bridge |
| **Reasoning & Report Agent** | **LLM-core**: reasons over the grounded verdict + signals to produce an attack-chain hypothesis, root-cause, and mitigation, then assembles the incident report | verdict + timeline + `evidence_refs`; `anthropic` LLM is the **primary** path (deterministic template fallback with `--llm-backend none`); reasoning **never overrides** the deterministic reflex verdict | attack-chain + root-cause reasoning, recovery actions, `IncidentReport` (Markdown/JSON) |

**Command Hold / Block** is a deterministic function owned by the defense controller, not the
LLM. The Correlation Agent produces the `hold_engaged` / `command_blocked` **decision** every
round. **Enforcement is mode-split:** in **dry-run** the decision is only recorded; in **live
mode** — gated behind `--confirm-live-testbed-only` — the orchestrator may **actively** issue
a hold/block (publish a zero-Twist hold on `/cmd_vel`). This active block is simulation-bound
and, being a `/cmd_vel` publisher, structurally resembles Scenario A, so it is documented as
an **authoritative-override demonstration**, layered on top of the Bridge's own inline
enforcement (which remains the primary real-time guard).

---

## 4. Orchestration Flow (closed loop, per round)

```
S0  Discover        : enumerate ROS2 topics/publishers + Bridge ports (map surfaces).
S1  Select scenario : LLM brain picks A / B / C (team scenario files first, else vuln-driven); deterministic fallback with --llm-backend none.
S2  Plan attack     : bind adapter parameters (rate, target topic, spoof value, mission/gps payload).
S3  Inject          : Attack Replay Agent runs the selected adapter (dry-run = simulate; live = gated).
        │
        ▼  (settle wait ~4s)
S4  Detect+Correlate: Defense sensors collect AnomalySignals; Correlation reflex combines them into its OWN deterministic risk_score + hold/block verdict (correlation_event.log = corroborating evidence).
S5  Gap analysis    : LLM brain compares expected_guard/expected_signal vs observed and flags missed detections (deterministic fallback).
S6  Recommend       : Reasoning & Report Agent (LLM-core) reasons out attack-chain + root-cause and proposes recovery / mitigation (no auto-apply of code).
S7  Verify + Report : dry-run records the hold/block decision; gated live mode issues the active block (zero-Twist hold) and verifies /cmd_vel is held; write incident report.
        │
        └──► interactive confirmation gate → next round
```

- **dry-run mode**: adapters *simulate* injection; defense path is exercised against
  synthetic signals. Safe default, no live testbed required.
- **live mode**: adapters perform real local injection **and** the defense controller may
  **actively enforce** hold/block (publish a zero-Twist hold on `/cmd_vel`); both require
  `--confirm-live-testbed-only` and are simulation-bound. Dry-run only records the decision.
  GNSS/manual-control injectors already work; mission live-injection (needs a real MAVLink
  mission handshake) and port auto-discovery are known gaps (see §9).

---

## 5. Attack ↔ Defense Traceability (1:1, for report 4.2/4.3)

| Attack scenario | Detecting defense agent(s) | Guard mechanism | Expected verdict / evidence |
| --- | --- | --- | --- |
| **A** `/cmd_vel` injection | Command Monitor → Correlation | unexpected-publisher + rate/envelope check → risk score | `hold_engaged`, `command_blocked`, `/cmd_vel` clamped `0.0` in `correlation_event.log` |
| **B** odom/scan spoof | State Consistency → Correlation | odom↔tf / scan consistency check → risk score | inconsistency flagged; operator-awareness degradation reported |
| **C** mission/GNSS/manual | Mission-GNSS Guard → Correlation | Mission Audit reject + GNSS Integrity classify (`spoof_jump`/`poor_fix`) | rejections in `mission_audit.log` / `gnss_integrity.log`; `risk_score`, `hold_engaged` in `correlation_event.log` |

This table is the backbone of report **§4.3** — every confirmed attack maps to a named
defensive agent and a concrete evidence artifact. The **agent-layer Correlation Agent** owns
the `risk_score` / `hold_engaged` / `command_blocked` verdict; the `correlation_event.log`
entries **corroborate** it, they are not its source of truth.

---

## 6. Agent Interface Contract (conceptual — Codex fills in code)

All agents share a common message shape so the orchestrator can compose them. These are the
**Batch 1 dataclass contracts** (`agents/contracts.py`) — schema description, not code:

- **AttackAction**: `run_id`, `round_id`, `scenario_id`, `surface`, `adapter`, `parameters`,
  `mode` (`dry-run`|`live`), `created_at`, `confirm_live_testbed_only`
- **AnomalySignal**: `run_id`, `round_id`, `scenario_id`, `source_agent`, `surface`,
  `signal_type`, `severity`, `observed_value`, `expected`, `observed_at`, `evidence_refs`,
  `fresh_after`, `confidence`
- **CorrelationVerdict**: `run_id`, `round_id`, `scenario_id`, `risk_score`, `hold_engaged`,
  `command_blocked`, `contributing_signals`, `decided_at`, `evidence_refs`, `reason`
- **IncidentReport**: `run_id`, `round_id`, `scenario_id`, `timeline`, `root_cause`,
  `guard_hit`, `recovery_actions`, `evidence_refs`, `llm_backend`, `generated_at`, `status`

**Stale-log false-positive protection (load-bearing).** The three Bridge logs are append-only
and persist across runs, so a naive tail will read *old* events as if they were caused by the
current round. Every signal/verdict must therefore be scoped:

- `run_id` / `round_id` — issued by the orchestrator at the start of each run/round; stamped
  onto every `AnomalySignal` and `CorrelationVerdict` so agents can discard anything not
  belonging to the current round.
- `fresh_after` — a timestamp (per round) below which log lines are ignored as stale.
- `evidence_refs` — explicit source-log location for each signal (e.g.
  `{ "log": "logs/correlation_event.log", "line": N, "ts": ... }`) so every claim is traceable
  to a specific line and can be re-verified, never invented.

Evidence contract (do **not** regenerate or edit raw logs):
`logs/mission_audit.log`, `logs/gnss_integrity.log`, `logs/correlation_event.log` are the
read-only source of truth for the Mission-GNSS Guard and Correlation agents. Agent-produced
artifacts (incident reports, run traces) are written as **new JSONL/Markdown** files under
`agents/reports/`, never by editing Bridge evidence logs.

---

## 7. Technology Stack

| Concern | Choice | Notes |
| --- | --- | --- |
| Language | Python 3.10 | matches Bridge (`cpython-310`) |
| ROS2 interface | `rclpy` (Humble) | `/cmd_vel`, `/odometry/filtered`, `/scan`, `/tf`; `ROS_DOMAIN_ID=17` |
| MAVLink interface | `pymavlink` | reuse `Bridge/tools/send_*.py` injectors (default `--port 14551`, Bridge listens on `BRIDGE_LOCAL_PORT`, default 14551) |
| Defense logic | Bridge reuse + **new agent-layer detectors/correlation** | Mission Audit / GNSS Integrity **semantics reused** via Bridge modules + logs. Agent-level correlation, `/cmd_vel` external-publisher detection, and state-consistency detection are **new deterministic agent logic** — the agent correlation aggregates multi-source `AnomalySignal`s and is **not** a reimplementation of the node-coupled `CorrelationEngine`; `logs/correlation_event.log` is corroborating evidence. Do not indiscriminately reimplement Bridge logic. |
| Orchestration | plain Python state machine (`agents/main_orchestrator.py`) | CLI flags: `--rounds`, `--dry-run` / `--live`, `--confirm-live-testbed-only`, `--llm-backend` |
| LLM backend | `anthropic` Python SDK (`pip install anthropic`), pluggable; **LLM-on is the primary path**, `none` is the deterministic-reflex fallback | `client.messages.create(model=..., max_tokens=..., messages=[...])`. Drives the orchestrator brain (scenario selection, gap analysis) and the Reasoning & Report agent (attack-chain, root-cause, mitigation); the safety reflex must still run fully with `--llm-backend none`. Model id via env `AGENT_LLM_MODEL` — default `claude-haiku-4-5` for cheap local reasoning; `claude-opus-4-8` / `claude-fable-5` for demo quality. On `claude-fable-5`: omit the `thinking` param (always-on), guard `response.stop_reason == "refusal"` before reading content, and opt into server-side fallbacks. Do **not** use the heavier Claude Agent SDK / Managed Agents — the Messages API is the right surface here. |
| Evidence | JSONL + Markdown under `agents/reports/` | deterministic, reproducible |

---

## 8. Planned Directory Layout (target for Codex)

```
agents/
  README.md                 # this design (do not put code here)
  main_orchestrator.py      # closed-loop state machine (S0–S7)
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

Module boundaries above are **required**; do not merge attack and defense concerns into
one file, and do not reimplement Bridge logic inside `agents/`.

---

## 9. Known Gaps / Assumptions (carry forward, do not overclaim)

1. **External ROS2 `/cmd_vel` anomaly detection + agent correlation are new agent-layer logic.**
   The MAVLink **MANUAL_CONTROL high-command evaluation path already exists in the Bridge**
   (`ros2_mavlink_bridge.py`: `MANUAL_CONTROL` → `publish_cmd_vel(source="MANUAL_CONTROL")` →
   `correlation_engine.evaluate_command`). There is **no** Bridge path for an external ROS2
   `/cmd_vel` publisher/rate/envelope anomaly (Scenario A). The **Command Monitor Agent detects
   it and the agent-layer Correlation Agent scores it** into the verdict — this is new
   deterministic agent logic, not a change to the node-coupled Bridge engine.
2. **Scenario C mission live-injection** still needs a proper MAVLink mission handshake.
   `Bridge/tools/send_mission_upload.py` currently sends `MISSION_COUNT`, `time.sleep(0.3)`,
   then items — do **not** describe it as a robust handshake client; a real
   `MISSION_REQUEST`/`MISSION_ACK` round-trip is TODO. GNSS and manual-control live injection
   already work.
3. **Port auto-discovery is not wired.** The Bridge listen port is configurable via
   `BRIDGE_LOCAL_PORT` (default `14551`), and `tools/send_*.py` all default `--port` to
   `14551`. So the value is *defaulted*, not hardcoded — the gap is that **S0 discovery /
   environment propagation of the port into the adapters is not yet implemented**. TODO.
4. **Scenario B** consistency checks (odom↔tf, scan plausibility) are **new logic** with
   no existing Bridge counterpart — scope them as detector heuristics, not learned models.
5. **Grounding boundary (hard rule).** The **safety reflex** — the real-time `hold_engaged` /
   `command_blocked` enforcement and every sensor — is deterministic and must **never** depend
   on an LLM call; `--llm-backend none` must keep the reflex and a reproducible verdict fully
   working offline. The **LLM is the reasoning core** (scenario selection, correlation
   reasoning, gap analysis, root-cause, mitigation) and is the primary path, but it reasons
   *over* the grounded verdict and can **never override** the deterministic block.
   LLM = brain; deterministic = reflex/oracle.

Mark anything uncertain as `Assumption` / `Needs human confirmation` / `TODO` in code and
docs. Do not invent test results or evidence.

---

## 10. Codex Implementation Batches

Follow the **AGENTS.md two-phase workflow** (Plan Review → Plan Execute). Each batch below
is small and independently reviewable. **Do not combine batches.** Each must list expected
files before editing, run `python3 -m py_compile` on changed files, and preserve existing
env/port/topic behavior.

> **Phase 1 (Plan Review) first:** before writing any code, Codex performs adversarial
> review of this design — missing assumptions, unsafe scope, weak detection heuristics,
> two-layer mismatches — and returns issues ranked by severity. Claude refines, then
> execution starts.

Batch order is **defense-first**: scenarios A/B/C are being validated **live by teammates**,
so the Attack Replay adapters are pushed late (Batch 7). The **Correlation Agent is built
before** the ROS2 detectors: it is pure deterministic logic that can be validated offline
against the real Mission-GNSS signals (Batch 2) plus synthetic `AnomalySignal`s, whereas the
Command Monitor / State Consistency detectors need a live ROS2 stack to validate. This lands a
demonstrable detect → correlate → verdict slice early. The deterministic sensors + reflex
(Batches 1–4) are the **grounding layer**; the **LLM reasoning core lands in Batch 5
(Reasoning & Report) and Batch 6 (orchestrator brain)** on top of that grounded slice.

> **Prerequisite (contract patch, before Batch 2):** in `agents/contracts.py` only, add
> `signal_id: str` as the first field of `AnomalySignal`, and change
> `CorrelationVerdict.contributing_signals` to `list[str]` (it holds `signal_id` values).
> This lets the Correlation Agent reference the exact signals behind each verdict.

> **Prerequisite (contract patch, before Batch 5):** in `agents/contracts.py` only, add
> additive reasoning fields to `IncidentReport` (all with defaults, backward-compatible):
> `attack_chain: list[str]` (LLM/template attack-step hypothesis), `llm_rationale: str`
> (reasoning narrative), and `reasoning_source: str` (`"llm"` | `"template"`). These carry
> the LLM reasoning-core output without changing the deterministic reflex verdict.

**Batch 1 — Skeleton + contracts + no-op orchestrator.** Done. See the finalized spec below.
Expected files: `agents/__init__.py`, `agents/contracts.py`, `agents/main_orchestrator.py`.

**Batch 2 — Mission-GNSS log guard.** Done. Tail `logs/mission_audit.log` and
`logs/gnss_integrity.log` (read-only, `fresh_after`/`run_id`-scoped per §6) and emit
`AnomalySignal` (with `signal_id`) for rejected mission, `spoof_jump`, `poor_fix`. Reuse
`Bridge/mission_audit.py` / `Bridge/gnss_integrity.py` validation semantics; do not
reimplement. Expected file: `agents/defense/mission_gnss_guard.py`.

**Batch 3 — Correlation Agent + Command Hold/Block decision.** Done. Landed pure
agent-layer risk scoring, `CorrelationVerdict`, signal-id contribution tracking, and the
deterministic hold/block decision helper. Combine the collected
`AnomalySignal`s with **new deterministic agent-layer scoring** (weights/thresholds as module
constants) into a `CorrelationVerdict` (`risk_score`, `hold_engaged`, `command_blocked`,
`reason`, `contributing_signals` = the driving `signal_id`s, `evidence_refs`). Must produce a
deterministic verdict in **dry-run without the Bridge**, validated offline against the Batch 2
Mission-GNSS signals plus synthetic `AnomalySignal`s; read `logs/correlation_event.log` only as
corroborating evidence. Do **not** import the node-coupled `CorrelationEngine`.
`command_hold_block.py` holds the deterministic decision→action mapping (the active action is
gated to live mode, wired in Batch 6). Expected files:
`agents/defense/correlation_agent.py`, `agents/defense/command_hold_block.py`.

**Batch 4 — Command Monitor + State Consistency detectors (new deterministic logic).** Done.
Landed offline-testable deterministic `/cmd_vel`, odom/tf, and scan anomaly producers with
guarded ROS2 imports and JSONL `AnomalySignal` output. The
ROS2 signal producers: Command Monitor directly detects external `/cmd_vel`
publisher/rate/envelope anomalies (ROS2 graph introspection); State Consistency directly
detects odom↔tf↔scan inconsistency. Both emit `AnomalySignal` with `signal_id`, consumed by
the Batch 3 Correlation Agent. Label as deterministic detector heuristics; no learned-model
claims. Offline demo/fixture paths are available; live ROS2 stack validation is deferred.
Expected files:
`agents/defense/command_monitor.py`, `agents/defense/state_consistency.py`.

**Batch 5 — Reasoning & Report agent (LLM-core).** Done. Landed the `IncidentReport`
reasoning fields, untrusted-evidence prompt boundary, Anthropic optional path, deterministic
template fallback, and JSONL/Markdown report writing under `agents/reports/`. Consume verdict + timeline +
`evidence_refs` and use the `anthropic` LLM as the **primary** path to reason over the
grounded evidence — attack-chain hypothesis, root-cause, mitigation — then assemble the
`IncidentReport` (with the new reasoning fields) to `agents/reports/`. A deterministic
template fallback must still fully work with `--llm-backend none`, and **neither path may
override the deterministic reflex verdict**. Expected file:
`agents/defense/response_report.py`.

**Batch 6 — Orchestrator wiring (dry-run loop) + LLM brain + gated live active-block.** Done.
Landed single-command closed-loop dry-run orchestration, LLM/default-model selection with
deterministic fallback, gap analysis, run traces, and gated live enforcement attempts. 
Connect the real defense agents into S0–S7; produce a reproducible dry-run trace under
`agents/reports/`. Wire the **LLM brain**: S1 scenario selection and S5 gap analysis are
LLM-driven when a backend is set, with a deterministic fallback when `--llm-backend none`.
Record the **gated live-enforcement decision** every round; in `--live` +
`--confirm-live-testbed-only` mode the orchestrator logs an enforcement-attempt event (and,
when `rclpy`/`geometry_msgs` are unavailable, a `deferred` event). **The actual zero-Twist
`/cmd_vel` publish moves to Batch 7** (it needs the same `rclpy` publisher infra as the
attack adapters and can only be validated on the live stack). Dry-run records the decision
without publishing. The deterministic reflex verdict is authoritative — the LLM never
overrides it. **Flip the orchestrator default `--llm-backend`** from `none` to the
env-configured model (`AGENT_LLM_MODEL`, default `claude-haiku-4-5`), keeping
`--llm-backend none` as the explicit deterministic-reflex fallback. **Do not** edit
`Bridge/logs/*.log`. **Single-command requirement:** after this batch the entire closed loop
must run from one command — `python3 -m agents.main_orchestrator --rounds N --dry-run` (LLM
primary) and the offline fallback `--llm-backend none` — with no manual pre-steps. Expected
files: `agents/main_orchestrator.py` (wiring) and `agents/defense/response_report.py`
(Batch 5 fixes: remove the misplaced `extra_body` beta flag; `status` mirrors `guard_hit`).

**Batch 7 — Thin Attack Replay adapters + active `/cmd_vel` hold publisher.** Done. Landed
deterministic replay adapters, self-contained dry-run Scenario C evidence, gated live adapter
paths, safe allowlisted Adapter C subprocess wrapping, and active zero-Twist hold publishing
behind `--live --confirm-live-testbed-only`. 
`agents/attack/replay_agent.py` + adapters; Adapter C wraps `Bridge/tools/send_*.py` (dry-run
simulates, live gated by `--confirm-live-testbed-only`), Adapters A/B are `rclpy` publishers.
Also implements the **active zero-Twist `/cmd_vel` hold publisher** (`rclpy`) that Batch 6's
gated live-enforcement path invokes — grouped here because it shares the `rclpy` publisher
infra and needs live-stack validation. Kept thin because teammates own live attack validation.

**Batch 8 — Docs sync / Korean mirror.** In progress in this documentation batch. Update this README status section and author
`docs/agents_KR.md` as a Korean mirror carrying the **LLM-brain + deterministic-reflex**
framing (LLM reasoning core for scenario selection / correlation reasoning / gap analysis /
root-cause / mitigation, grounded by deterministic sensors + a real-time hold/block reflex the
LLM never overrides, gated live active-block). Align terminology with AGENTS.md (Simulation
Layer, Software-Defined UGV Security Layer, Mission Audit, GNSS Integrity, Correlation Engine,
Command Hold / Block).

### Implementation Status (after Batches 1-7)

The deterministic closed loop and the LLM-brain fallback are demonstrated in dry-run from one
command: `python3 -m agents.main_orchestrator --rounds N --dry-run` and the offline fallback
`--llm-backend none`. The stable dry-run core is:
**A(1.0, block) · B(0.48, none) · C(1.0, block)**.

Live ROS2/MAVLink injection paths and the active zero-Twist `/cmd_vel` hold are implemented
only behind `--live --confirm-live-testbed-only`, with `rclpy`/message-package dependency
guards and safe subprocess wrapping for the existing Bridge MAVLink tools. They are pending
validation on the team's live stack and are not claimed as validated in this environment.
This status preserves the **Logical Two-Layer Testbed Architecture**: Simulation Layer
signals are observed and replayed, while the Software-Defined UGV Security Layer owns
Mission Audit, GNSS Integrity, Correlation Engine semantics, and Command Hold / Block
decisions.

### Batch 1 — finalized spec

**Expected files:** `agents/__init__.py`, `agents/contracts.py`, `agents/main_orchestrator.py`.

**Constraints:**
- **No `Bridge` import, no `rclpy`/ROS2 import, no `pymavlink` import, no `anthropic` import.**
- No live injection; no read or write of `Bridge/logs/*.log`.
- `contracts.py` defines the four dataclasses exactly as in §6 (all listed fields).
- `main_orchestrator.py` walks **S0–S7 with stubs**, producing a deterministic **no-op**
  `CorrelationVerdict` (`risk_score=0.0`, `hold_engaged=False`, `command_blocked=False`) and a
  no-op `IncidentReport`.
- CLI defaults: `--dry-run` default (not `--live`); `--llm-backend none` default;
  `--live` requires `--confirm-live-testbed-only`, else exit with an error.
- `--rounds N` loops the stub S0–S7 N times with per-round `run_id`/`round_id`.

**Validation (must both pass):**
```bash
python3 -m py_compile agents/__init__.py agents/contracts.py agents/main_orchestrator.py
python3 -m agents.main_orchestrator --rounds 1 --dry-run --llm-backend none
```

---

## 11. Definition of Done (per contest criterion "AI 에이전트 아키텍처, 25점")

- Agent **roles**, **cooperation structure**, **tech stack**, and **diagram** are documented
  (this README) and reflected in report §4.2 / §4.3.
- Attack ↔ Defense traceability table (§5) is backed by real evidence artifacts.
- A **prototype** runs end-to-end in dry-run: the **LLM reasoning core** (scenario selection,
  gap analysis, attack-chain/root-cause report) is demonstrated on the primary path, and the
  deterministic `--llm-backend none` fallback still produces the reflex verdict offline.
  Live ROS2/MAVLink injection and active `/cmd_vel` hold are gated and dependency-guarded,
  with live-stack validation deferred.
- **Single-command execution:** the whole closed-loop pipeline runs from one command
  (`python3 -m agents.main_orchestrator …`) with no manual pre-steps — LLM-driven by default,
  deterministic reflex via `--llm-backend none`; live enforcement only behind
  `--live --confirm-live-testbed-only`.
- No overclaiming: the **LLM is the reasoning core** grounded by a deterministic sensor/reflex
  layer (rule + risk-scoring), not a learned model; the safety reflex enforces the block and
  the LLM never overrides it; testbed described as software-defined and simulation-bound.
