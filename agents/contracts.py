"""Shared message contracts for the Batch 1 agent skeleton."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp with a Z suffix."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class AttackAction:
    run_id: str = ""
    round_id: int = 0
    scenario_id: str = "stub"
    surface: str = "none"
    adapter: str = "stub"
    parameters: dict[str, Any] = field(default_factory=dict)
    mode: str = "dry-run"
    created_at: str = field(default_factory=utc_now)
    confirm_live_testbed_only: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnomalySignal:
    signal_id: str = ""
    run_id: str = ""
    round_id: int = 0
    scenario_id: str = "stub"
    source_agent: str = "stub"
    surface: str = "none"
    signal_type: str = "none"
    severity: str = "low"
    observed_value: Any = None
    expected: Any = None
    observed_at: str = field(default_factory=utc_now)
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    fresh_after: str = field(default_factory=utc_now)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CorrelationVerdict:
    run_id: str = ""
    round_id: int = 0
    scenario_id: str = "stub"
    risk_score: float = 0.0
    hold_engaged: bool = False
    command_blocked: bool = False
    contributing_signals: list[str] = field(default_factory=list)
    decided_at: str = field(default_factory=utc_now)
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    reason: str = "stub: no signals"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IncidentReport:
    run_id: str = ""
    round_id: int = 0
    scenario_id: str = "stub"
    timeline: list[dict[str, Any]] = field(default_factory=list)
    attack_chain: list[str] = field(default_factory=list)
    root_cause: str = "stub"
    guard_hit: str = "none"
    recovery_actions: list[str] = field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    llm_backend: str = "none"
    llm_rationale: str = ""
    reasoning_source: str = "template"
    generated_at: str = field(default_factory=utc_now)
    status: str = "no_finding"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
