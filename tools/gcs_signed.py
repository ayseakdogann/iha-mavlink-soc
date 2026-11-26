#!/usr/bin/env python3
"""Mesru Yer Istasyonu (imzali komut). Savunma acikken bile kabul edilir."""
import argparse
import socket
import time

from pymavlink.dialects.v20 import common as mavlink2

SIGNING_KEY = bytes([0x01]) * 32
LEGIT_GCS_SYSID = 254
LEGIT_GCS_COMPID = 190

CMDS = {
    "LAND": mavlink2.MAV_CMD_NAV_LAND,
    "RTL": mavlink2.MAV_CMD_NAV_RETURN_TO_LAUNCH,
    "DISARM": mavlink2.MAV_CMD_COMPONENT_ARM_DISARM,
}


class SignedSender:
    def __init__(self, host, port, sysid, compid):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))
        self.addr = (host, int(port))
        self.mav = mavlink2.MAVLink(self, srcSystem=sysid, srcComponent=compid)
        self.mav.signing.secret_key = SIGNING_KEY
        self.mav.signing.sign_outgoing = True
        self.mav.signing.link_id = 0
        self.mav.signing.timestamp = int(time.time() * 1e5) & 0xFFFFFFFFFFFF

    def write(self, data):
        self.sock.sendto(data, self.addr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="127.0.0.1:14561")
    ap.add_argument("--cmd", default="RTL", choices=list(CMDS.keys()))
    ap.add_argument("--repeat", type=int, default=1)
    args = ap.parse_args()

    host, port = args.target.split(":")
    s = SignedSender(host, port, LEGIT_GCS_SYSID, LEGIT_GCS_COMPID)
    print(f"[operator] IMZALI {args.cmd} komutu -> {args.target} (sysid={LEGIT_GCS_SYSID}, imzali)")
    for i in range(args.repeat):
        s.mav.command_long_send(
            1, mavlink2.MAV_COMP_ID_AUTOPILOT1,
            CMDS[args.cmd], 0, 0, 0, 0, 0, 0, 0, 0,
        )
        print(f"[operator] gonderildi ({i + 1}/{args.repeat})")
        time.sleep(0.5)
    print("[operator] tamam. (Savunma acik olsa bile kabul edilir.)")


if __name__ == "__main__":
    main()