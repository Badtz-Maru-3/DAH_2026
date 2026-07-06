"""Deterministic state consistency anomaly signal producer."""

import argparse
import hashlib
import json
import math
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


DEFAULT_ODOM_FRAME = "odom"
DEFAULT_BASE_FRAME = "base_link"

# Assumption / TODO: confirm against live stack.
TF_TIME_TOLERANCE_S = 0.5
# Assumption / TODO: confirm against live stack.
ODOM_TF_POS_TH = 0.5
# Assumption / TODO: confirm against live stack.
SCAN_MIN_SAMPLES = 20
# Assumption / TODO: confirm against live stack.
SCAN_ANOMALY_RATIO = 0.9

# Contract: these (surface, signal_type) values must match correlation_agent.SIGNAL_WEIGHTS.
SIGNAL_PROFILE = {
    "odom_tf_mismatch": ("medium", 0.7),
    "scan_anomaly": ("medium", 0.7),
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


def frame_basename(name: str) -> str:
    return str(name).strip().rstrip("/").split("/")[-1]


def is_fresh(observed_at: str, fresh_after: str) -> bool:
    observed = parse_timestamp(observed_at)
    threshold = parse_timestamp(fresh_after)
    if observed is None or threshold is None:
        return False
    return observed >= threshold


def seconds_between(first: str, second: str) -> float | None:
    first_ts = parse_timestamp(first)
    second_ts = parse_timestamp(second)
    if first_ts is None or second_ts is None:
        return None
    return abs((first_ts - second_ts).total_seconds())


def evidence_ref(topic: str, source: str, observed_at: str, detail: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "source": source,
            "topic": topic,
            "detail": detail,
            "ts": observed_at,
        }
    ]


def vector_from_pose(record: dict[str, Any]) -> tuple[float, float, float] | None:
    position = record.get("position")
    if isinstance(position, dict):
        return (
            float(position.get("x") or 0.0),
            float(position.get("y") or 0.0),
            float(position.get("z") or 0.0),
        )

    pose = record.get("pose")
    if isinstance(pose, dict):
        return vector_from_pose(pose)

    translation = record.get("translation")
    if isinstance(translation, dict):
        return (
            float(translation.get("x") or 0.0),
            float(translation.get("y") or 0.0),
            float(translation.get("z") or 0.0),
        )

    return None


def find_tf_transform(
    transforms: list[Any],
    odom_frame: str,
    base_frame: str,
) -> dict[str, Any] | None:
    expected_parent = frame_basename(odom_frame)
    expected_child = frame_basename(base_frame)

    for transform in transforms:
        if not isinstance(transform, dict):
            continue

        parent = frame_basename(
            str(transform.get("parent_frame") or transform.get("frame_id") or "")
        )
        child = frame_basename(
            str(transform.get("child_frame") or transform.get("child_frame_id") or "")
        )
        if parent == expected_parent and child == expected_child:
            return transform

    return None


def scan_ranges(scan: dict[str, Any]) -> list[float]:
    ranges = scan.get("ranges", [])
    if not isinstance(ranges, list):
        return []

    values = []
    for value in ranges:
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            values.append(float("nan"))
    return values


def scan_anomaly_detail(scan: dict[str, Any]) -> dict[str, Any] | None:
    values = scan_ranges(scan)
    total = len(values)
    if total < SCAN_MIN_SAMPLES:
        return None

    range_max = float(scan.get("range_max") or 0.0)
    if range_max <= 0.0:
        return None

    invalid_count = sum(1 for value in values if math.isnan(value) or math.isinf(value))
    at_max_count = sum(
        1 for value in values if math.isfinite(value) and value >= range_max * 0.99
    )
    constant_count = 0
    finite_values = [value for value in values if math.isfinite(value)]
    if finite_values:
        first = finite_values[0]
        constant_count = sum(1 for value in finite_values if abs(value - first) <= 0.001)

    max_ratio = at_max_count / total
    invalid_ratio = invalid_count / total
    constant_ratio = constant_count / total
    dominant_ratio = max(max_ratio, invalid_ratio, constant_ratio)

    if dominant_ratio <= SCAN_ANOMALY_RATIO:
        return None

    return {
        "total_returns": total,
        "range_max": range_max,
        "at_max_ratio": round(max_ratio, 3),
        "invalid_ratio": round(invalid_ratio, 3),
        "constant_ratio": round(constant_ratio, 3),
        "threshold_ratio": SCAN_ANOMALY_RATIO,
    }


