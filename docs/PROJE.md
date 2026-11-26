# İHA Haberleşme Güvenliği + Yapay Zeka Destekli SOC

**Ders:** Siber Güvenlik Çözümleri ve Uygulamaları — Dr. Süleyman M. Arıkan, 2026 Güz
**Teslim:** ~17 Aralık 2026 (3 hafta) · **Şart:** sunumda canlı çalışan demo

---

## 1. Amaç ve tek cümlelik özet

Simüle bir İHA'nın yer istasyonuyla konuştuğu MAVLink haberleşmesine yapılan gerçek saldırıları (sahte komut, kaçırma, telemetri sahteciliği, mesajla boğma) sahneye koyan; bu saldırıları kural + makine öğrenmesiyle tespit edip bir SOC paneline düşüren; olayları bir LLM ile Türkçe özetleyip müdahale öneren; ve MAVLink 2 mesaj imzalama ile saldırıyı fiilen engelleyen uçtan uca bir sistem. Tek dizüstünde, donanımsız, Docker ile çalışır.

## 2. Hikâye (demoyu da bu anlatır)

1. **Normal:** Simüle drone bir görev rotasında uçar; panelde telemetri (konum, irtifa, mod, batarya) akar, her şey yeşil.
2. **Saldırı:** Saldırgan makineden sahte "iniş yap" (veya "disarm") komutu enjekte edilir. Drone itaat eder, inmeye başlar. Panelde kırmızı alarm düşer.
3. **Tespit + AI:** SOC kuralı ve ML modeli olayı "yetkisiz komut enjeksiyonu" olarak işaretler; LLM olayı "ne oldu, nasıl, ne yapmalı" diye Türkçe özetler, MITRE ATT&CK tekniğine eşler.
4. **Savunma:** MAVLink 2 mesaj imzalama açılır. Aynı saldırı tekrarlanır; imzasız paket reddedilir, drone görevine devam eder. Panelde "reddedilen sahte komut" olarak loglanır.
5. **Kapanış:** Panelde saldırı öncesi/sonrası metrikler, tespit süresi, rapor PDF'i.

## 3. Mimari

```
[ArduPilot SITL]  --MAVLink/UDP-->  [Köprü/Proxy]  -->  [QGroundControl / Panel]
     (drone)                              |  (tüm paketleri aynalar)
                                          v
                              [Tespit Motoru: kural + ML]
                                          |  olaylar
                                          v
                        [Olay Deposu] --> [FastAPI backend] --> [React SOC Paneli]
                                                 |
                                                 v
                                        [LLM Raporlama Servisi]
[Saldırgan betikleri] --MAVLink enjeksiyon--> Köprü
```

**Bileşenler**
- **SITL (ArduPilot):** gerçek uçuş kontrol yazılımının yazılım simülasyonu; gerçek MAVLink üretir.
- **Köprü/proxy (Python, pymavlink):** SITL ile yer istasyonu arasında oturur, tüm trafiği aynalayıp tespit motoruna besler; imzalama savunması burada uygulanır.
- **Saldırgan betikleri:** pymavlink/Scapy ile komut enjeksiyonu, telemetri sahteciliği, flood, keşif.
- **Tespit motoru:** (a) kural tabanlı (imzasız komut, beklenmeyen mod değişimi, komut hız eşiği, kaynak IP uyumsuzluğu), (b) ML — normal telemetriden sapma (IsolationForest/one-class) + komut sınıflama.
- **Backend (FastAPI):** olayları toplar, WebSocket ile panele canlı yayınlar, LLM servisini çağırır.
- **SOC paneli (React):** canlı telemetri, olay akışı, ATT&CK haritası, AI rapor kartı, saldırı/savunma anahtarları.
- **LLM raporlama:** olay verisini alır, Türkçe özet + müdahale adımı üretir (API; anahtar yoksa şablon tabanlı yedek).

## 4. Saldırı senaryoları

