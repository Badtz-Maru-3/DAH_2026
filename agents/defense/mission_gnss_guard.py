"""Mission/GNSS log guard for deterministic anomaly signal collection."""

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.contracts import AnomalySignal, utc_now


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MISSION_LOG = str(REPO_ROOT / "Bridge" / "logs" / "mission_audit.log")
DEFAULT_GNSS_LOG = str(REPO_ROOT / "Bridge" / "logs" / "gnss_integrity.log")


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


def resolve_log_path(path_value: str, env_name: str, default_path: str) -> str:
    if path_value == default_path:
        return os.environ.get(env_name, default_path)
    return path_value


def make_signal_id(run_id: str, round_id: int, log_path: str, line_no: int, ts: str) -> str:
    raw = f"{run_id}:{round_id}:{log_path}:{line_no}:{ts}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def load_jsonl(path_value: str) -> list[tuple[int, dict[str, Any]]]:
    path = Path(path_value).expanduser()
    if not path.exists():
        return []

    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if isinstance(record, dict):
                records.append((line_no, record))

    return records


def mission_reason(record: dict[str, Any]) -> str:
    reason = record.get("reason")
    if reason:
        return str(reason)

    reasons = record.get("reasons")
    if isinstance(reasons, list):
        return "; ".join(str(item) for item in reasons)

    return ""


def mission_observed_value(record: dict[str, Any]) -> dict[str, Any]:
    observed = {
        "event": record.get("event"),
        "reason": mission_reason(record),
    }

    if "seq" in record:
        observed["seq"] = record.get("seq")
    if "count" in record:
        observed["count"] = record.get("count")

    return observed


def gnss_signal_type(reasons: list[Any]) -> str:
    for reason in reasons:
        if str(reason).startswith("position residual"):
            return "spoof_jump"
    return "poor_fix"


def gnss_observed_value(record: dict[str, Any], reasons: list[Any]) -> dict[str, Any]:
    return {
        "residual_m": record.get("residual_m"),
        "fix_type": record.get("fix_type"),
        "satellites_visible": record.get("satellites_visible"),
        "horiz_accuracy": record.get("horiz_accuracy"),
        "reasons": reasons,
    }


def evidence_ref(log_path: str, line_no: int, ts: str) -> list[dict[str, Any]]:
    return [
        {
            "log": log_path,
            "line": line_no,
            "ts": ts,
        }
    ]


def collect_mission_signals(
    run_id: str,
    round_id: int,
    fresh_after: str,
    mission_log: str,
    threshold: datetime,
) -> list[AnomalySignal]:
    signals = []

    for line_no, record in load_jsonl(mission_log):
        ts = str(record.get("ts", ""))
        observed_at = parse_timestamp(ts)
        if observed_at is None or observed_at < threshold:
            continue

        if record.get("result") != "rejected":
            continue

        signals.append(
            AnomalySignal(
                signal_id=make_signal_id(run_id, round_id, mission_log, line_no, ts),
                run_id=run_id,
                round_id=round_id,
                scenario_id="C",
                source_agent="mission_gnss_guard",
                surface="mission",
                signal_type="mission_rejected",
                severity="high",
                observed_value=mission_observed_value(record),
                expected="accepted",
                observed_at=ts,
                evidence_refs=evidence_ref(mission_log, line_no, ts),
                fresh_after=fresh_after,
                confidence=1.0,
            )
        )

    return signals


def collect_gnss_signals(
    run_id: str,
    round_id: int,
    fresh_after: str,
    gnss_log: str,
    threshold: datetime,
) -> list[AnomalySignal]:
    signals = []

    for line_no, record in load_jsonl(gnss_log):
        ts = str(record.get("ts", ""))
        observed_at = parse_timestamp(ts)
        if observed_at is None or observed_at < threshold:
            continue

        if record.get("result") != "rejected":
            continue

        reasons_raw = record.get("reasons", [])
        reasons = reasons_raw if isinstance(reasons_raw, list) else []

        signals.append(
            AnomalySignal(
                signal_id=make_signal_id(run_id, round_id, gnss_log, line_no, ts),
                run_id=run_id,
                round_id=round_id,
                scenario_id="C",
                source_agent="mission_gnss_guard",
                surface="gnss",
                signal_type=gnss_signal_type(reasons),
                severity="high",
                observed_value=gnss_observed_value(record, reasons),
                expected="within GNSS integrity limits",
                observed_at=ts,
                evidence_refs=evidence_ref(gnss_log, line_no, ts),
                fresh_after=fresh_after,
                confidence=1.0,
            )
        )

    return signals


def collect_signals(
    run_id: str,
    round_id: int,
    fresh_after: str,
    mission_log: str = DEFAULT_MISSION_LOG,
    gnss_log: str = DEFAULT_GNSS_LOG,
) -> list[AnomalySignal]:
    effective_mission_log = resolve_log_path(
        mission_log,
        "MISSION_AUDIT_LOG",
        DEFAULT_MISSION_LOG,
    )
    effective_gnss_log = resolve_log_path(
        gnss_log,
        "GNSS_INTEGRITY_LOG",
        DEFAULT_GNSS_LOG,
    )

    threshold = parse_timestamp(fresh_after)
    if threshold is None:
        return []

    signals = []
    signals.extend(
        collect_mission_signals(
            run_id,
            round_id,
            fresh_after,
            effective_mission_log,
            threshold,
        )
    )
    signals.extend(
        collect_gnss_signals(
            run_id,
            round_id,
            fresh_after,
            effective_gnss_log,
            threshold,
        )
    )
    return signals


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect Mission/GNSS anomaly signals from read-only Bridge JSONL logs."
    )
    parser.add_argument("--fresh-after", default=utc_now())
    parser.add_argument("--run-id", default="")
    parser.add_argument("--round-id", type=int, default=1)
    parser.add_argument("--mission-log")
    parser.add_argument("--gnss-log")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    mission_log = args.mission_log if args.mission_log is not None else DEFAULT_MISSION_LOG
    gnss_log = args.gnss_log if args.gnss_log is not None else DEFAULT_GNSS_LOG

    for signal in collect_signals(
        run_id=args.run_id,
        round_id=args.round_id,
        fresh_after=args.fresh_after,
        mission_log=mission_log,
        gnss_log=gnss_log,
    ):
        print(json.dumps(signal.to_dict(), ensure_ascii=False, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

