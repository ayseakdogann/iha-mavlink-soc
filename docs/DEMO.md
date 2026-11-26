# Sunum Demo Akışı

Hocaya canlı gösterim için adım adım senaryo. ~4-5 dakika. 4 terminal + tarayıcı.

## Hazırlık
Proje klasöründe (.venv) aktif, paketler kurulu. 4 PowerShell penceresi aç;
hepsinde: cd ...\iha-soc\iha-soc  ve  .venv\Scripts\Activate.ps1

| Terminal | Komut |
|---|---|
| T1 Backend/SOC | python backend\app.py |
| T2 Drone | python sim\drone_sim.py --out 127.0.0.1:14560 --in 127.0.0.1:14571 |
| T3 Saldırgan | (komutları buraya) |
| T4 Operatör | (imzalı komut) |

Tarayıcı: http://localhost:8000 (projeksiyonda açık).

## Akış

1) NORMAL (30 sn): Panelde telemetri akar, nokta hareket eder. "Bu bir İHA'nın
   MAVLink haberleşmesi; ortadaki köprü tüm trafiği izleyip SOC paneline işliyor."

2) KOMUT ENJEKSİYONU (60 sn) — T3:
   python attacks\inject_land.py --target 127.0.0.1:14561 --cmd LAND
   Panelde KRITIK alarm, T2'de mod=LAND. "Sahte iniş komutu, imzalama yokken
   kabul edildi — drone kaçırıldı. SOC T0855 olarak yakaladı, AI müdahale önerdi."

3) SPOOF / KEŞİF / FLOOD (60 sn) — T3:
   python attacks\spoof_gps.py --target 127.0.0.1:14560 --offset-km 2
   python attacks\recon.py --target 127.0.0.1:14561
   python attacks\flood.py --target 127.0.0.1:14561 --rate 2000 --duration 5
   Panelde sırasıyla GPS SPOOF (nokta kırmızı), KEŞİF, FLOOD alarmları; MITRE etiketli.

4) SAVUNMA (90 sn, final): Panelde "Savunma (imzalama)" düğmesine bas -> AÇIK.
   T3 aynı saldırı:
   python attacks\inject_land.py --target 127.0.0.1:14561 --cmd LAND
   Panelde yeşil KOMUT REDDEDILDI; T2'de mod=LAND GELMEZ (drone korunur).
   Sonra meşru operatör (T4):
   python tools\gcs_signed.py --target 127.0.0.1:14561 --cmd RTL
   Bu KABUL edilir (mod=RTL). "Savunma her komutu engellemiyor; yalnızca
   imzasız/sahte olanı reddediyor. İmzalı komut geçiyor."

5) KAPANIŞ (30 sn): Özet sayaçları (paket/alarm/reddedilen). Ofansif + Defansif
   + Yapay zeka + MITRE ATT&CK. Ders konuları ve BG Rehberi ile bağ (ESLEME.md).

## Olası sorular
- "Gerçek drone mu?" -> Hayır, gerçek MAVLink konuşan simülatör; aynı protokol,
  gerçek donanıma da uygulanabilir (SITL/ArduPilot veya Pixhawk).
- "İmzalama nasıl?" -> MAVLink 2 mesaj imzalama; köprü imzasız komutu reddediyor.