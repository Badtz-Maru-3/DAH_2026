#!/usr/bin/env python3

import argparse
import os
import socket
import time
from typing import Optional

from pymavlink.dialects.v20 import common as mavlink2


BASE_LAT = 37.5665
BASE_LON = 126.9780

DEFAULT_TIMEOUT_S = 5.0
DEFAULT_MAX_ROUNDS = 50

MISSION_RESULT_NAMES = {
    int(value): name
    for name, value in vars(mavlink2).items()
    if name.startswith("MAV_MISSION_")
    and isinstance(value, int)
    and "_TYPE_" not in name
    and not name.endswith("_ENUM_END")
}


class UdpMavlinkClientEndpoint:
    """Bidirectional UDP transport for a pymavlink.MAVLink instance.

    Bridge (Bridge/ros2_mavlink_bridge.py: UdpMavlinkEndpoint) always sends its
    replies to a single fixed (QGC_IP, QGC_PORT) peer, not back to whichever port
    a packet arrived from. A real MISSION_REQUEST_INT / MISSION_ACK round trip
    therefore requires this client to bind to that same reply port to receive
    Bridge's replies -- see --reply-port / --reply-bind-ip below.
    """

    def __init__(self, remote_ip: str, remote_port: int, bind_ip: str, bind_port: int):
        self.remote = (remote_ip, remote_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((bind_ip, bind_port))
        self.sock.setblocking(False)

    def write(self, data):
        if isinstance(data, str):
            data = data.encode("latin1")
        return self.sock.sendto(data, self.remote)

    def flush(self):
        return None

    def recv_packet(self, bufsize: int = 4096) -> Optional[bytes]:
        try:
            data, _ = self.sock.recvfrom(bufsize)
            return data
        except BlockingIOError:
            return None


def build_mission_items(case: str):
    if case == "normal":
        return [
            (BASE_LAT + 0.00005, BASE_LON + 0.00002, 50.0),
            (BASE_LAT + 0.00008, BASE_LON + 0.00004, 50.0),
        ]
    if case == "malicious_far":
        return [
            (BASE_LAT + 0.02000, BASE_LON + 0.02000, 50.0),
        ]
    return [
        (BASE_LAT + 0.00005, BASE_LON + 0.00002, 50.0),
        (BASE_LAT + 0.01000, BASE_LON + 0.01000, 50.0),
    ]


def send_mission_count(mav, count: int, mission_type: int = 0):
    try:
        mav.mission_count_send(1, 1, count, mission_type)
    except TypeError:
        mav.mission_count_send(1, 1, count)


def send_item(mav, seq: int, lat: float, lon: float, alt: float, mission_type: int = 0):
    frame = int(getattr(mavlink2, "MAV_FRAME_GLOBAL_RELATIVE_ALT_INT", 3))
    command = int(getattr(mavlink2, "MAV_CMD_NAV_WAYPOINT", 16))

    try:
        mav.mission_item_int_send(
            1, 1, seq, frame, command,
            1 if seq == 0 else 0,
            1,
            0, 0, 0, 0,
            int(lat * 1e7),
            int(lon * 1e7),
            alt,
            mission_type,
        )
    except TypeError:
        mav.mission_item_int_send(
            1, 1, seq, frame, command,
            1 if seq == 0 else 0,
            1,
            0, 0, 0, 0,
            int(lat * 1e7),
            int(lon * 1e7),
            alt,
        )


def run_handshake(
    mav,
    transport: UdpMavlinkClientEndpoint,
    items: list,
    timeout_s: float,
    max_rounds: int,
) -> dict:
    """Real MISSION_COUNT -> MISSION_REQUEST_INT -> MISSION_ITEM_INT -> MISSION_ACK
    handshake against Bridge/mission_audit.py's MissionAudit.handle(). Mirrors the
    request/response pattern in MissionAudit.start_upload()/receive_item(): Bridge
    asks for one seq at a time via mission_request_int_send() and only sends
    MISSION_ACK once every item has been received and audited."""

    send_mission_count(mav, len(items))

    deadline = time.monotonic() + timeout_s
    rounds = 0
    sent_seqs: set[int] = set()

    while time.monotonic() < deadline and rounds < max_rounds:
        data = transport.recv_packet()
        if data is None:
            time.sleep(0.02)
            continue

        for byte in data:
            msg = mav.parse_char(bytes([byte]))
            if msg is None:
                continue

            msg_type = msg.get_type()

            if msg_type == "MISSION_ACK":
                result = int(getattr(msg, "type", -1))
                return {
                    "status": "acked",
                    "result": result,
                    "result_name": MISSION_RESULT_NAMES.get(result, str(result)),
                    "rounds": rounds,
                    "sent_seqs": sorted(sent_seqs),
                }

            if msg_type in ("MISSION_REQUEST_INT", "MISSION_REQUEST"):
                rounds += 1
                seq = int(getattr(msg, "seq", -1))
                if seq < 0 or seq >= len(items):
                    continue
                lat, lon, alt = items[seq]
                send_item(mav, seq, lat, lon, alt)
                sent_seqs.add(seq)
                deadline = time.monotonic() + timeout_s

    return {
        "status": "timeout",
        "result": None,
        "result_name": "no MISSION_ACK received before timeout",
        "rounds": rounds,
        "sent_seqs": sorted(sent_seqs),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=["normal", "malicious_far", "malicious_jump"])
    parser.add_argument("--port", type=int, default=14551, help="Bridge's MAVLink listen port (BRIDGE_LOCAL_PORT).")
    parser.add_argument(
        "--reply-port",
        type=int,
        default=int(os.environ.get("QGC_PORT", "14550")),
        help=(
            "Local port to bind for receiving Bridge's MISSION_REQUEST_INT / MISSION_ACK "
            "replies. Bridge always replies to its configured QGC_IP:QGC_PORT, so this must "
            "match that value -- which means the real QGC client must not be bound to it "
            "concurrently. Defaults to the QGC_PORT env var (falls back to 14550)."
        ),
    )
    parser.add_argument("--reply-bind-ip", default="0.0.0.0")
    parser.add_argument("--timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    args = parser.parse_args()

    items = build_mission_items(args.case)

    transport = UdpMavlinkClientEndpoint(
        remote_ip="127.0.0.1",
        remote_port=args.port,
        bind_ip=args.reply_bind_ip,
        bind_port=args.reply_port,
    )
    mav = mavlink2.MAVLink(transport, srcSystem=250, srcComponent=190)
    mav.robust_parsing = True

    outcome = run_handshake(mav, transport, items, args.timeout_s, DEFAULT_MAX_ROUNDS)

    print(
        f"sent {args.case} mission with {len(items)} item(s); "
        f"handshake status={outcome['status']} result={outcome['result_name']} "
        f"rounds={outcome['rounds']} sent_seqs={outcome['sent_seqs']}"
    )
    return 0 if outcome["status"] == "acked" else 1


if __name__ == "__main__":
    raise SystemExit(main())
