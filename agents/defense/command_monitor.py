"""Deterministic /cmd_vel anomaly signal producer."""

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.contracts import AnomalySignal, utc_now

try:
    import rclpy  # type: ignore[import-not-found]
except ImportError:
    rclpy = None


# Assumption: Bridge node name; confirm against live graph.
DEFAULT_EXPECTED_PUBLISHERS = {"ros2_mavlink_bridge"}

# Assumption / TODO: confirm against live stack.
CMD_VEL_RATE_MAX_HZ = 20.0
# Mirror the Bridge correlation "high command" detection thresholds
# (COMMAND_HIGH_LINEAR_MPS / COMMAND_HIGH_ANGULAR_RADPS in .env / compose) so the
# agent-layer envelope detector and the Bridge command guard flag the same
# over-limit /cmd_vel commands. Legit Bridge output is clamped to MAX_LINEAR=0.5 /
# MAX_ANGULAR=1.2, so these detection thresholds sit just above the clamp.
CMD_VEL_LINEAR_MAX = 0.60
CMD_VEL_ANGULAR_MAX = 1.50

# Contract: these (surface, signal_type) values must match correlation_agent.SIGNAL_WEIGHTS.
SIGNAL_PROFILE = {
    "unexpected_publisher": ("high", 0.9),
    "rate_spike": ("medium", 0.7),
    "envelope_breach": ("high", 0.8),
}


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


def make_signal_id(
    run_id: str,
    round_id: int,
    source_agent: str,
    signal_type: str,
    observed_at: str,
    detail: Any,
) -> str:
    raw = f"{run_id}:{round_id}:{source_agent}:{signal_type}:{observed_at}:{detail}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def node_basename(name: str) -> str:
    return str(name).strip().rstrip("/").split("/")[-1]


def is_fresh(observed_at: str, fresh_after: str) -> bool:
    observed = parse_timestamp(observed_at)
    threshold = parse_timestamp(fresh_after)
    if observed is None or threshold is None:
        return False
    return observed >= threshold


def evidence_ref(topic: str, source: str, observed_at: str, detail: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "source": source,
            "topic": topic,
            "detail": detail,
            "ts": observed_at,
        }
    ]


def velocity_component(sample: dict[str, Any], group: str, axis: str, flat_name: str) -> float:
    if flat_name in sample:
        return float(sample.get(flat_name) or 0.0)

    group_value = sample.get(group)
    if isinstance(group_value, dict):
        return float(group_value.get(axis) or 0.0)

    return 0.0


def max_rate_hz(snapshot: dict[str, Any]) -> float:
    if "publish_rate_hz" in snapshot:
        return float(snapshot.get("publish_rate_hz") or 0.0)

    samples = snapshot.get("rate_samples_hz", [])
    if not isinstance(samples, list) or not samples:
        return 0.0

    return max(float(sample or 0.0) for sample in samples)


