#!/usr/bin/env python3

import argparse
import socket
import time

from pymavlink.dialects.v20 import common as mavlink2


class UdpWriter:
    def __init__(self, host: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target = (host, port)

    def write(self, data):
        if isinstance(data, str):
            data = data.encode("latin1")
        self.sock.sendto(data, self.target)

    def flush(self):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["forward", "turn", "stop"])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=14551)
    parser.add_argument("--duration", type=float, default=2.0)
    parser.add_argument("--rate", type=float, default=10.0)
    args = parser.parse_args()

    mav = mavlink2.MAVLink(UdpWriter(args.host, args.port), srcSystem=255, srcComponent=190)

    if args.mode == "forward":
        x, y, z, r = 900, 0, 0, 0
    elif args.mode == "turn":
        x, y, z, r = 0, 0, 0, 900
    else:
        x, y, z, r = 0, 0, 0, 0

    count = max(1, int(args.duration * args.rate))
    delay = 1.0 / args.rate

    for _ in range(count):
        mav.manual_control_send(
            1,
            x,
            y,
            z,
            r,
            0,
        )
        time.sleep(delay)

    for _ in range(5):
        mav.manual_control_send(1, 0, 0, 0, 0, 0)
        time.sleep(delay)

    print(f"sent MANUAL_CONTROL mode={args.mode}, duration={args.duration}s")


if __name__ == "__main__":
    main()
