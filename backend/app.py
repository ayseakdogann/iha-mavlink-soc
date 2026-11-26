#!/usr/bin/env python3
"""
SOC Backend — köprü + tespit + web panel + yapay zeka raporu, tek serviste.

Bu servis:
  - Telemetriyi drondan alır (14560), komutları yer istasyonundan alır (14561),
    ikisini de ilgili tarafa iletir (köprü görevi).
  - Her paketi inceler, saldırı tespit ederse olay üretir.
  - Olayları ve canlı telemetriyi tarayıcıdaki panele WebSocket ile yayınlar.
  - Her olay için Türkçe bir "yapay zeka" raporu üretir (LLM anahtarı varsa onu,
    yoksa şablon tabanlı yedeği kullanır) — demo internetsiz de çalışır.

Çalıştırma:
  python backend/app.py
  Tarayıcı:  http://localhost:8000
Drone:   python sim/drone_sim.py --out 127.0.0.1:14560 --in 127.0.0.1:14571
Saldırı: python attacks/inject_land.py --target 127.0.0.1:14561 --cmd LAND
"""
import argparse
import asyncio
import math
import os
import socket
import threading
import time
from collections import deque
from pathlib import Path
from queue import Queue, Empty

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink2

# ----------------------------- Tespit (SOC çekirdeği) -----------------------
LEGIT_GCS_SYSID = 254
CRITICAL = {
    mavlink2.MAV_CMD_NAV_LAND: "LAND",
    mavlink2.MAV_CMD_NAV_RETURN_TO_LAUNCH: "RTL",
    mavlink2.MAV_CMD_COMPONENT_ARM_DISARM: "ARM/DISARM",
}
RECON_MSGS = {"PARAM_REQUEST_LIST", "MISSION_REQUEST_LIST", "REQUEST_DATA_STREAM"}


def mesafe_m(a, b, c, d):
    dlat = (c - a) * 111320.0
    dlon = (d - b) * 111320.0 * math.cos(math.radians(a))
    return math.hypot(dlat, dlon)


class RawSender:
    def __init__(self, host, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 0))
        self.addr = (host, int(port))

    def send(self, data):
        if data:
            self.sock.sendto(data, self.addr)


class Detector:
    def __init__(self, jump_m=100.0, flood_per_s=200):
        self.jump_m = jump_m
        self.flood_per_s = flood_per_s
        self.last_pos = None
        self.msg_times = deque()
        self.flood_active = False
        self.last_spoof = 0.0

    def _event(self, tur, siddet, aciklama, kaynak, mitre):
        return {"zaman": time.strftime("%H:%M:%S"), "tur": tur, "siddet": siddet,
                "aciklama": aciklama, "kaynak": kaynak, "mitre": mitre}

    def _flood_check(self, src):
        now = time.time()
        self.msg_times.append(now)
        while self.msg_times and now - self.msg_times[0] > 1.0:
            self.msg_times.popleft()
        hiz = len(self.msg_times)
        if hiz > self.flood_per_s and not self.flood_active:
            self.flood_active = True
            return self._event("FLOOD/DoS", "YUKSEK",
                               f"mesaj hizi {hiz}/s esigi ({self.flood_per_s}) asti",
                               f"sysid={src}", "T0814 Denial of Service")
        if hiz <= self.flood_per_s * 0.5:
            self.flood_active = False
        return None

    def on_command(self, msg):
        out = []
        src = msg.get_srcSystem()
        f = self._flood_check(src)
        if f:
            out.append(f)
        t = msg.get_type()
        if t == "COMMAND_LONG":
            krit = CRITICAL.get(msg.command)
            if src != LEGIT_GCS_SYSID:
                out.append(self._event("KOMUT ENJEKSIYONU", "KRITIK",
                          f"yetkisiz kaynaktan komut{' (' + krit + ')' if krit else ''}",
                          f"sysid={src}", "T0855 Unauthorized Command Message"))
            elif krit:
                out.append(self._event("KRITIK KOMUT", "ORTA", f"{krit} komutu",
                          f"sysid={src}", "T0855"))
        elif t in RECON_MSGS and src != LEGIT_GCS_SYSID:
            out.append(self._event("KESIF", "ORTA", f"{t} istegi",
                      f"sysid={src}", "T0888 Remote System Information Discovery"))
        return out

    def on_telemetry(self, msg):
        out = []
        f = self._flood_check(msg.get_srcSystem())
        if f:
            out.append(f)
        if msg.get_type() == "GLOBAL_POSITION_INT":
            lat, lon = msg.lat / 1e7, msg.lon / 1e7
            if self.last_pos is not None:
                d = mesafe_m(self.last_pos[0], self.last_pos[1], lat, lon)
                now = time.time()
                if d > self.jump_m and now - self.last_spoof > 1.5:
                    self.last_spoof = now
                    out.append(self._event("GPS SPOOF", "YUKSEK",
                              f"konumda ani {int(d)} m sicrama",
                              f"sysid={msg.get_srcSystem()}",
                              "T0830 Adversary-in-the-Middle / spoofing"))
            self.last_pos = (lat, lon)
        return out