def build_signal(
    run_id: str,
    round_id: int,
    scenario_id: str,
    signal_type: str,
    observed_value: Any,
    expected: Any,
    observed_at: str,
    fresh_after: str,
    topic: str,
    evidence_detail: dict[str, Any],
) -> AnomalySignal:
    severity, confidence = SIGNAL_PROFILE[signal_type]
    return AnomalySignal(
        signal_id=make_signal_id(
            run_id,
            round_id,
            "state_consistency",
            signal_type,
            observed_at,
            observed_value,
        ),
        run_id=run_id,
        round_id=round_id,
        scenario_id=scenario_id,
        source_agent="state_consistency",
        surface="state",
        signal_type=signal_type,
        severity=severity,
        observed_value=observed_value,
        expected=expected,
        observed_at=observed_at,
        evidence_refs=evidence_ref(topic, "ros2_topic", observed_at, evidence_detail),
        fresh_after=fresh_after,
        confidence=confidence,
    )


def detect_state_anomalies(
    snapshot: dict[str, Any],
    run_id: str,
    round_id: int,
    fresh_after: str,
    scenario_id: str = "B",
    odom_frame: str = DEFAULT_ODOM_FRAME,
    base_frame: str = DEFAULT_BASE_FRAME,
) -> list[AnomalySignal]:
    observed_at = str(snapshot.get("observed_at") or snapshot.get("ts") or utc_now())
    if not is_fresh(observed_at, fresh_after):
        return []

    signals = []
    odom = snapshot.get("odom", {})
    tf_transforms = snapshot.get("tf", [])
    scan = snapshot.get("scan", {})

    if isinstance(odom, dict) and isinstance(tf_transforms, list):
        transform = find_tf_transform(tf_transforms, odom_frame, base_frame)
        odom_pos = vector_from_pose(odom)
        tf_pos = vector_from_pose(transform or {})
        odom_ts = str(odom.get("ts") or observed_at)
        tf_ts = str((transform or {}).get("ts") or observed_at)
        age_delta = seconds_between(odom_ts, tf_ts)

        if (
            transform is not None
            and odom_pos is not None
            and tf_pos is not None
            and age_delta is not None
            and age_delta <= TF_TIME_TOLERANCE_S
        ):
            pos_delta = math.dist(odom_pos, tf_pos)
            if pos_delta > ODOM_TF_POS_TH:
                observed_value = {
                    "odom_position": odom_pos,
                    "tf_position": tf_pos,
                    "position_delta_m": round(pos_delta, 3),
                    "time_delta_s": round(age_delta, 3),
                    "odom_frame": frame_basename(odom_frame),
                    "base_frame": frame_basename(base_frame),
                }
                signals.append(
                    build_signal(
                        run_id,
                        round_id,
                        scenario_id,
                        "odom_tf_mismatch",
                        observed_value,
                        {
                            "max_position_delta_m": ODOM_TF_POS_TH,
                            "max_time_delta_s": TF_TIME_TOLERANCE_S,
                        },
                        observed_at,
                        fresh_after,
                        "/tf",
                        {"check": "odom_tf_position_delta", **observed_value},
                    )
                )

    if isinstance(scan, dict):
        detail = scan_anomaly_detail(scan)
        if detail is not None:
            signals.append(
                build_signal(
                    run_id,
                    round_id,
                    scenario_id,
                    "scan_anomaly",
                    detail,
                    {
                        "min_samples": SCAN_MIN_SAMPLES,
                        "max_dominant_ratio": SCAN_ANOMALY_RATIO,
                    },
                    observed_at,
                    fresh_after,
                    "/scan",
                    {"check": "scan_dominant_return_ratio", **detail},
                )
            )

    return signals


