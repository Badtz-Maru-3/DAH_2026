#!/usr/bin/env python3

import math
import os
import socket
import time
from typing import Optional, Tuple

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

from pymavlink.dialects.v20 import common as mavlink2


def env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def env_float(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


def env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def yaw_from_quaternion(q) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def local_xy_to_latlon(base_lat: float, base_lon: float, north_m: float, east_m: float) -> Tuple[float, float]:
    lat = base_lat + (north_m / 111_111.0)
    lon_scale = 111_111.0 * max(math.cos(math.radians(base_lat)), 0.01)
    lon = base_lon + (east_m / lon_scale)
    return lat, lon


class UdpMavlinkEndpoint:
    def __init__(self, local_ip: str, local_port: int, remote_ip: str, remote_port: int):
        self.remote = (remote_ip, remote_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((local_ip, local_port))
        self.sock.setblocking(False)

    def write(self, data):
        if isinstance(data, str):
            data = data.encode("latin1")
        return self.sock.sendto(data, self.remote)

    def flush(self):
        return None

    def recv_packet(self):
        return self.sock.recvfrom(4096)


class Ros2MavlinkBridge(Node):
    def __init__(self):
        super().__init__("ros2_mavlink_bridge")

        self.ros_domain_id = env_int("ROS_DOMAIN_ID", 17)
        self.qgc_ip = env_str("QGC_IP", "127.0.0.1")
        self.qgc_port = env_int("QGC_PORT", 14550)
        self.bridge_local_port = env_int("BRIDGE_LOCAL_PORT", 14551)

        self.system_id = env_int("MAV_SYS_ID", 1)
        self.component_id = env_int("MAV_COMP_ID", 1)

        self.max_linear = env_float("MAX_LINEAR", 0.5)
        self.max_angular = env_float("MAX_ANGULAR", 1.2)
        self.cmd_timeout = env_float("CMD_TIMEOUT", 0.6)

        self.base_lat = env_float("BASE_LAT", 37.5665)
        self.base_lon = env_float("BASE_LON", 126.9780)
        self.base_alt = env_float("BASE_ALT", 50.0)

        self.transport = UdpMavlinkEndpoint(
            local_ip="0.0.0.0",
            local_port=self.bridge_local_port,
            remote_ip=self.qgc_ip,
            remote_port=self.qgc_port,
        )

        self.mav = mavlink2.MAVLink(
            self.transport,
            srcSystem=self.system_id,
            srcComponent=self.component_id,
        )
        self.mav.robust_parsing = True

        self.cmd_pub = self.create_publisher(Twist, "/cmd_vel", 10)
        self.odom_sub = self.create_subscription(
            Odometry,
            "/odometry/filtered",
            self.on_odom,
            10,
        )

        self.last_odom: Optional[Odometry] = None
        self.last_cmd_time: Optional[float] = None
        self.sent_idle_stop = False
        self.start_time = time.monotonic()
        self.last_cmd_log = 0.0
        self.last_odom_log = 0.0
        self.last_statustext = 0.0

        self.params = [
            ("SYSID_THISMAV", float(self.system_id), mavlink2.MAV_PARAM_TYPE_INT32),
            ("SYSID_MYGCS", 255.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("MAV_TYPE", float(mavlink2.MAV_TYPE_GROUND_ROVER), mavlink2.MAV_PARAM_TYPE_INT32),
            ("FRAME_CLASS", 1.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("ARMING_CHECK", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("FS_GCS_ENABLE", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("INITIAL_MODE", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),

            ("RCMAP_ROLL", 1.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RCMAP_PITCH", 2.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RCMAP_THROTTLE", 3.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RCMAP_YAW", 4.0, mavlink2.MAV_PARAM_TYPE_INT32),

            ("RC1_MIN", 1000.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RC1_MAX", 2000.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RC1_TRIM", 1500.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RC2_MIN", 1000.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RC2_MAX", 2000.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RC2_TRIM", 1500.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RC3_MIN", 1000.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RC3_MAX", 2000.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RC3_TRIM", 1500.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RC4_MIN", 1000.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RC4_MAX", 2000.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("RC4_TRIM", 1500.0, mavlink2.MAV_PARAM_TYPE_INT32),

            ("FLTMODE1", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("FLTMODE2", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("FLTMODE3", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("FLTMODE4", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("FLTMODE5", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("FLTMODE6", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),

            ("COMPASS_DEV_ID", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("COMPASS_DEV_ID2", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("COMPASS_DEV_ID3", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),
            ("COMPASS_DEC", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),

            ("COMPASS_OFS_X", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),
            ("COMPASS_OFS_Y", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),
            ("COMPASS_OFS_Z", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),
            ("COMPASS_OFS2_X", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),
            ("COMPASS_OFS2_Y", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),
            ("COMPASS_OFS2_Z", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),
            ("COMPASS_OFS3_X", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),
            ("COMPASS_OFS3_Y", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),
            ("COMPASS_OFS3_Z", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),

            ("INS_ACCOFFS_X", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),
            ("INS_ACCOFFS_Y", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),
            ("INS_ACCOFFS_Z", 0.0, mavlink2.MAV_PARAM_TYPE_REAL32),

            ("BATT_MONITOR", 0.0, mavlink2.MAV_PARAM_TYPE_INT32),
        ]

        self.create_timer(1.0, self.send_heartbeat)
        self.create_timer(0.2, self.send_telemetry)
        self.create_timer(0.02, self.receive_mavlink)
        self.create_timer(0.1, self.cmd_watchdog)

        self.get_logger().info(
            f"Bridge up: ROS_DOMAIN_ID={self.ros_domain_id}, "
            f"MAVLink 0.0.0.0:{self.bridge_local_port} -> {self.qgc_ip}:{self.qgc_port}, "
            f"ROS /cmd_vel <-> /odometry/filtered"
        )

    def time_boot_ms(self) -> int:
        return int((time.monotonic() - self.start_time) * 1000) & 0xFFFFFFFF

    def on_odom(self, msg: Odometry):
        self.last_odom = msg
        now = time.monotonic()
        if now - self.last_odom_log > 3.0:
            p = msg.pose.pose.position
            self.get_logger().info(f"odom received: x={p.x:.2f}, y={p.y:.2f}, z={p.z:.2f}")
            self.last_odom_log = now

    def send_heartbeat(self):
        base_mode = (
            mavlink2.MAV_MODE_FLAG_MANUAL_INPUT_ENABLED
            | mavlink2.MAV_MODE_FLAG_SAFETY_ARMED
        )

        self.mav.heartbeat_send(
            mavlink2.MAV_TYPE_GROUND_ROVER,
            mavlink2.MAV_AUTOPILOT_ARDUPILOTMEGA,
            base_mode,
            0,
            mavlink2.MAV_STATE_ACTIVE,
        )

        now = time.monotonic()
        if now - self.last_statustext > 10.0:
            self.mav.statustext_send(
                mavlink2.MAV_SEVERITY_INFO,
                b"DAH ROS2-MAVLink bridge alive",
            )
            self.last_statustext = now

    def send_empty_mission_count(self, msg):
        target_system = msg.get_srcSystem()
        target_component = msg.get_srcComponent()
        mission_type = int(getattr(msg, "mission_type", 0))

        try:
            self.mav.mission_count_send(target_system, target_component, 0, mission_type)
        except TypeError:
            self.mav.mission_count_send(target_system, target_component, 0)

        self.get_logger().info(f"MISSION_REQUEST_LIST -> empty count, mission_type={mission_type}")

    def send_param_value(self, index: int):
        if index < 0 or index >= len(self.params):
            return

        name, value, param_type = self.params[index]
        self.mav.param_value_send(
            name.encode("ascii"),
            float(value),
            param_type,
            len(self.params),
            index,
        )
        self.get_logger().info(f"PARAM_VALUE {index + 1}/{len(self.params)}: {name}={value}")

    def send_all_params(self):
        self.get_logger().info("PARAM_REQUEST_LIST -> sending minimal parameter set")
        for i in range(len(self.params)):
            self.send_param_value(i)

    def decode_param_id(self, raw):
        if isinstance(raw, bytes):
            return raw.decode("ascii", errors="ignore").rstrip("\x00")
        return str(raw).rstrip("\x00")

    def handle_param_request_read(self, msg):
        param_index = int(getattr(msg, "param_index", -1))
        if param_index >= 0:
            self.send_param_value(param_index)
            return

        param_id = self.decode_param_id(getattr(msg, "param_id", ""))
        for i, (name, _value, _type) in enumerate(self.params):
            if name == param_id:
                self.send_param_value(i)
                return

        self.get_logger().warn(f"unknown PARAM_REQUEST_READ: {param_id}")

    def send_telemetry(self):
        if self.last_odom is None:
            return

        odom = self.last_odom
        t = self.time_boot_ms()

        p = odom.pose.pose.position
        v = odom.twist.twist.linear
        q = odom.pose.pose.orientation

        # ROS ENU-ish local pose를 MAVLink NED 유사 값으로 단순 매핑.
        # prototype 기준: ROS x -> north, ROS y -> east, ROS z -> -down
        north = float(p.x)
        east = float(p.y)
        down = float(-p.z)

        vn = float(v.x)
        ve = float(v.y)
        vd = float(-v.z)

        self.mav.local_position_ned_send(
            t,
            north,
            east,
            down,
            vn,
            ve,
            vd,
        )

        lat, lon = local_xy_to_latlon(self.base_lat, self.base_lon, north, east)
        rel_alt_mm = int(max(0.0, -down) * 1000.0)
        alt_mm = int(self.base_alt * 1000.0) + rel_alt_mm

        yaw = yaw_from_quaternion(q)
        hdg = int((math.degrees(yaw) % 360.0) * 100.0)

        self.mav.global_position_int_send(
            t,
            int(lat * 1e7),
            int(lon * 1e7),
            alt_mm,
            rel_alt_mm,
            int(vn * 100.0),
            int(ve * 100.0),
            int(vd * 100.0),
            hdg,
        )

    def receive_mavlink(self):
        while True:
            try:
                data, _addr = self.transport.recv_packet()
                now = time.monotonic()
                if not hasattr(self, "_last_raw_udp_log"):
                    self._last_raw_udp_log = 0.0
                if now - self._last_raw_udp_log > 1.0:
                    self.get_logger().info(f"RAW UDP RX: {len(data)} bytes from {_addr}")
                    self._last_raw_udp_log = now
            except BlockingIOError:
                break
            except Exception as exc:
                self.get_logger().warn(f"MAVLink recv error: {exc}")
                break

            for byte in data:
                try:
                    msg = self.mav.parse_char(bytes([byte]))
                except Exception:
                    continue

                if msg is not None:
                    self.handle_mavlink_msg(msg)

    def handle_mavlink_msg(self, msg):
        msg_type = msg.get_type()

        now = time.monotonic()
        if not hasattr(self, "_last_rx_type_log"):
            self._last_rx_type_log = {}
        if now - self._last_rx_type_log.get(msg_type, 0.0) > 1.0:
            self.get_logger().info(f"MAVLink RX: {msg_type}")
            self._last_rx_type_log[msg_type] = now

        if msg_type == "MISSION_REQUEST_LIST":
            self.send_empty_mission_count(msg)

        elif msg_type == "PARAM_REQUEST_LIST":
            self.send_all_params()

        elif msg_type == "PARAM_REQUEST_READ":
            self.handle_param_request_read(msg)

        elif msg_type == "MANUAL_CONTROL":
            x_axis = clamp(float(getattr(msg, "x", 0)) / 1000.0, -1.0, 1.0)

            r_raw = float(getattr(msg, "r", 0))
            y_raw = float(getattr(msg, "y", 0))
            yaw_axis_raw = r_raw if abs(r_raw) > 10.0 else y_raw
            yaw_axis = clamp(yaw_axis_raw / 1000.0, -1.0, 1.0)

            self.publish_cmd_vel(
                linear=x_axis * self.max_linear,
                angular=yaw_axis * self.max_angular,
                source="MANUAL_CONTROL",
            )

        elif msg_type == "RC_CHANNELS_OVERRIDE":
            steer = self.norm_rc(getattr(msg, "chan1_raw", 1500))
            throttle = self.norm_rc(getattr(msg, "chan3_raw", 1500))

            self.publish_cmd_vel(
                linear=throttle * self.max_linear,
                angular=steer * self.max_angular,
                source="RC_CHANNELS_OVERRIDE",
            )

        elif msg_type == "COMMAND_LONG":
            command = int(getattr(msg, "command", 0))
            self.mav.command_ack_send(command, mavlink2.MAV_RESULT_ACCEPTED)

        elif msg_type == "PING":
            self.mav.ping_send(
                getattr(msg, "time_usec", 0),
                getattr(msg, "seq", 0),
                msg.get_srcSystem(),
                msg.get_srcComponent(),
            )

    def norm_rc(self, value) -> float:
        try:
            value = int(value)
        except Exception:
            return 0.0

        if value in (0, 65534, 65535):
            return 0.0

        return clamp((float(value) - 1500.0) / 500.0, -1.0, 1.0)

    def publish_cmd_vel(self, linear: float, angular: float, source: str):
        cmd = Twist()
        cmd.linear.x = float(linear)
        cmd.angular.z = float(angular)

        self.cmd_pub.publish(cmd)
        self.last_cmd_time = time.monotonic()
        self.sent_idle_stop = False

        now = time.monotonic()
        if now - self.last_cmd_log > 1.0:
            self.get_logger().info(
                f"{source} -> /cmd_vel linear.x={linear:.3f}, angular.z={angular:.3f}"
            )
            self.last_cmd_log = now

    def cmd_watchdog(self):
        if self.last_cmd_time is None:
            return

        if time.monotonic() - self.last_cmd_time > self.cmd_timeout and not self.sent_idle_stop:
            cmd = Twist()
            self.cmd_pub.publish(cmd)
            self.sent_idle_stop = True
            self.get_logger().info("cmd timeout -> publish zero /cmd_vel")


def main():
    rclpy.init()
    node = Ros2MavlinkBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