# ----------------------------- Yapay zeka raporu ----------------------------
MUDAHALE = {
    "KOMUT ENJEKSIYONU": "Mesaj imzalamayi (MAVLink 2) etkinlestir; yetkisiz sysid'i "
                         "engelle; komut kaynagini dogrula.",
    "GPS SPOOF": "Konum tutarliligini capraz kontrol et (IMU/bariyer); supheli "
                 "telemetriyi karantinaya al; sinyal kaynagini izle.",
    "FLOOD/DoS": "Kaynak sysid'e hiz sinirlama uygula; beyaz liste disini dusur; "
                 "kanal kapasitesini izle.",
    "KESIF": "Yetkisiz bilgi isteklerini reddet; kaynagi logla ve alarma bagla.",
    "KRITIK KOMUT": "Kritik komutlari ikinci bir dogrulamaya tabi tut.",
    "KOMUT REDDEDILDI": "Saldiri MAVLink imzalama ile engellendi; drone etkilenmedi. "
                        "Kaynagi logla ve engel listesine ekle.",
}


def ai_rapor(olay):
    """Olay icin Turkce rapor. LLM_API_KEY tanimli ise LLM, yoksa sablon."""
    key = os.environ.get("LLM_API_KEY")
    if key:
        try:
            return _llm_rapor(olay, key)
        except Exception:  # LLM hatasinda sablona dus
            pass
    m = MUDAHALE.get(olay["tur"], "Olayi incele ve kaynagi dogrula.")
    return (f"Ne oldu: {olay['tur']} ({olay['siddet']}). {olay['aciklama']}. "
            f"Kaynak {olay['kaynak']}.\n"
            f"ATT&CK: {olay['mitre']}.\n"
            f"Onerilen mudahale: {m}")


