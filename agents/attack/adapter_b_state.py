"""Scenario B replay adapter for odometry and scan spoofing."""

import os
import time
from typing import Any

from agents.contracts import AttackAction


ADAPTER_NAME = "adapter_b_state"
DEFAULT_ROS_DOMAIN_ID = "17"
DEFAULT_MESSAGE_COUNT = 3
DEFAULT_DELAY_S = 0.05


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
        "odom": {
            "ts": observed_at,
            "position": {"x": 0.0, "y": 0.0, "z": 0.0},
        },
        "tf": [
            {
                "ts": observed_at,
                "parent_frame": "odom",
                "child_frame": "base_link",
                "translation": {"x": float(params.get("tf_x", 1.0)), "y": 0.0, "z": 0.0},
            }
        ],
        "scan": {
            "ts": observed_at,
            "range_max": float(params.get("range_max", 10.0)),
            "ranges": [
                float(params.get("range_max", 10.0))
                for _ in range(int(params.get("scan_samples", 25)))
            ],
        },
    }
    return result("simulated", action, {"snapshot": snapshot})


def inject(action: AttackAction) -> dict[str, Any]:
    if action.mode != "live" or not action.confirm_live_testbed_only:
        return result(
            "blocked",
            action,
            {"reason": "live injection requires --live --confirm-live-testbed-only"},
        )

    try:
        import rclpy  # type: ignore[import-not-found]
        from nav_msgs.msg import Odometry  # type: ignore[import-not-found]
        from sensor_msgs.msg import LaserScan  # type: ignore[import-not-found]
    except ImportError as exc:
        return result(
            "unavailable",
            action,
            {"reason": "rclpy, nav_msgs, or sensor_msgs unavailable", "error": str(exc)},
        )

    params = action.parameters
    os.environ.setdefault("ROS_DOMAIN_ID", str(params.get("ros_domain_id", DEFAULT_ROS_DOMAIN_ID)))
    count = max(1, int(params.get("message_count", DEFAULT_MESSAGE_COUNT)))
    delay_s = max(0.0, float(params.get("delay_s", DEFAULT_DELAY_S)))
    odom_topic = str(params.get("odom_topic", "/odometry/filtered"))
    scan_topic = str(params.get("scan_topic", "/scan"))

    rclpy.init(args=None)
    node = rclpy.create_node("dah_replay_state_adapter")
    try:
        odom_pub = node.create_publisher(Odometry, odom_topic, 10)
        scan_pub = node.create_publisher(LaserScan, scan_topic, 10)
        odom = Odometry()
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"
        odom.pose.pose.position.x = float(params.get("odom_x", 1.0))
        scan = LaserScan()
        scan.header.frame_id = "laser"
        scan.range_min = 0.0
        scan.range_max = float(params.get("range_max", 10.0))
        scan.ranges = [scan.range_max for _ in range(int(params.get("scan_samples", 25)))]
        observed_at = str(params.get("observed_at", params.get("fresh_after", "")))
        for _ in range(count):
            odom_pub.publish(odom)
            scan_pub.publish(scan)
            rclpy.spin_once(node, timeout_sec=0.0)
            time.sleep(delay_s)
    finally:
        node.destroy_node()
        rclpy.shutdown()

    snapshot = {
        "observed_at": observed_at,
        "odom": {
            "ts": observed_at,
            "position": {"x": odom.pose.pose.position.x, "y": 0.0, "z": 0.0},
        },
        "scan": {
            "ts": observed_at,
            "range_max": scan.range_max,
            "ranges": list(scan.ranges),
        },
    }
    return result(
        "injected",
        action,
        {
            "odom_topic": odom_topic,
            "scan_topic": scan_topic,
            "message_count": count,
            "snapshot": snapshot,
        },
    )
