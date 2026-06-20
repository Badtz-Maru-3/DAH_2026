#!/usr/bin/env python3

import json
import math
import os
import time
from pathlib import Path
from typing import Optional, Tuple

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


def local_xy_to_latlon(base_lat: float, base_lon: float, north_m: float, east_m: float) -> Tuple[float, float]:
    lat = base_lat + (north_m / 111111.0)
    lon_scale = 111111.0 * max(math.cos(math.radians(base_lat)), 0.01)
    lon = base_lon + (east_m / lon_scale)
    return lat, lon


class GnssIntegrity:
    def __init__(self, node):
        self.node = node

        self.base_lat = env_float("BASE_LAT", 37.5665)
        self.base_lon = env_float("BASE_LON", 126.9780)

        self.max_residual_m = env_float("GNSS_MAX_RESIDUAL_M", 30.0)
        self.min_fix_type = env_int("GNSS_MIN_FIX_TYPE", 3)
        self.min_satellites = env_int("GNSS_MIN_SATELLITES", 6)
        self.max_horiz_accuracy_m = env_float("GNSS_MAX_HACC_M", 15.0)

        self.log_path = Path(env_str("GNSS_INTEGRITY_LOG", "/logs/gnss_integrity.log"))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self.last_status = "unknown"

    def handle(self, msg) -> bool:
        if msg.get_type() != "GPS_INPUT":
            return False

        lat = float(getattr(msg, "lat", 0)) / 1e7
        lon = float(getattr(msg, "lon", 0)) / 1e7
        alt = float(getattr(msg, "alt", 0.0))
        fix_type = int(getattr(msg, "fix_type", 0))
        sats = int(getattr(msg, "satellites_visible", 0))
        hacc = float(getattr(msg, "horiz_accuracy", 9999.0))

        expected = self.expected_position()
        reasons = []

        residual_m: Optional[float] = None

        if expected is not None:
            exp_lat, exp_lon = expected
            residual_m = haversine_m(exp_lat, exp_lon, lat, lon)

            if residual_m > self.max_residual_m:
                reasons.append(
                    f"position residual {residual_m:.2f}m > limit {self.max_residual_m:.2f}m"
                )
        else:
            exp_lat, exp_lon = None, None
            reasons.append("no odometry reference available")

        if fix_type < self.min_fix_type:
            reasons.append(f"fix_type {fix_type} < required {self.min_fix_type}")

        if sats < self.min_satellites:
            reasons.append(f"satellites {sats} < required {self.min_satellites}")

        if hacc > self.max_horiz_accuracy_m:
            reasons.append(f"horiz_accuracy {hacc:.2f}m > limit {self.max_horiz_accuracy_m:.2f}m")

        result = "accepted" if not reasons else "rejected"
        self.last_status = result

        self.audit_log(
            "gps_input",
            result=result,
            lat=lat,
            lon=lon,
            alt=alt,
            expected_lat=exp_lat,
            expected_lon=exp_lon,
            residual_m=residual_m,
            fix_type=fix_type,
            satellites_visible=sats,
            horiz_accuracy=hacc,
            reasons=reasons,
        )

        if result == "rejected":
            try:
                self.node.mav.statustext_send(
                    mavlink2.MAV_SEVERITY_WARNING,
                    b"GNSS integrity rejected",
                )
            except Exception:
                pass

        self.node.get_logger().info(
            f"[gnss_integrity] result={result}, residual_m={residual_m}, "
            f"fix_type={fix_type}, sats={sats}, reasons={reasons}"
        )

        return True

    def expected_position(self) -> Optional[Tuple[float, float]]:
        odom = getattr(self.node, "last_odom", None)
        if odom is None:
            return None

        p = odom.pose.pose.position
        north = float(p.x)
        east = float(p.y)

        return local_xy_to_latlon(self.base_lat, self.base_lon, north, east)

    def audit_log(self, event: str, **fields):
        record = {
            "ts": utc_now(),
            "event": event,
            **fields,
        }

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        corr = getattr(self.node, "correlation_engine", None)
        if corr is not None and event == "gps_input":
            if fields.get("result") == "rejected":
                corr.record_signal(
                    source="gnss_integrity",
                    kind="rejected",
                    severity=1.0,
                    detail=fields,
                )