| # | Saldırı | Teknik | Beklenen etki |
|---|---------|--------|----------------|
| 1 | Yetkisiz komut enjeksiyonu | sahte COMMAND_LONG (LAND/DISARM/RTL) | drone kaçırılır |
| 2 | Telemetri sahteciliği (GPS spoof) | sahte GLOBAL_POSITION_INT | yanlış konum |
| 3 | Mesajla boğma (flood/DoS) | yüksek hızlı HEARTBEAT/param | gecikme, kopma |
| 4 | Oturum/keşif | param okuma, stream talebi | ağ haritalama |

## 5. Tespit ve savunma

- **Kural tabanlı:** imzasız veya bilinmeyen `sysid/compid`, kritik komut, anormal mesaj hızı, mod/konum sıçraması.
- **ML:** normal uçuştan telemetri öznitelikleri (hız, irtifa değişimi, mesaj aralığı) ile anomali skoru; etiketli saldırı verisiyle basit sınıflandırıcı.
- **Savunma:** MAVLink 2 HMAC mesaj imzalama (paylaşılan anahtar); köprü imzasız/yanlış imzalı komutu düşürür. Ek: komut hız sınırlama, kaynak beyaz liste.

## 6. Ders konuları ve BG Rehberi eşlemesi

| Proje parçası | Ders konusu |
|---|---|
| Saldırı betikleri | Ofansif Güvenlik Uygulamaları (Hafta 10) |
| Tespit + panel | Defansif Uygulamalar (Hafta 11), Ağ Güvenliği |
| İHA/köprü | Mobil ve IoT Güvenliği |
| LLM raporlama | Yapay Zeka ve Siber Güvenlik (Hafta 13) |
| Olay akışı + müdahale | Operasyonlar ve Olay Müdahale, Adli Bilişim |
| Güvenli panel (OWASP) | Uygulama Güvenliği, Güvenli Yazılım (OWASP Top 10) |

**BG Rehberi:** rapora alınan tedbirler (ağ erişim kontrolü, kriptografik koruma, loglama/izleme, olay yönetimi) rehber maddelerine atıfla eşlenecek — hocanın derste işlediği ulusal çerçeveye bağlanır.

## 7. Teknoloji yığını

ArduPilot SITL, QGroundControl, Python (pymavlink, Scapy, scikit-learn, FastAPI, WebSocket), React + Vite, bir LLM API'si (şablon yedekli), Docker + docker-compose. Tümü ücretsiz/açık kaynak, tek makinede.

## 8. 3 haftalık ayrıntılı plan

**Hafta 1 — Temel + saldırılar**
- Depo iskeleti, docker-compose, SITL ve QGroundControl kurulumu, bağlantı doğrulama.
- pymavlink köprüsü (trafiği aynalama, loglama).
- Saldırı betikleri 1–4; her biri için "çalışıyor" kaydı.
- Çıktı: saldırı drone'u gözle görülür etkiliyor.

**Hafta 2 — Tespit + panel + AI**
- Kural motoru + ML (normal veri toplama, eğitim, skor).
- FastAPI backend + WebSocket olay yayını.
- React SOC paneli: telemetri, olay akışı, ATT&CK haritası, AI rapor kartı.
- LLM raporlama servisi (+ şablon yedek).
- Çıktı: saldırı → panelde alarm + AI özeti.

**Hafta 3 — Savunma + cila + sunum**
- MAVLink 2 imzalama savunması; saldırı reddedilişi.
- Demo akışı senaryosu, metrikler, PDF rapor üretimi.
- OWASP/BG Rehberi eşleme raporu, README, sunum provası.
- Çıktı: baştan sona canlı demo + teslim paketi.

## 9. Riskler ve önlemler

- SITL/QGC kurulum zorluğu → Docker imajı + net README; gerekirse jMAVSim/headless.
- LLM anahtarı yoksa → şablon tabanlı rapor yedeği (demo her hâlükârda çalışır).
- Zaman → her hafta sonunda çalışan bir dilim; panel ve saldırı önce, ML/AI sonra.

---

*Sonraki adım: depo iskeleti ve Hafta 1.*