def demo_snapshot() -> dict[str, Any]:
    observed_at = utc_now()
    return {
        "observed_at": observed_at,
        "odom": {
            "ts": observed_at,
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
        },
        "tf": [
            {
                "ts": observed_at,
                "parent_frame": "odom",
                "child_frame": "base_link",
                "translation": {"x": ODOM_TF_POS_TH + 0.5, "y": 0.0, "z": 0.0},
            }
        ],
        "scan": {
            "ts": observed_at,
            "range_max": 10.0,
            "ranges": [10.0 for _ in range(SCAN_MIN_SAMPLES + 5)],
        },
    }


def ros_position(position: Any) -> dict[str, float]:
    return {
        "x": float(getattr(position, "x", 0.0)),
        "y": float(getattr(position, "y", 0.0)),
        "z": float(getattr(position, "z", 0.0)),
    }


def transform_record(transform: Any, observed_at: str) -> dict[str, Any]:
    return {
        "ts": observed_at,
        "parent_frame": str(getattr(transform.header, "frame_id", "")),
        "child_frame": str(getattr(transform, "child_frame_id", "")),
        "translation": ros_position(transform.transform.translation),
    }


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


def collect_live_snapshot(
    odom_topic: str = "/odometry/filtered",
    scan_topic: str = "/scan",
    tf_topic: str = "/tf",
    sample_seconds: float = 1.0,
) -> dict[str, Any]:
    if rclpy is None:
        print("rclpy is unavailable; use --demo or provide a JSON snapshot fixture.", file=sys.stderr)
        return {}

    try:
        from nav_msgs.msg import Odometry  # type: ignore[import-not-found]
        from sensor_msgs.msg import LaserScan  # type: ignore[import-not-found]
        from tf2_msgs.msg import TFMessage  # type: ignore[import-not-found]
    except ImportError as exc:
        print(f"ROS2 message package unavailable: {exc}", file=sys.stderr)
        return {}

    observed_at = utc_now()
    latest_odom: dict[str, Any] = {}
    latest_scan: dict[str, Any] = {}
    transforms: list[dict[str, Any]] = []

    def on_odom(msg: Any) -> None:
        latest_odom.clear()
        latest_odom.update(
            {
                "ts": observed_at,
                "position": ros_position(msg.pose.pose.position),
            }
        )

    def on_scan(msg: Any) -> None:
        latest_scan.clear()
        latest_scan.update(
            {
                "ts": observed_at,
                "range_max": float(getattr(msg, "range_max", 0.0)),
                "ranges": [float(value) for value in list(getattr(msg, "ranges", []))],
            }
        )

    def on_tf(msg: Any) -> None:
        transforms[:] = [transform_record(item, observed_at) for item in msg.transforms]

    rclpy.init(args=None)
    node = rclpy.create_node("dah_state_consistency_snapshot")
    started = time.monotonic()
    try:
        node.create_subscription(Odometry, odom_topic, on_odom, 10)
        node.create_subscription(LaserScan, scan_topic, on_scan, 10)
        node.create_subscription(TFMessage, tf_topic, on_tf, 10)
        while time.monotonic() - started < max(0.05, sample_seconds):
            rclpy.spin_once(node, timeout_sec=0.05)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    return {
        "observed_at": utc_now(),
        "odom": latest_odom,
        "tf": transforms,
        "scan": latest_scan,
    }


