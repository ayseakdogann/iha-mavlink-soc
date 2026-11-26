# İHA Haberleşme Güvenliği + Yapay Zeka Destekli SOC

Simüle bir İHA'nın MAVLink haberleşmesine yapılan saldırıları gerçekleştiren,
tespit eden, bir SOC panelinde gösteren, yapay zeka ile raporlayan ve mesaj
imzalama ile savunan uçtan uca demo. Ders projesi — Siber Güvenlik Çözümleri ve
Uygulamaları, 2026 Güz.

## Dizin yapısı
```
sim/       drone_sim.py    – gerçek MAVLink konuşan hafif drone simülatörü
attacks/   saldırı betikleri (komut enjeksiyonu, spoof, flood, keşif)
bridge/    drone <-> yer istasyonu arası köprü + imzalama savunması (Hafta 2-3)
detect/    kural + makine öğrenmesi tespit motoru (Hafta 2)
backend/   FastAPI + WebSocket olay servisi (Hafta 2)
panel/     React SOC paneli (Hafta 2)
docs/      rapor, ders/BG Rehberi eşlemesi
```

## Kurulum
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Hızlı deneme (şu an çalışan parça)
İki terminalde:
```bash
# 1) drone simülatörü
python3 sim/drone_sim.py --out 127.0.0.1:14560 --in 127.0.0.1:14561

# 2) saldırı: sahte 'iniş' komutu enjekte et
python3 attacks/inject_land.py --target 127.0.0.1:14561 --cmd LAND
```
Simülatör logunda `komut -> mod=LAND` görülür: imzalama yokken drone sahte komutu
kabul eder (kaçırma senaryosu). Savunma (Hafta 3) açıldığında bu komut reddedilir.

## Durum
- [x] Drone simülatörü (telemetri + komut tepkisi)
- [x] Saldırı #1: yetkisiz komut enjeksiyonu
- [ ] Saldırı #2-4: spoof, flood, keşif
- [ ] Köprü + tespit motoru
- [ ] SOC paneli + yapay zeka raporlama
- [ ] Mesaj imzalama savunması
