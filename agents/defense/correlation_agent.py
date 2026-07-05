"""Deterministic correlation agent for anomaly signals."""

import argparse
import json
import sys
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.contracts import AnomalySignal, CorrelationVerdict, utc_now
from agents.defense.command_hold_block import decide


# Heuristic weights for deterministic scoring. These are not learned-model weights.
SIGNAL_WEIGHTS = {
    ("mission", "mission_rejected"): 0.5,
    ("gnss", "spoof_jump"): 0.6,
    ("gnss", "poor_fix"): 0.4,
    ("cmd_vel", "unexpected_publisher"): 0.5,
    ("cmd_vel", "rate_spike"): 0.4,
    ("cmd_vel", "envelope_breach"): 0.6,
    ("state", "odom_tf_mismatch"): 0.4,
    ("state", "scan_anomaly"): 0.4,
}
DEFAULT_WEIGHT = 0.3
SEVERITY_MULT = {"high": 1.0, "medium": 0.6, "low": 0.3}
HOLD_THRESHOLD = 0.5
BLOCK_THRESHOLD = 0.8


def parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None

    normalized = value
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def signal_weight(signal: AnomalySignal) -> float:
    return SIGNAL_WEIGHTS.get((signal.surface, signal.signal_type), DEFAULT_WEIGHT)


def severity_multiplier(signal: AnomalySignal) -> float:
    return SEVERITY_MULT.get(signal.severity, 0.6)


def infer_scenario_id(signals: list[AnomalySignal]) -> str:
    if not signals:
        return "none"

    scenario_ids = {signal.scenario_id for signal in signals}
    if len(scenario_ids) == 1:
        return next(iter(scenario_ids))

    return "mixed"


def signal_type_counts(signals: list[AnomalySignal]) -> str:
    counts: dict[str, int] = {}
    for signal in signals:
        counts[signal.signal_type] = counts.get(signal.signal_type, 0) + 1

    return ", ".join(f"{name}={counts[name]}" for name in sorted(counts))


def signal_evidence_refs(signals: list[AnomalySignal]) -> list[dict[str, Any]]:
    evidence_refs: list[dict[str, Any]] = []
    for signal in signals:
        evidence_refs.extend(signal.evidence_refs)
    return evidence_refs


def load_corroborating_refs(correlation_log: str, fresh_after: str) -> list[dict[str, Any]]:
    threshold = parse_timestamp(fresh_after)
    if threshold is None:
        return []

    path = Path(correlation_log).expanduser()
    if not path.exists():
        return []

    refs = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not isinstance(record, dict):
                continue

            ts = str(record.get("ts", ""))
            observed_at = parse_timestamp(ts)
            if observed_at is None or observed_at < threshold:
                continue

            refs.append(
                {
                    "log": correlation_log,
                    "line": line_no,
                    "ts": ts,
                    "corroborating": True,
                }
            )

    return refs


def correlate(
    run_id: str,
    round_id: int,
    signals: list[AnomalySignal],
    scenario_id: str = "",
    correlation_log: str | None = None,
    fresh_after: str | None = None,
) -> CorrelationVerdict:
    if not signals:
        return CorrelationVerdict(
            run_id=run_id,
            round_id=round_id,
            scenario_id=scenario_id or "none",
            risk_score=0.0,
            hold_engaged=False,
            command_blocked=False,
            contributing_signals=[],
            evidence_refs=[],
            reason="no signals",
            decided_at=utc_now(),
        )

    score = sum(signal_weight(signal) * severity_multiplier(signal) for signal in signals)
    risk_score = round(min(1.0, score), 3)
    hold_engaged = risk_score >= HOLD_THRESHOLD
    command_blocked = risk_score >= BLOCK_THRESHOLD
    resolved_scenario_id = scenario_id or infer_scenario_id(signals)
    contributing_signals = [signal.signal_id for signal in signals]
    evidence_refs = signal_evidence_refs(signals)

    if correlation_log is not None and fresh_after is not None:
        evidence_refs.extend(load_corroborating_refs(correlation_log, fresh_after))

    counts = signal_type_counts(signals)
    reason = (
        f"risk={risk_score:.3f} from {len(signals)} signals ({counts}); "
        f"hold={hold_engaged} block={command_blocked}"
    )

    return CorrelationVerdict(
        run_id=run_id,
        round_id=round_id,
        scenario_id=resolved_scenario_id,
        risk_score=risk_score,
        hold_engaged=hold_engaged,
        command_blocked=command_blocked,
        contributing_signals=contributing_signals,
        evidence_refs=evidence_refs,
        reason=reason,
        decided_at=utc_now(),
    )


def signal_field_names() -> set[str]:
    return {field.name for field in fields(AnomalySignal)}


def signal_from_dict(record: dict[str, Any]) -> AnomalySignal | None:
    names = signal_field_names()
    values = {key: value for key, value in record.items() if key in names}
    try:
        return AnomalySignal(**values)
    except TypeError:
        return None


def read_signals_from_stdin() -> list[AnomalySignal]:
    if sys.stdin.isatty():
        return sample_signals()

    raw = sys.stdin.read()
    if not raw.strip():
        return []

    signals = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        if isinstance(record, dict):
            signal = signal_from_dict(record)
            if signal is not None:
                signals.append(signal)

    return signals


def sample_signals() -> list[AnomalySignal]:
    return [
        AnomalySignal(
            signal_id="sample-mission",
            run_id="sample",
            round_id=1,
            scenario_id="C",
            source_agent="mission_gnss_guard",
            surface="mission",
            signal_type="mission_rejected",
            severity="high",
            observed_value={"event": "mission_audit_result"},
            expected="accepted",
            confidence=1.0,
        ),
        AnomalySignal(
            signal_id="sample-gnss",
            run_id="sample",
            round_id=1,
            scenario_id="C",
            source_agent="mission_gnss_guard",
            surface="gnss",
            signal_type="spoof_jump",
            severity="high",
            observed_value={"reasons": ["position residual sample"]},
            expected="within GNSS integrity limits",
            confidence=1.0,
        ),
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Correlate AnomalySignal JSONL into a deterministic verdict."
    )
    parser.add_argument("--run-id", default="")
    parser.add_argument("--round-id", type=int, default=1)
    parser.add_argument("--scenario-id", default="")

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    mode_group.add_argument("--live", dest="dry_run", action="store_false")

    parser.add_argument("--confirm-live-testbed-only", action="store_true")
    parser.add_argument("--correlation-log")
    parser.add_argument("--fresh-after")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    mode = "dry-run" if args.dry_run else "live"
    signals = read_signals_from_stdin()

    verdict = correlate(
        run_id=args.run_id,
        round_id=args.round_id,
        signals=signals,
        scenario_id=args.scenario_id,
        correlation_log=args.correlation_log,
        fresh_after=args.fresh_after,
    )
    action = decide(
        verdict=verdict,
        mode=mode,
        confirm_live_testbed_only=args.confirm_live_testbed_only,
    )

    print(json.dumps(verdict.to_dict(), ensure_ascii=False, sort_keys=True))
    print(json.dumps(action.to_dict(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