def collect_live_signals(
    run_id: str,
    round_id: int,
    fresh_after: str,
    scenario_id: str = "B",
    odom_frame: str = DEFAULT_ODOM_FRAME,
    base_frame: str = DEFAULT_BASE_FRAME,
    odom_topic: str = "/odometry/filtered",
    scan_topic: str = "/scan",
    tf_topic: str = "/tf",
    sample_seconds: float = 1.0,
) -> list[AnomalySignal]:
    """Stream the live topics and latch any anomaly seen during the window.

    A transient injection (Adapter B publishes ~20 messages over ~1s) competes
    with the simulation's continuous legitimate traffic on the same topics. A
    single last-write-wins snapshot at window end almost always lands on a
    legitimate message and misses the injection. Instead, evaluate every spin
    and keep the first anomalous sample per signal_type, so any anomalous frame
    within the window is detected regardless of what arrives last.
    """
    if rclpy is None:
        print("rclpy is unavailable; use --demo or provide a JSON snapshot fixture.", file=sys.stderr)
        return []

    try:
        from nav_msgs.msg import Odometry  # type: ignore[import-not-found]
        from sensor_msgs.msg import LaserScan  # type: ignore[import-not-found]
        from tf2_msgs.msg import TFMessage  # type: ignore[import-not-found]
    except ImportError as exc:
        print(f"ROS2 message package unavailable: {exc}", file=sys.stderr)
        return []

    latest_odom: dict[str, Any] = {}
    latest_scan: dict[str, Any] = {}
    transforms: list[dict[str, Any]] = []

    def on_odom(msg: Any) -> None:
        latest_odom.clear()
        latest_odom.update({"ts": utc_now(), "position": ros_position(msg.pose.pose.position)})

    def on_scan(msg: Any) -> None:
        latest_scan.clear()
        latest_scan.update(
            {
                "ts": utc_now(),
                "range_max": float(getattr(msg, "range_max", 0.0)),
                "ranges": [float(value) for value in list(getattr(msg, "ranges", []))],
            }
        )

    def on_tf(msg: Any) -> None:
        now = utc_now()
        transforms[:] = [transform_record(item, now) for item in msg.transforms]

    latched: dict[str, AnomalySignal] = {}

    rclpy.init(args=None)
    node = rclpy.create_node("dah_state_consistency_stream")
    started = time.monotonic()
    try:
        node.create_subscription(Odometry, odom_topic, on_odom, 10)
        node.create_subscription(LaserScan, scan_topic, on_scan, 10)
        node.create_subscription(TFMessage, tf_topic, on_tf, 10)
        while time.monotonic() - started < max(0.05, sample_seconds):
            rclpy.spin_once(node, timeout_sec=0.05)
            snapshot = {
                "observed_at": utc_now(),
                "odom": dict(latest_odom),
                "tf": list(transforms),
                "scan": dict(latest_scan),
            }
            for signal in detect_state_anomalies(
                snapshot=snapshot,
                run_id=run_id,
                round_id=round_id,
                fresh_after=fresh_after,
                scenario_id=scenario_id,
                odom_frame=odom_frame,
                base_frame=base_frame,
            ):
                latched.setdefault(signal.signal_type, signal)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    return list(latched.values())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect deterministic state consistency anomaly signals."
    )
    parser.add_argument("--fresh-after", default=utc_now())
    parser.add_argument("--run-id", default="")
    parser.add_argument("--round-id", type=int, default=1)
    parser.add_argument("--scenario-id", default="B")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--snapshot")
    parser.add_argument("--sample-seconds", type=float, default=1.0)
    parser.add_argument("--odom-frame", default=DEFAULT_ODOM_FRAME)
    parser.add_argument("--base-frame", default=DEFAULT_BASE_FRAME)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.demo:
        snapshot = demo_snapshot()
    else:
        snapshot = load_snapshot(args.snapshot)

    if args.demo or snapshot:
        # Deterministic fixture/demo path: evaluate the single provided snapshot.
        signals = detect_state_anomalies(
            snapshot=snapshot,
            run_id=args.run_id,
            round_id=args.round_id,
            fresh_after=args.fresh_after,
            scenario_id=args.scenario_id,
            odom_frame=args.odom_frame,
            base_frame=args.base_frame,
        )
    else:
        # Live path: stream the topics and latch any anomaly seen in the window,
        # so a transient injection is not overwritten by legitimate traffic.
        signals = collect_live_signals(
            run_id=args.run_id,
            round_id=args.round_id,
            fresh_after=args.fresh_after,
            scenario_id=args.scenario_id,
            odom_frame=args.odom_frame,
            base_frame=args.base_frame,
            sample_seconds=args.sample_seconds,
        )

    for signal in signals:
        print(json.dumps(signal.to_dict(), ensure_ascii=False, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
