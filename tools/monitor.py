#!/usr/bin/env python3
"""Canli telemetri izleme konsolu + basit spoof (konum sicramasi) uyarisi."""
import argparse
import math
import time

from pymavlink import mavutil


def mesafe_m(lat1, lon1, lat2, lon2):
    dlat = (lat2 - lat1) * 111320.0
    dlon = (lon2 - lon1) * 111320.0 * math.cos(math.radians(lat1))
    return math.hypot(dlat, dlon)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--listen", default="127.0.0.1:14560")
    ap.add_argument("--jump", type=float, default=100.0)
    args = ap.parse_args()

    m = mavutil.mavlink_connection("udpin:" + args.listen)
    print(f"[monitor] dinleniyor: {args.listen}  (Ctrl+C ile cik)")
    print(f"{'zaman':>8} | {'enlem':>10} {'boylam':>10} | {'irtifa':>7} | durum")
    print("-" * 60)

    son_lat = son_lon = None
    while True:
        msg = m.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=5)
        if msg is None:
            continue
        lat = msg.lat / 1e7
        lon = msg.lon / 1e7
        alt = msg.relative_alt / 1000.0
        durum = "OK"
        if son_lat is not None:
            d = mesafe_m(son_lat, son_lon, lat, lon)
            if d > args.jump:
                durum = f"! SPOOF? ani {int(d)} m sicrama"
        son_lat, son_lon = lat, lon
        t = time.strftime("%H:%M:%S")
        print(f"{t:>8} | {lat:10.5f} {lon:10.5f} | {alt:6.1f}m | {durum}")


if __name__ == "__main__":
    main()