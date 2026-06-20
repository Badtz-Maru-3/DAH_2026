#!/usr/bin/env python3

import argparse
import time
from pymavlink import mavutil


BASE_LAT = 37.5665
BASE_LON = 126.9780
BASE_ALT = 50.0


def send_gps_input(mav, lat, lon, alt, fix_type, sats, hacc):
    now_us = int(time.time() * 1_000_000)

    args = [
        now_us,          # time_usec
        0,               # gps_id
        0,               # ignore_flags
        0,               # time_week_ms
        0,               # time_week
        fix_type,
        int(lat * 1e7),
        int(lon * 1e7),
        float(alt),
        1.0,             # hdop
        1.0,             # vdop
        0.0,             # vn
        0.0,             # ve
        0.0,             # vd
        0.5,             # speed_accuracy
        float(hacc),     # horiz_accuracy
        1.0,             # vert_accuracy
        int(sats),       # satellites_visible
    ]

    try:
        mav.mav.gps_input_send(*args, 0)
    except TypeError:
        mav.mav.gps_input_send(*args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case", choices=["normal", "spoof_jump", "poor_fix"])
    parser.add_argument("--port", type=int, default=14551)
    args = parser.parse_args()

    if args.case == "normal":
        lat = BASE_LAT + 0.00002
        lon = BASE_LON + 0.00001
        fix_type = 3
        sats = 12
        hacc = 1.5
    elif args.case == "spoof_jump":
        lat = BASE_LAT + 0.02000
        lon = BASE_LON + 0.02000
        fix_type = 3
        sats = 12
        hacc = 1.5
    else:
        lat = BASE_LAT + 0.00002
        lon = BASE_LON + 0.00001
        fix_type = 1
        sats = 3
        hacc = 50.0

    mav = mavutil.mavlink_connection(
        f"udpout:127.0.0.1:{args.port}",
        source_system=251,
        source_component=191,
        dialect="common",
    )

    send_gps_input(mav, lat, lon, BASE_ALT, fix_type, sats, hacc)
    time.sleep(0.2)

    print(
        f"sent {args.case} GPS_INPUT "
        f"lat={lat}, lon={lon}, fix_type={fix_type}, sats={sats}, hacc={hacc}"
    )


if __name__ == "__main__":
    main()
