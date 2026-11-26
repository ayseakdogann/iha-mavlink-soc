# Eşleme: Saldırı/Savunma ↔ MITRE ATT&CK ↔ Ders Konuları ↔ BG Rehberi

Bu belge, projedeki her saldırı ve savunma bileşenini üç çerçeveye bağlar:
MITRE ATT&CK for ICS, dersin konu başlıkları ve Bilgi Güvenliği (BG) Rehberi
tedbir alanları. Amaç: demonun yalnızca bir gösteri değil, derste işlenen
konuların ve kabul görmüş çerçevelerin somut bir uygulaması olduğunu göstermek.

## 1. Tehdit modeli (özet)

Sistem: Bir İHA (drone) ile yer kontrol istasyonu (GCS) arasında **MAVLink 2**
protokolüyle UDP üzerinden haberleşme. Ortadaki **köprü/SOC**, tüm trafiği izler,
anormallikleri tespit eder ve (savunma açıkken) imzasız komutları reddeder.

Varsayılan saldırgan yeteneği: Ağa erişebilen, paket enjekte edebilen (aynı
L2/L3 segmentinde veya ele geçirilmiş bir ara düğümde) bir aktör. Kimlik
doğrulama/imzalama yoksa, protokolün hiçbir yerinde "bu komutu kim gönderdi?"
sorusunun cevabı yoktur — projenin çözdüğü temel boşluk budur.

## 2. Ana eşleme tablosu

| # | Bileşen | Tür | Kaynak (sysid) | MITRE ATT&CK (ICS) | Ders konusu | BG Rehberi tedbir alanı |
|---|---------|-----|----------------|--------------------|-------------|--------------------------|
| S1 | `inject_land.py` | Komut enjeksiyonu / kaçırma | 255 (yetkisiz) | **T0855** Unauthorized Command Message | Ofansif güvenlik; Ağ güvenliği | Kimlik doğrulama ve yetkilendirme; mesaj bütünlüğü (kriptografi) |
| S2 | `spoof_gps.py` | Konum/sensör sahteciliği | 1 (taklit) | **T0830** Adversary-in-the-Middle / spoofing | Ağ güvenliği; Çevrebirim güvenliği | Veri bütünlüğü; sensör/girdi doğrulama |
| S3 | `recon.py` | Keşif / bilgi toplama | 255 | **T0888** Remote System Information Discovery | Ofansif güvenlik; Operasyon/izleme | Saldırı yüzeyinin azaltılması; en az yetki |
| S4 | `flood.py` | Hizmet dışı bırakma (DoS) | 255 | **T0814** Denial of Service | Ağ güvenliği; Operasyon | Erişilebilirlik; hız sınırlama / anomali tespiti |
| D1 | Köprü tespit motoru (`Detector`) | Tespit / izleme | — | Tespit kontrolü (ATT&CK tekniklerinin tespiti) | Defansif güvenlik; Operasyon ve olay müdahale | Günlükleme ve izleme (SOC); saldırı tespiti |
| D2 | MAVLink 2 mesaj imzalama (`/defense`) | Önleme / kimlik doğrulama | Operatör: 254 (imzalı) | T0855'in önlenmesi (imzasız komutun reddi) | Defansif güvenlik; Uygulama güvenliği; Mimari | Kriptografik kimlik doğrulama (HMAC-SHA256); anahtar yönetimi |
| D3 | YZ olay raporu + ATT&CK etiketi | Müdahale / raporlama | — | Olay müdahale otomasyonu | Operasyon ve olay müdahale | Olay kayıt ve raporlama; müdahale süreçleri |

## 3. Detaylı açıklamalar

### S1 — Komut enjeksiyonu (T0855)
Saldırgan, yetkisiz bir `sysid` (255) ile sahte bir `COMMAND_LONG` (ör. `NAV_LAND`)
gönderir. İmzalama yokken drone bunu kabul eder → kaçırma/düşürme. **Tespit:**
köprü, bilinen/yetkili olmayan kaynaktan gelen kritik komutu "KOMUT ENJEKSIYONU
(KRİTİK)" olarak işaretler ve T0855 ile etiketler.
**Ders bağı:** Ofansif güvenlik haftasının birebir uygulaması; ağ katmanında
kimlik doğrulamanın yokluğunun sonucu.

### S2 — GPS/konum sahteciliği (T0830)
Saldırgan sahte `GLOBAL_POSITION_INT` mesajları (2 km kayma) enjekte eder.
**Tespit:** konumda fiziksel olarak imkânsız sıçrama → "GPS SPOOF". Panelde drone
noktası kırmızıya döner. **BG bağı:** sensör girdilerinin doğrulanması ve veri
bütünlüğü; çevrebirim güvenliği.

### S3 — Keşif (T0888)
`PARAM_REQUEST_LIST`, `MISSION_REQUEST_LIST`, `REQUEST_DATA_STREAM` gibi bilgi
toplama istekleri. **Tespit:** "KEŞİF" olarak işaretlenir. Gerçek bir saldırının
hazırlık aşamasını temsil eder; en az yetki ve saldırı yüzeyi azaltımı ile
ilişkilidir.

### S4 — Flood / DoS (T0814)
Yüksek hızda `HEARTBEAT` seli ile hattı ve işlemeyi boğma. **Tespit:** mesaj hızı
eşiği (200/s) aşılınca "FLOOD/DoS (YÜKSEK)". **BG bağı:** erişilebilirlik ve hız
sınırlama tedbirleri.

### D1/D2/D3 — Savunma katmanı
- **Tespit (D1):** kural tabanlı SOC; her olay ATT&CK tekniğiyle etiketlenir.
- **Önleme (D2):** MAVLink 2 imzalama açıkken imzasız komutlar drona iletilmeden
  reddedilir ("KOMUT REDDEDİLDİ"). Meşru operatör paylaşılan anahtarla imzaladığı
  için (sysid 254) komutu kabul edilir. HMAC-SHA256 → mesaj bütünlüğü + kaynak
  kimliği. **Bu, savunmanın her komutu değil yalnızca sahte/imzasız olanı
  engellediğini kanıtlar.**
- **Müdahale (D3):** Her olay için Türkçe YZ raporu (ne oldu, etki, öneri) üretilir.

## 4. Katmanlı savunma (defense-in-depth) görünümü

```
Ağ/Çevrebirim  ──► Sensör/girdi doğrulama (S2'ye karşı)
Kimlik/Kripto  ──► MAVLink 2 imzalama (S1'e karşı, D2)
Operasyon/SOC  ──► Tespit + loglama + anomali (S3, S4, D1)
Olay müdahale  ──► YZ raporlama + ATT&CK eşleme (D3)
```

## 5. Çerçeve notları
- **MITRE ATT&CK for ICS:** Endüstriyel/siber-fiziksel sistemlere özgü teknik
  kataloğu; İHA gibi siber-fiziksel bir sistem için uygun çerçeve.
- **BG Rehberi:** Bilgi güvenliği tedbirleri; burada kimlik doğrulama, kriptografi,
  bütünlük, erişilebilirlik, günlükleme/izleme ve olay müdahale alanlarıyla
  eşleşir.
- Demonun akışı için bkz. [DEMO.md](DEMO.md).
