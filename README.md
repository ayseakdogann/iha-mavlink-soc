# İHA Haberleşme Güvenliği ve Yapay Zeka Destekli SOC

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![MAVLink](https://img.shields.io/badge/Protocol-MAVLink%202-FF6F00)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)
![MITRE ATT&CK](https://img.shields.io/badge/Mapping-MITRE%20ATT%26CK%20for%20ICS-C7222A)
![Lisans](https://img.shields.io/badge/Lisans-MIT-informational)

Simüle bir İHA'nın **MAVLink** haberleşmesine yapılan saldırıları gerçekleştiren,
canlı tespit eden, bir **SOC panelinde** gösteren, **MITRE ATT&CK for ICS** ile
eşleyen, yapay zeka ile raporlayan ve **MAVLink 2 mesaj imzalama** ile savunan
uçtan uca bir güvenlik demosu. Tamamı tek dizüstünde, ek donanım gerekmeden
çalışır.

> Eğitim ve savunma (defansif) güvenlik amaçlıdır. Saldırı betikleri yalnızca
> `127.0.0.1` üzerindeki yerel simülatöre yöneliktir.

---

## Öne çıkanlar

- **Ofansif:** 4 farklı saldırı — komut enjeksiyonu (kaçırma), GPS spoof, keşif, flood/DoS.
- **Defansif:** Kural tabanlı canlı tespit + MAVLink 2 imzalama (HMAC-SHA256) ile önleme.
- **SOC paneli:** Tarayıcıda canlı telemetri, olay akışı, şiddet seviyeleri ve MITRE etiketleri (WebSocket).
- **Yapay zeka:** Her olay için Türkçe müdahale raporu (sağlayıcı-bağımsız; anahtar yoksa şablon moduna düşer).
- **Çerçeve eşlemesi:** Her saldırı/savunma MITRE ATT&CK for ICS, ders konuları ve BG Rehberi tedbirleriyle eşlenir.

---

## Mimari

```
  Drone (simülatör) ──MAVLink──►  Köprü / SOC  ──MAVLink──►  Operatör (GCS)
   sim/drone_sim.py              backend/app.py              tools/gcs_signed.py
                                      │
                                      ├─ kural tabanlı tespit
                                      ├─ MAVLink 2 imzalama (savunma)
                                      ├─ yapay zeka olay raporu
                                      └─ WebSocket ──► panel/index.html (tarayıcı)

  Saldırganlar:  attacks/inject_land.py · spoof_gps.py · recon.py · flood.py
```

Ortadaki köprü hem telemetriyi hem komutları görür; savunma açıkken imzasız
komutları drona iletmeden reddeder, imzalı meşru komutları geçirir.

---

## Dizin yapısı

```
sim/       drone_sim.py     – gerçek MAVLink konuşan hafif drone simülatörü
attacks/   inject_land.py   – komut enjeksiyonu (T0855)
           spoof_gps.py     – GPS/konum sahteciliği (T0830)
           recon.py         – keşif / bilgi toplama (T0888)
           flood.py         – flood / DoS (T0814)
backend/   app.py           – FastAPI + WebSocket SOC servisi (tespit + imzalama + YZ rapor)
panel/     index.html       – canlı SOC paneli (tarayıcı)
tools/     gcs_signed.py    – imzalı komut gönderen meşru operatör
           monitor.py       – bağımsız telemetri/anomali konsolu
bridge/    bridge.py        – konsol tabanlı köprü (bağımsız çalıştırma seçeneği)
docs/      PROJE.md · UYGULAMA.md · DEMO.md · ESLEME.md · SORULAR.md · WINDOWS-KURULUM.md
```

---

## Kurulum

```bash
# Sanal ortam
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

Windows için ayrıntılı adımlar: [docs/WINDOWS-KURULUM.md](docs/WINDOWS-KURULUM.md).

---

## Çalıştırma

4 terminal (hepsinde sanal ortam aktif):

```bash
# T1 — Backend + SOC paneli  →  http://localhost:8000
python backend/app.py

# T2 — Drone simülatörü
python sim/drone_sim.py --out 127.0.0.1:14560 --in 127.0.0.1:14571

# T3 — Saldırı (örnek: komut enjeksiyonu)
python attacks/inject_land.py --target 127.0.0.1:14561 --cmd LAND

# T4 — Meşru operatör (imzalı komut)
python tools/gcs_signed.py --target 127.0.0.1:14561 --cmd RTL
```

Tarayıcıda **http://localhost:8000** açık olsun. Panelin sağ üstündeki
**Savunma (imzalama)** düğmesi ile imzalama önlemini canlı aç/kapat.

Adım adım sunum senaryosu: [docs/DEMO.md](docs/DEMO.md).

---

## Saldırı ↔ savunma ↔ MITRE eşlemesi

| Saldırı | Betik | MITRE ATT&CK (ICS) | Hedef ilke | Savunma |
|---|---|---|---|---|
| Komut enjeksiyonu | `inject_land.py` | T0855 Unauthorized Command Message | Bütünlük | MAVLink 2 imzalama |
| GPS spoof | `spoof_gps.py` | T0830 Adversary-in-the-Middle | Bütünlük | Girdi/sensör doğrulama |
| Keşif | `recon.py` | T0888 Remote System Information Discovery | Gizlilik | En az yetki |
| Flood / DoS | `flood.py` | T0814 Denial of Service | Erişilebilirlik | Hız sınırlama / anomali |

Tam eşleme (ders konuları + BG Rehberi tedbir alanları ile):
[docs/ESLEME.md](docs/ESLEME.md).

---

## Savunma: MAVLink 2 mesaj imzalama

Savunma açıkken köprü, imzasız `COMMAND_LONG` mesajlarını drona iletmeden
reddeder (**KOMUT REDDEDİLDİ**). Meşru operatör paylaşılan anahtarla imzaladığı
için (HMAC-SHA256) komutu kabul edilir. Böylece savunma her komutu değil,
yalnızca sahte/imzasız olanı engeller — komut enjeksiyonunun (T0855) kök çözümü.

---

## Yapay zeka olay raporu

Her alarm için **ne oldu / etki / MITRE tekniği / müdahale önerisi** biçiminde
Türkçe bir rapor üretilir. LLM sağlayıcısı ortam değişkenleriyle yapılandırılır;
anahtar tanımlı değilse sistem şablon tabanlı rapora düşer, böylece demo
internetsiz de çalışır.

```bash
# Opsiyonel: OpenAI-uyumlu bir sağlayıcı
export LLM_API_KEY=...            # Windows: setx LLM_API_KEY ...
export LLM_API_URL=...            # varsayılan: OpenAI uyumlu uç nokta
export LLM_MODEL=...              # örn. gpt-4o-mini
```

---

## Dokümanlar

- [docs/PROJE.md](docs/PROJE.md) — proje tanımı ve kapsam
- [docs/UYGULAMA.md](docs/UYGULAMA.md) — teknik uygulama ayrıntıları
- [docs/DEMO.md](docs/DEMO.md) — canlı sunum senaryosu
- [docs/ESLEME.md](docs/ESLEME.md) — MITRE + ders + BG Rehberi eşlemesi
- [docs/SORULAR.md](docs/SORULAR.md) — çoktan seçmeli sınav soruları
- [docs/WINDOWS-KURULUM.md](docs/WINDOWS-KURULUM.md) — Windows kurulum rehberi

---

## Lisans

MIT. Eğitim ve araştırma amaçlıdır; yalnızca kendi kontrolünüzdeki sistemlerde
kullanın.
