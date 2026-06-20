#!/usr/bin/env python3

import json
import math
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pymavlink.dialects.v20 import common as mavlink2


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


def env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return 2.0 * radius * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


class MissionAudit:
    def __init__(self, node):
        self.node = node

        self.base_lat = env_float("BASE_LAT", 37.5665)
        self.base_lon = env_float("BASE_LON", 126.9780)

        self.max_items = env_int("MISSION_MAX_ITEMS", 20)
        self.geofence_radius_m = env_float("MISSION_GEOFENCE_RADIUS_M", 300.0)
        self.max_jump_m = env_float("MISSION_MAX_JUMP_M", 120.0)
        self.min_alt_m = env_float("MISSION_MIN_ALT_M", -20.0)
        self.max_alt_m = env_float("MISSION_MAX_ALT_M", 200.0)

        allowed = env_str("MISSION_ALLOWED_COMMANDS", "16,20")
        self.allowed_commands = {int(x.strip()) for x in allowed.split(",") if x.strip()}

        self.log_path = Path(env_str("MISSION_AUDIT_LOG", "/logs/mission_audit.log"))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self.pending: Optional[Dict] = None
        self.active_mission: List[Dict] = []

        self.global_frames = {
            int(getattr(mavlink2, "MAV_FRAME_GLOBAL", 0)),
            int(getattr(mavlink2, "MAV_FRAME_GLOBAL_RELATIVE_ALT", 3)),
            int(getattr(mavlink2, "MAV_FRAME_GLOBAL_TERRAIN_ALT", 10)),
            int(getattr(mavlink2, "MAV_FRAME_GLOBAL_INT", 5)),
            int(getattr(mavlink2, "MAV_FRAME_GLOBAL_RELATIVE_ALT_INT", 6)),
            int(getattr(mavlink2, "MAV_FRAME_GLOBAL_TERRAIN_ALT_INT", 11)),
        }

        self.nav_waypoint = int(getattr(mavlink2, "MAV_CMD_NAV_WAYPOINT", 16))
        self.nav_rtl = int(getattr(mavlink2, "MAV_CMD_NAV_RETURN_TO_LAUNCH", 20))

    def handle(self, msg) -> bool:
        msg_type = msg.get_type()

        if msg_type == "MISSION_REQUEST_LIST":
            self.send_mission_count(msg)
            return True

        if msg_type == "MISSION_CLEAR_ALL":
            self.active_mission = []
            self.pending = None
            self.send_ack(msg, self.accepted_result(), "mission cleared")
            self.audit_log("mission_clear_all", result="accepted")
            return True

        if msg_type == "MISSION_COUNT":
            self.start_upload(msg)
            return True

        if msg_type in ("MISSION_ITEM_INT", "MISSION_ITEM"):
            self.receive_item(msg)
            return True

        return False

    def accepted_result(self) -> int:
        return int(getattr(mavlink2, "MAV_MISSION_ACCEPTED", 0))

    def rejected_result(self) -> int:
        return int(getattr(mavlink2, "MAV_MISSION_DENIED", getattr(mavlink2, "MAV_MISSION_INVALID", 5)))

    def sender(self, msg) -> Tuple[int, int]:
        src_sys = int(msg.get_srcSystem() or 255)
        src_comp = int(msg.get_srcComponent() or 0)
        return src_sys, src_comp

    def send_mission_count(self, msg):
        target_sys, target_comp = self.sender(msg)
        mission_type = int(getattr(msg, "mission_type", 0))
        count = len(self.active_mission)

        try:
            self.node.mav.mission_count_send(target_sys, target_comp, count, mission_type)
        except TypeError:
            self.node.mav.mission_count_send(target_sys, target_comp, count)

        self.audit_log("mission_request_list", result="count_sent", count=count)

    def send_ack(self, msg, result: int, reason: str, mission_type: Optional[int] = None):
        target_sys, target_comp = self.sender(msg)
        if mission_type is None:
            mission_type = int(getattr(msg, "mission_type", 0))

        try:
            self.node.mav.mission_ack_send(target_sys, target_comp, result, mission_type)
        except TypeError:
            self.node.mav.mission_ack_send(target_sys, target_comp, result)

        self.node.get_logger().info(f"MISSION_ACK result={result} reason={reason}")

    def request_item(self, seq: int):
        if self.pending is None:
            return

        target_sys = self.pending["src_sys"]
        target_comp = self.pending["src_comp"]
        mission_type = self.pending["mission_type"]

        try:
            self.node.mav.mission_request_int_send(target_sys, target_comp, seq, mission_type)
        except TypeError:
            self.node.mav.mission_request_int_send(target_sys, target_comp, seq)

        self.audit_log("mission_request_int", seq=seq)

    def start_upload(self, msg):
        count = int(getattr(msg, "count", 0))
        mission_type = int(getattr(msg, "mission_type", 0))
        src_sys, src_comp = self.sender(msg)

        if count < 0 or count > self.max_items:
            self.pending = None
            reason = f"mission item count out of range: {count}"
            self.send_ack(msg, self.rejected_result(), reason, mission_type)
            self.audit_log("mission_upload_start", result="rejected", reason=reason, count=count)
            return

        if count == 0:
            self.active_mission = []
            self.pending = None
            self.send_ack(msg, self.accepted_result(), "empty mission accepted", mission_type)
            self.audit_log("mission_upload_start", result="accepted", count=0)
            return

        self.pending = {
            "src_sys": src_sys,
            "src_comp": src_comp,
            "count": count,
            "mission_type": mission_type,
            "items": {},
            "started_at": time.monotonic(),
        }

        self.audit_log("mission_upload_start", result="pending", count=count)
        self.request_item(0)

    def receive_item(self, msg):
        if self.pending is None:
            self.audit_log("mission_item_unexpected", msg_type=msg.get_type())
            return

        item = self.extract_item(msg)
        seq = item["seq"]
        count = self.pending["count"]

        if seq < 0 or seq >= count:
            reason = f"invalid seq {seq} for count {count}"
            self.send_ack(msg, self.rejected_result(), reason, self.pending["mission_type"])
            self.audit_log("mission_item", result="rejected", reason=reason, seq=seq)
            self.pending = None
            return

        self.pending["items"][seq] = item
        self.audit_log(
            "mission_item",
            result="received",
            seq=seq,
            command=item["command"],
            lat=item["lat"],
            lon=item["lon"],
            alt=item["alt"],
        )

        if len(self.pending["items"]) < count:
            for next_seq in range(count):
                if next_seq not in self.pending["items"]:
                    self.request_item(next_seq)
                    return

        items = [self.pending["items"][i] for i in range(count)]
        accepted, reasons = self.audit_items(items)

        if accepted:
            self.active_mission = items
            self.send_ack(msg, self.accepted_result(), "mission accepted", self.pending["mission_type"])
            self.audit_log("mission_audit_result", result="accepted", count=count)
        else:
            self.send_ack(msg, self.rejected_result(), "; ".join(reasons), self.pending["mission_type"])
            self.audit_log("mission_audit_result", result="rejected", count=count, reasons=reasons)

        self.pending = None

    def extract_item(self, msg) -> Dict:
        msg_type = msg.get_type()

        if msg_type == "MISSION_ITEM_INT":
            lat = float(getattr(msg, "x", 0)) / 1e7
            lon = float(getattr(msg, "y", 0)) / 1e7
        else:
            lat = float(getattr(msg, "x", 0.0))
            lon = float(getattr(msg, "y", 0.0))

        return {
            "seq": int(getattr(msg, "seq", 0)),
            "frame": int(getattr(msg, "frame", 0)),
            "command": int(getattr(msg, "command", 0)),
            "current": int(getattr(msg, "current", 0)),
            "autocontinue": int(getattr(msg, "autocontinue", 0)),
            "param1": float(getattr(msg, "param1", 0.0)),
            "param2": float(getattr(msg, "param2", 0.0)),
            "param3": float(getattr(msg, "param3", 0.0)),
            "param4": float(getattr(msg, "param4", 0.0)),
            "lat": lat,
            "lon": lon,
            "alt": float(getattr(msg, "z", 0.0)),
            "msg_type": msg_type,
        }

    def audit_items(self, items: List[Dict]) -> Tuple[bool, List[str]]:
        reasons = []

        expected = list(range(len(items)))
        actual = [item["seq"] for item in items]
        if actual != expected:
            reasons.append(f"non-contiguous sequence: {actual}")

        last_lat = self.base_lat
        last_lon = self.base_lon

        for item in items:
            seq = item["seq"]
            command = item["command"]

            if command not in self.allowed_commands:
                reasons.append(f"seq={seq}: unsupported command={command}")
                continue

            if command == self.nav_rtl:
                continue

            if command != self.nav_waypoint:
                reasons.append(f"seq={seq}: command={command} not supported in audit v1")
                continue

            frame = item["frame"]
            lat = item["lat"]
            lon = item["lon"]
            alt = item["alt"]

            if frame not in self.global_frames:
                reasons.append(f"seq={seq}: unsupported frame={frame}")

            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                reasons.append(f"seq={seq}: invalid coordinate lat={lat}, lon={lon}")
                continue

            if not (self.min_alt_m <= alt <= self.max_alt_m):
                reasons.append(f"seq={seq}: altitude out of range alt={alt}")

            dist_from_base = haversine_m(self.base_lat, self.base_lon, lat, lon)
            if dist_from_base > self.geofence_radius_m:
                reasons.append(
                    f"seq={seq}: geofence violation distance={dist_from_base:.2f}m "
                    f"limit={self.geofence_radius_m:.2f}m"
                )

            jump = haversine_m(last_lat, last_lon, lat, lon)
            if jump > self.max_jump_m:
                reasons.append(
                    f"seq={seq}: waypoint jump={jump:.2f}m limit={self.max_jump_m:.2f}m"
                )

            last_lat = lat
            last_lon = lon

        return len(reasons) == 0, reasons

    def audit_log(self, event: str, **fields):
        record = {
            "ts": utc_now(),
            "event": event,
            **fields,
        }

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        corr = getattr(self.node, "correlation_engine", None)
        if corr is not None and event == "mission_audit_result":
            if fields.get("result") == "rejected":
                corr.record_signal(
                    source="mission_audit",
                    kind="rejected",
                    severity=1.0,
                    detail=fields,
                )

        if event in {"mission_upload_start", "mission_audit_result", "mission_item"}:
            self.node.get_logger().info(f"[mission_audit] {json.dumps(record, ensure_ascii=False)}")
