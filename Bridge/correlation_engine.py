#!/usr/bin/env python3

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from geometry_msgs.msg import Twist
from pymavlink.dialects.v20 import common as mavlink2


def env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


def env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class CorrelationEngine:
    def __init__(self, node):
        self.node = node

        self.log_path = Path(env_str("CORRELATION_LOG", "/logs/correlation_event.log"))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self.signal_ttl_s = env_float("CORRELATION_SIGNAL_TTL_S", 20.0)
        self.risk_threshold = env_float("CORRELATION_RISK_THRESHOLD", 0.75)
        self.hold_seconds = env_float("CORRELATION_HOLD_SECONDS", 5.0)

        self.weight_mission_rejected = env_float("CORRELATION_WEIGHT_MISSION_REJECTED", 0.75)
        self.weight_gnss_rejected = env_float("CORRELATION_WEIGHT_GNSS_REJECTED", 0.75)
        self.weight_high_command = env_float("CORRELATION_WEIGHT_HIGH_COMMAND", 0.35)

        self.command_high_linear = env_float("COMMAND_HIGH_LINEAR_MPS", 0.45)
        self.command_high_angular = env_float("COMMAND_HIGH_ANGULAR_RADPS", 1.0)

        self.signals: List[Dict[str, Any]] = []
        self.block_until = 0.0

        self.audit_log(
            "correlation_engine_started",
            risk_threshold=self.risk_threshold,
            hold_seconds=self.hold_seconds,
            signal_ttl_s=self.signal_ttl_s,
        )

    def now(self) -> float:
        return time.monotonic()

    def is_blocked(self) -> bool:
        return self.now() < self.block_until

    def decay(self):
        cutoff = self.now() - self.signal_ttl_s
        self.signals = [s for s in self.signals if s["mono_ts"] >= cutoff]

    def weight_for(self, source: str, kind: str) -> float:
        if source == "mission_audit" and kind == "rejected":
            return self.weight_mission_rejected
        if source == "gnss_integrity" and kind == "rejected":
            return self.weight_gnss_rejected
        if source == "command_guard" and kind == "high_command":
            return self.weight_high_command
        return 0.25

    def risk_score(self) -> float:
        self.decay()
        score = 0.0
        for signal in self.signals:
            score += float(signal["weight"]) * float(signal["severity"])
        return clamp(score, 0.0, 1.0)

    def record_signal(self, source: str, kind: str, severity: float = 1.0, detail: Dict[str, Any] = None):
        severity = clamp(float(severity), 0.0, 1.0)
        weight = self.weight_for(source, kind)

        signal = {
            "mono_ts": self.now(),
            "source": source,
            "kind": kind,
            "severity": severity,
            "weight": weight,
            "detail": detail or {},
        }

        self.signals.append(signal)
        score = self.risk_score()

        self.audit_log(
            "signal_recorded",
            source=source,
            kind=kind,
            severity=severity,
            weight=weight,
            risk_score=score,
            active_signals=self.active_signal_summary(),
            detail=detail or {},
        )

        if score >= self.risk_threshold:
            self.engage_hold(
                reason=f"risk_score {score:.2f} >= threshold {self.risk_threshold:.2f}",
                risk_score=score,
            )

        return score

    def evaluate_command(self, linear: float, angular: float, source: str) -> Tuple[bool, float, List[str]]:
        reasons = []

        if self.is_blocked():
            score = self.risk_score()
            reasons.append("correlation hold active")
            self.audit_log(
                "command_blocked",
                source=source,
                linear=linear,
                angular=angular,
                risk_score=score,
                reasons=reasons,
            )
            return False, score, reasons

        if abs(linear) >= self.command_high_linear or abs(angular) >= self.command_high_angular:
            reasons.append("high manual command")
            score = self.record_signal(
                source="command_guard",
                kind="high_command",
                severity=1.0,
                detail={
                    "command_source": source,
                    "linear": linear,
                    "angular": angular,
                    "linear_limit": self.command_high_linear,
                    "angular_limit": self.command_high_angular,
                },
            )
        else:
            score = self.risk_score()

        if self.is_blocked():
            reasons.append("risk threshold crossed after command evaluation")
            self.audit_log(
                "command_blocked",
                source=source,
                linear=linear,
                angular=angular,
                risk_score=score,
                reasons=reasons,
            )
            return False, score, reasons

        return True, score, reasons

    def engage_hold(self, reason: str, risk_score: float):
        until = self.now() + self.hold_seconds
        if until > self.block_until:
            self.block_until = until

        self.publish_zero()

        try:
            self.node.mav.statustext_send(
                mavlink2.MAV_SEVERITY_WARNING,
                b"Correlation hold engaged",
            )
        except Exception:
            pass

        self.audit_log(
            "hold_engaged",
            reason=reason,
            risk_score=risk_score,
            hold_seconds=self.hold_seconds,
            active_signals=self.active_signal_summary(),
        )

        self.node.get_logger().warn(
            f"[correlation] hold engaged: risk_score={risk_score:.2f}, reason={reason}"
        )

    def publish_zero(self):
        cmd = Twist()
        self.node.cmd_pub.publish(cmd)
        self.node.sent_idle_stop = True

    def active_signal_summary(self):
        self.decay()
        return [
            {
                "source": s["source"],
                "kind": s["kind"],
                "severity": s["severity"],
                "weight": s["weight"],
            }
            for s in self.signals
        ]

    def audit_log(self, event: str, **fields):
        record = {
            "ts": utc_now(),
            "event": event,
            **fields,
        }

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