def _llm_rapor(olay, key):
    """OpenAI uyumlu bir LLM API'si ile kisa Turkce rapor (opsiyonel).

    Ortam degiskenleri:
      LLM_API_KEY  : API anahtari (zorunlu)
      LLM_API_URL  : chat/completions ucu (varsayilan OpenAI uyumlu)
      LLM_MODEL    : model adi
    """
    import json
    import urllib.request
    url = os.environ.get("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    prompt = (
        "Bir İHA SOC analistisin. Aşağıdaki MAVLink güvenlik olayını Türkçe, "
        "kısa ve madde madde raporla (Ne oldu / Risk / Önerilen müdahale / "
        "MITRE ATT&CK). Olay: " + json.dumps(olay, ensure_ascii=False)
    )
    body = json.dumps({
        "model": model,
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Authorization": f"Bearer {key}",
                 "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]


# ----------------------------- Paylaşılan durum -----------------------------
EVENT_LOG = deque(maxlen=200)
LATEST_TEL = {"lat": None, "lon": None, "alt": None, "mode": None, "armed": None}
RAW_Q = Queue()          # köprü thread'inden -> async yayına
STATS = {"paket": 0, "alarm": 0, "reddedilen": 0}
STATE = {"defense": False}   # savunma (MAVLink imzalama) açık/kapalı


def komut_imzali(msg):
    """MAVLink 2 mesaji imzali mi? (incompat_flags bit0 = imzali)"""
    try:
        return bool(msg.get_header().incompat_flags & 0x01)
    except Exception:
        return False


def bridge_thread(args):
    tele = mavutil.mavlink_connection("udpin:" + args.tele_in, dialect="common")
    cmd = mavutil.mavlink_connection("udpin:" + args.cmd_in, dialect="common")
    ph, pp = args.to_panel.split(":")
    dh, dp = args.to_drone.split(":")
    to_panel = RawSender(ph, pp)
    to_drone = RawSender(dh, dp)
    det = Detector(jump_m=args.jump, flood_per_s=args.flood)
    print(f"[backend] kopru calisiyor: tele {args.tele_in}, cmd {args.cmd_in}")

    def push(mesaj):
        RAW_Q.put(mesaj)

    while True:
        got = False
        m = tele.recv_match(blocking=False)
        if m is not None:
            got = True
            STATS["paket"] += 1
            to_panel.send(m.get_msgbuf())
            if m.get_type() == "GLOBAL_POSITION_INT":
                LATEST_TEL["lat"] = round(m.lat / 1e7, 6)
                LATEST_TEL["lon"] = round(m.lon / 1e7, 6)
                LATEST_TEL["alt"] = round(m.relative_alt / 1000.0, 1)
                push({"tip": "telemetri", "veri": dict(LATEST_TEL)})
            for e in det.on_telemetry(m):
                STATS["alarm"] += 1
                e["ai"] = ai_rapor(e)
                EVENT_LOG.appendleft(e)
                push({"tip": "olay", "veri": e})
        m = cmd.recv_match(blocking=False)
        if m is not None:
            got = True
            STATS["paket"] += 1
            # SAVUNMA: açıkken imzasız komutlar drona iletilmeden reddedilir
            if (STATE["defense"] and m.get_type() == "COMMAND_LONG"
                    and not komut_imzali(m)):
                STATS["reddedilen"] += 1
                e = det._event("KOMUT REDDEDILDI", "ENGELLENDI",
                               "imzasiz komut dusuruldu (drone korundu)",
                               f"sysid={m.get_srcSystem()}",
                               "Savunma: MAVLink 2 mesaj imzalama")
                e["ai"] = ai_rapor(e)
                EVENT_LOG.appendleft(e)
                push({"tip": "olay", "veri": e})
                continue  # drona GÖNDERME
            to_drone.send(m.get_msgbuf())
            for e in det.on_command(m):
                STATS["alarm"] += 1
                e["ai"] = ai_rapor(e)
                EVENT_LOG.appendleft(e)
                push({"tip": "olay", "veri": e})
        if not got:
            time.sleep(0.002)


# ----------------------------- Web / API ------------------------------------
app = FastAPI(title="İHA SOC")
PANEL = Path(__file__).resolve().parent.parent / "panel" / "index.html"
subscribers = set()


@app.get("/")
def index():
    return FileResponse(str(PANEL))


@app.get("/events")
def events():
    return JSONResponse({"stats": STATS, "defense": STATE["defense"],
                         "olaylar": list(EVENT_LOG)[:50]})


@app.post("/defense")
def set_defense(on: bool):
    STATE["defense"] = bool(on)
    return {"defense": STATE["defense"]}


@app.websocket("/ws")
async def ws(ws: WebSocket):
    await ws.accept()
    q = asyncio.Queue()
    subscribers.add(q)
    # anlık durum
    await ws.send_json({"tip": "durum", "veri": dict(LATEST_TEL)})
    for e in list(EVENT_LOG)[:20][::-1]:
        await ws.send_json({"tip": "olay", "veri": e})
    try:
        while True:
            mesaj = await q.get()
            await ws.send_json(mesaj)
    except WebSocketDisconnect:
        pass
    finally:
        subscribers.discard(q)


async def fanout():
    """RAW_Q'dan al, tüm abonelere dağıt."""
    while True:
        try:
            while True:
                mesaj = RAW_Q.get_nowait()
                for q in list(subscribers):
                    q.put_nowait(mesaj)
        except Empty:
            pass
        await asyncio.sleep(0.03)


@app.on_event("startup")
async def startup():
    asyncio.create_task(fanout())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tele-in", default="127.0.0.1:14560")
    ap.add_argument("--cmd-in", default="127.0.0.1:14561")
    ap.add_argument("--to-panel", default="127.0.0.1:14570")
    ap.add_argument("--to-drone", default="127.0.0.1:14571")
    ap.add_argument("--jump", type=float, default=100.0)
    ap.add_argument("--flood", type=int, default=200)
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    t = threading.Thread(target=bridge_thread, args=(args,), daemon=True)
    t.start()
    print(f"[backend] panel: http://localhost:{args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
