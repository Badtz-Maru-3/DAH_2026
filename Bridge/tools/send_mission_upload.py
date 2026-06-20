#!/usr/bin/env python3

import argparse
import time
from pymavlink import mavutil


BASE_LAT = 37.5665
BASE_LON = 126.9780


def send_item(mav, seq, lat, lon, alt=50.0):
    frame = mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT
    command = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT

    try:
        mav.mav.mission_item_int_send(
            1, 1, seq, frame, command,
            1 if seq == 0 else 0,
            1,
            0, 0, 0, 0,
            int(lat * 1e7),
            int(lon * 1e7),
            alt,
            0,
        )
    except TypeError:
        mav.mav.mission_item_int_send(
            1, 1, seq, frame, command,
            1 if seq == 0 else 0,
            1,
            0, 0, 0, 0,
            int(lat * 1e7),
            int(lon * 1e7),
            alt,
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=["normal", "malicious_far", "malicious_jump"])
    parser.add_argument("--port", type=int, default=14551)
    args = parser.parse_args()

    if args.case == "normal":
        items = [
            (BASE_LAT + 0.00005, BASE_LON + 0.00002, 50.0),
            (BASE_LAT + 0.00008, BASE_LON + 0.00004, 50.0),
        ]
    elif args.case == "malicious_far":
        items = [
            (BASE_LAT + 0.02000, BASE_LON + 0.02000, 50.0),
        ]
    else:
        items = [
            (BASE_LAT + 0.00005, BASE_LON + 0.00002, 50.0),
            (BASE_LAT + 0.01000, BASE_LON + 0.01000, 50.0),
        ]

    mav = mavutil.mavlink_connection(
        f"udpout:127.0.0.1:{args.port}",
        source_system=250,
        source_component=190,
        dialect="common",
    )

    try:
        mav.mav.mission_count_send(1, 1, len(items), 0)
    except TypeError:
        mav.mav.mission_count_send(1, 1, len(items))

    time.sleep(0.3)

    for seq, (lat, lon, alt) in enumerate(items):
        send_item(mav, seq, lat, lon, alt)
        time.sleep(0.3)

    print(f"sent {args.case} mission with {len(items)} item(s)")


if __name__ == "__main__":
    main()
