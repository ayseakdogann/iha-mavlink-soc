#!/usr/bin/env python3
"""Basit İHA MAVLink simülatörü. Telemetri yayar, komutlara tepki verir."""
import argparse
import math
import socket
import time

from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink2

SYSID = 1
COMPID = mavlink2.MAV_COMP_ID_AUTOPILOT1


class UDPSender:
    """MAVLink mesajlarini ham UDP soketiyle gonderir (hedef portu bind etmez)."""

    def __init__(self, host, port, sysid, compid):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))
        self.addr = (host, int(port))
        self.mav = mavlink2.MAVLink(self, srcSystem=sysid, srcComponent=compid)

    def write(self, data):
        self.sock.sendto(data, self.addr)


class DroneState:
    def __init__(self):
        self.armed = False
        self.mode = "AUTO"
        self.lat = 39.925018
        self.lon = 32.836956
        self.alt = 0.0
        self.target_alt = 50.0
        self.heading = 90.0
        self.ground_speed = 0.0
        self.battery = 100.0
        self.t0 = time.time()
        self.boot_ms = 0

    def step(self, dt):
        self.boot_ms = int((time.time() - self.t0) * 1000)
        if not self.armed:
            self.ground_speed = 0.0
            return
        if self.mode == "AUTO":
            if self.alt < self.target_alt:
                self.alt = min(self.target_alt, self.alt + 5.0 * dt)
            self.ground_speed = 12.0
        elif self.mode in ("LAND", "RTL"):
            self.alt = max(0.0, self.alt - 4.0 * dt)
            self.ground_speed = 6.0 if self.alt > 1 else 0.0
            if self.alt <= 0.1:
                self.armed = False
        d = self.ground_speed * dt
        self.lat += (d * math.cos(math.radians(self.heading))) / 111320.0
        self.lon += (d * math.sin(math.radians(self.heading))) / (
            111320.0 * math.cos(math.radians(self.lat))
        )
        self.battery = max(0.0, self.battery - 0.05 * dt)


MODE_MAP = {
    mavlink2.MAV_CMD_NAV_LAND: "LAND",
    mavlink2.MAV_CMD_NAV_RETURN_TO_LAUNCH: "RTL",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="127.0.0.1:14560")
    ap.add_argument("--in", dest="inp", default="127.0.0.1:14561")
    ap.add_argument("--rate", type=float, default=10.0)
    args = ap.parse_args()

    out_host, out_port = args.out.split(":")
    tx = UDPSender(out_host, out_port, SYSID, COMPID)
    rx = mavutil.mavlink_connection("udpin:" + args.inp, dialect="common")

    st = DroneState()
    st.armed = True
    period = 1.0 / args.rate
    last = time.time()
    hb_last = 0.0
    print(f"[sim] drone başladı, telemetri -> {args.out}, komut <- {args.inp}")

    while True:
        now = time.time()
        dt = now - last
        last = now
        st.step(dt)

        msg = rx.recv_match(blocking=False)
        while msg is not None:
            if msg.get_type() == "COMMAND_LONG":
                cmd = msg.command
                if cmd == mavlink2.MAV_CMD_COMPONENT_ARM_DISARM:
                    st.armed = bool(msg.param1 >= 0.5)
                    print(f"[sim] ARM/DISARM -> armed={st.armed}")
                elif cmd in MODE_MAP:
                    st.mode = MODE_MAP[cmd]
                    print(f"[sim] komut -> mod={st.mode}")
            msg = rx.recv_match(blocking=False)

        if now - hb_last >= 1.0:
            tx.mav.heartbeat_send(
                mavlink2.MAV_TYPE_QUADROTOR,
                mavlink2.MAV_AUTOPILOT_ARDUPILOTMEGA,
                mavlink2.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
                | (mavlink2.MAV_MODE_FLAG_SAFETY_ARMED if st.armed else 0),
                0,
                mavlink2.MAV_STATE_ACTIVE if st.armed else mavlink2.MAV_STATE_STANDBY,
            )
            hb_last = now

        tx.mav.global_position_int_send(
            st.boot_ms,
            int(st.lat * 1e7), int(st.lon * 1e7),
            int(st.alt * 1000), int(st.alt * 1000),
            0, 0, 0,
            int(st.heading * 100),
        )
        time.sleep(period)


if __name__ == "__main__":
    main()