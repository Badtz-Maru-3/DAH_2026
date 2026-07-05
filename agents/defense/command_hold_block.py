"""Deterministic command hold/block action mapping and gated hold publisher."""

from dataclasses import asdict, dataclass, field
from typing import Any

from agents.contracts import CorrelationVerdict


@dataclass(frozen=True)
class HoldBlockAction:
    mode: str = "dry-run"
    hold_engaged: bool = False
    command_blocked: bool = False
    active: bool = False
    cmd_vel: dict[str, float] = field(default_factory=dict)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def decide(
    verdict: CorrelationVerdict,
    mode: str,
    confirm_live_testbed_only: bool,
) -> HoldBlockAction:
    """Map a verdict to an action.

    Active zero-Twist publishing is a Batch 7 authoritative-override
    demonstration and remains simulation-bound plus gated.
    """

    should_hold = verdict.command_blocked or verdict.hold_engaged
    cmd_vel = {"linear": 0.0, "angular": 0.0} if should_hold else {}
    active = mode == "live" and confirm_live_testbed_only and should_hold

    if should_hold:
        reason = (
            f"hold/block intent from verdict: hold={verdict.hold_engaged} "
            f"block={verdict.command_blocked}; active={active}"
        )
    else:
        reason = "no hold/block intent"

    return HoldBlockAction(
        mode=mode,
        hold_engaged=verdict.hold_engaged,
        command_blocked=verdict.command_blocked,
        active=active,
        cmd_vel=cmd_vel,
        reason=reason,
    )


def publish_zero_twist_hold(
    action: HoldBlockAction,
    mode: str,
    confirm_live_testbed_only: bool,
    topic: str = "/cmd_vel",
    message_count: int = 5,
    delay_s: float = 0.05,
) -> dict[str, Any]:
    """Publish a gated zero-Twist hold when live dependencies are available."""

    result = {
        "adapter": "command_hold_block",
        "mode": mode,
        "detail": {
            "topic": topic,
            "action": action.to_dict(),
            "message_count": message_count,
            "delay_s": delay_s,
        },
    }

    if mode != "live" or not confirm_live_testbed_only:
        return {
            **result,
            "status": "blocked",
            "detail": {
                **result["detail"],
                "reason": "zero-Twist hold requires --live --confirm-live-testbed-only",
            },
        }

    if not (action.hold_engaged or action.command_blocked):
        return {
            **result,
            "status": "deferred",
            "detail": {**result["detail"], "reason": "no hold/block action requested"},
        }

    try:
        import time

        import rclpy  # type: ignore[import-not-found]
        from geometry_msgs.msg import Twist  # type: ignore[import-not-found]
    except ImportError as exc:
        return {
            **result,
            "status": "unavailable",
            "detail": {
                **result["detail"],
                "reason": "rclpy or geometry_msgs unavailable",
                "error": str(exc),
            },
        }

    rclpy.init(args=None)
    node = rclpy.create_node("dah_command_hold_block")
    try:
        publisher = node.create_publisher(Twist, topic, 10)
        msg = Twist()
        for _ in range(max(1, message_count)):
            publisher.publish(msg)
            rclpy.spin_once(node, timeout_sec=0.0)
            time.sleep(max(0.0, delay_s))
    finally:
        node.destroy_node()
        rclpy.shutdown()

    return {**result, "status": "injected"}