def envelope_breach_detail(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    samples = snapshot.get("velocity_samples", [])
    if isinstance(snapshot.get("velocity"), dict):
        samples = [snapshot["velocity"]]

    if not isinstance(samples, list):
        return None

    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            continue

        linear_x = velocity_component(sample, "linear", "x", "linear_x")
        angular_z = velocity_component(sample, "angular", "z", "angular_z")
        if abs(linear_x) > CMD_VEL_LINEAR_MAX or abs(angular_z) > CMD_VEL_ANGULAR_MAX:
            return {
                "sample_index": index,
                "linear_x": linear_x,
                "angular_z": angular_z,
                "linear_max": CMD_VEL_LINEAR_MAX,
                "angular_max": CMD_VEL_ANGULAR_MAX,
            }

    return None


def build_signal(
    run_id: str,
    round_id: int,
    scenario_id: str,
    signal_type: str,
    observed_value: Any,
    expected: Any,
    observed_at: str,
    fresh_after: str,
    evidence_detail: dict[str, Any],
) -> AnomalySignal:
    severity, confidence = SIGNAL_PROFILE[signal_type]
    return AnomalySignal(
        signal_id=make_signal_id(
            run_id,
            round_id,
            "command_monitor",
            signal_type,
            observed_at,
            observed_value,
        ),
        run_id=run_id,
        round_id=round_id,
        scenario_id=scenario_id,
        source_agent="command_monitor",
        surface="cmd_vel",
        signal_type=signal_type,
        severity=severity,
        observed_value=observed_value,
        expected=expected,
        observed_at=observed_at,
        evidence_refs=evidence_ref("/cmd_vel", "ros2_topic", observed_at, evidence_detail),
        fresh_after=fresh_after,
        confidence=confidence,
    )


def detect_command_anomalies(
    snapshot: dict[str, Any],
    run_id: str,
    round_id: int,
    fresh_after: str,
    scenario_id: str = "A",
    expected_publishers: set[str] | None = None,
) -> list[AnomalySignal]:
    expected = expected_publishers or DEFAULT_EXPECTED_PUBLISHERS
    observed_at = str(snapshot.get("observed_at") or snapshot.get("ts") or utc_now())
    if not is_fresh(observed_at, fresh_after):
        return []

    signals = []
    raw_publishers = snapshot.get("publishers", [])
    publishers = raw_publishers if isinstance(raw_publishers, list) else []
    publisher_basenames = sorted(node_basename(str(name)) for name in publishers)
    unexpected = [name for name in publisher_basenames if name and name not in expected]
    if unexpected:
        signals.append(
            build_signal(
                run_id,
                round_id,
                scenario_id,
                "unexpected_publisher",
                {"publishers": publisher_basenames, "unexpected": unexpected},
                {"allowed_publishers": sorted(expected)},
                observed_at,
                fresh_after,
                {"check": "publisher_basename_allowlist", "publishers": publisher_basenames},
            )
        )

    observed_rate = max_rate_hz(snapshot)
    if observed_rate > CMD_VEL_RATE_MAX_HZ:
        signals.append(
            build_signal(
                run_id,
                round_id,
                scenario_id,
                "rate_spike",
                {"max_rate_hz": observed_rate},
                {"max_rate_hz": CMD_VEL_RATE_MAX_HZ},
                observed_at,
                fresh_after,
                {"check": "publish_rate", "max_rate_hz": observed_rate},
            )
        )

    breach = envelope_breach_detail(snapshot)
    if breach is not None:
        signals.append(
            build_signal(
                run_id,
                round_id,
                scenario_id,
                "envelope_breach",
                breach,
                {"linear_max": CMD_VEL_LINEAR_MAX, "angular_max": CMD_VEL_ANGULAR_MAX},
                observed_at,
                fresh_after,
                {"check": "velocity_envelope", **breach},
            )
        )

    return signals


def demo_snapshot() -> dict[str, Any]:
    return {
        "observed_at": utc_now(),
        "publishers": ["/attack/cmd_vel_injector", "/ros2_mavlink_bridge"],
        "rate_samples_hz": [8.0, CMD_VEL_RATE_MAX_HZ + 5.0],
        "velocity_samples": [
            {
                "linear": {"x": CMD_VEL_LINEAR_MAX + 0.5},
                "angular": {"z": 0.1},
            }
        ],
    }


def endpoint_names(infos: list[Any]) -> list[str]:
    names = []
    for info in infos:
        namespace = str(getattr(info, "node_namespace", "") or "").rstrip("/")
        name = str(getattr(info, "node_name", "") or "")
        if namespace and namespace != "/":
            names.append(f"{namespace}/{name}")
        elif name:
            names.append(f"/{name}")
    return sorted(set(names))


def load_snapshot(path_value: str | None) -> dict[str, Any]:
    if path_value:
        raw = Path(path_value).expanduser().read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
    else:
        return {}

    if not raw.strip():
        return {}

    record = json.loads(raw)
    return record if isinstance(record, dict) else {}


def collect_live_snapshot(topic: str = "/cmd_vel", sample_seconds: float = 1.0) -> dict[str, Any]:
    if rclpy is None:
        print("rclpy is unavailable; use --demo or provide a JSON snapshot fixture.", file=sys.stderr)
        return {}

    try:
        from geometry_msgs.msg import Twist  # type: ignore[import-not-found]
    except ImportError as exc:
        print(f"geometry_msgs is unavailable: {exc}", file=sys.stderr)
        return {}

    samples: list[dict[str, Any]] = []
    publishers: list[str] = []
    started = time.monotonic()

    def on_twist(msg: Any) -> None:
        samples.append(
            {
                "linear": {
                    "x": float(getattr(msg.linear, "x", 0.0)),
                    "y": float(getattr(msg.linear, "y", 0.0)),
                    "z": float(getattr(msg.linear, "z", 0.0)),
                },
                "angular": {
                    "x": float(getattr(msg.angular, "x", 0.0)),
                    "y": float(getattr(msg.angular, "y", 0.0)),
                    "z": float(getattr(msg.angular, "z", 0.0)),
                },
            }
        )

    rclpy.init(args=None)
    node = rclpy.create_node("dah_command_monitor_snapshot")
    try:
        node.create_subscription(Twist, topic, on_twist, 10)
        publishers.extend(endpoint_names(node.get_publishers_info_by_topic(topic)))
        while time.monotonic() - started < max(0.05, sample_seconds):
            rclpy.spin_once(node, timeout_sec=0.05)
            publishers.extend(endpoint_names(node.get_publishers_info_by_topic(topic)))
    finally:
        node.destroy_node()
        rclpy.shutdown()

    elapsed = max(time.monotonic() - started, 0.001)
    snapshot = {
        "observed_at": utc_now(),
        "publishers": sorted(set(publishers)),
        "velocity_samples": samples,
    }
    if samples:
        snapshot["publish_rate_hz"] = round(len(samples) / elapsed, 3)
    return snapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect deterministic /cmd_vel anomaly signals."
    )
    parser.add_argument("--fresh-after", default=utc_now())
    parser.add_argument("--run-id", default="")
    parser.add_argument("--round-id", type=int, default=1)
    parser.add_argument("--scenario-id", default="A")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--snapshot")
    parser.add_argument("--sample-seconds", type=float, default=1.0)
    parser.add_argument(
        "--expected-publisher",
        action="append",
        default=[],
        help="Allowed /cmd_vel publisher node basename; repeatable.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    expected_publishers = set(args.expected_publisher) or DEFAULT_EXPECTED_PUBLISHERS

    if args.demo:
        snapshot = demo_snapshot()
    else:
        snapshot = load_snapshot(args.snapshot)
        if not snapshot:
            snapshot = collect_live_snapshot(sample_seconds=args.sample_seconds)

    for signal in detect_command_anomalies(
        snapshot=snapshot,
        run_id=args.run_id,
        round_id=args.round_id,
        fresh_after=args.fresh_after,
        scenario_id=args.scenario_id,
        expected_publishers=expected_publishers,
    ):
        print(json.dumps(signal.to_dict(), ensure_ascii=False, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
