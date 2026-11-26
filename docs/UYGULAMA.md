# Uygulama Rehberi — Adım Adım Nasıl Gerçekleştirilir

Bu belge, projeyi **VS Code üzerinde kendiniz** (veya yapay zeka asistanıyla)
baştan sona nasıl tamamlayacağınızı anlatır. Her adımda: ne yapılacak, hangi
dosya, nasıl test edilir. Sıra önemlidir — her adım bir öncekinin üstüne biner
ve her hafta sonunda **çalışan bir demo** elde edersiniz.

> Proje tanımı ve mimari için `PROJE.md`'ye bakın. Hızlı başlangıç için ana
> dizindeki `README.md`'ye bakın.

---

## 0. Kurulum (bir kez)

VS Code'da `iha-soc` klasörünü açın (**File → Open Folder**). Entegre terminalde
(**Ctrl+`**):

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

VS Code sağ altta "venv'i seçmek ister misiniz?" derse **Evet**. Python
eklentisini kurun (Microsoft). Birden çok süreç çalıştıracağınız için birden çok
terminal açmayı öğrenin (terminal panelinde **+**).

**Doğrulama:** `python sim/drone_sim.py` çalışır ve `[sim] drone başladı` yazar.
Ctrl+C ile durdurun.

---

## 1. HAFTA — Temel + saldırılar

### Adım 1.1 — Simülatörü anla (hazır)
`sim/drone_sim.py` zaten çalışıyor. Okuyun: drone ARM olur, AUTO modda tırmanır,
her döngüde telemetri (`GLOBAL_POSITION_INT`, `HEARTBEAT`, `SYS_STATUS`) gönderir
ve gelen `COMMAND_LONG` komutlarına tepki verir.
- **Dene:** Terminal 1'de `python sim/drone_sim.py`. Terminal 2'de konumu dinle:
  ```powershell
  python -c "from pymavlink import mavutil; m=mavutil.mavlink_connection('udpin:127.0.0.1:14560'); [print(round(m.recv_match(type='GLOBAL_POSITION_INT',blocking=True).alt/1000,1),'m') for _ in range(5)]"
  ```
  İrtifanın arttığını görmelisiniz.

### Adım 1.2 — Saldırı #1: Komut enjeksiyonu (hazır)
`attacks/inject_land.py` hazır. Sahte GCS (sysid 255) olarak LAND/DISARM/RTL
gönderir.
- **Dene:** Sim açıkken `python attacks/inject_land.py --target 127.0.0.1:14561 --cmd LAND`.
  Sim logunda `komut -> mod=LAND` görünür, drone iner. **Kaçırma başarılı.**

### Adım 1.3 — Saldırı #2: GPS/telemetri sahteciliği (YAZILACAK)
Yeni dosya: `attacks/spoof_gps.py`.
- **Ne yapmalı:** `GLOBAL_POSITION_INT` mesajını sahte lat/lon/alt ile yüksek
  hızda (örn. 20 Hz) sim'in telemetri portuna değil, **yer istasyonu/panelin
  dinlediği yöne** basın. Amaç: panelde dronu yanlış konumda göstermek.
- **İpucu:** `mavutil.mavlink_connection("udpout:...")`, sonra döngüde
  `conn.mav.global_position_int_send(...)`. Gerçek konumdan sapan bir "atlama"
  üretin (ör. aniden 2 km kayma) — tespiti kolay olsun.
- **Test:** Panel/dinleyicide konumun zıpladığını görün.

### Adım 1.4 — Saldırı #3: Flood / DoS (YAZILACAK)
Yeni dosya: `attacks/flood.py`.
- **Ne yapmalı:** Çok yüksek hızda (örn. saniyede binlerce) `HEARTBEAT` veya
  `PARAM_REQUEST_LIST` gönderin. Amaç: haberleşmeyi boğmak, gecikme yaratmak.
- **İpucu:** `while True: conn.mav.heartbeat_send(...)` — uyku koymayın ama
  `--rate` ile sınırlanabilir yapın ki demo kontrollü olsun.
- **Test:** Tespit motoru (Hafta 2) mesaj hızında ani artışı yakalayacak.

### Adım 1.5 — Saldırı #4: Keşif (YAZILACAK)
Yeni dosya: `attacks/recon.py`.
- **Ne yapmalı:** `PARAM_REQUEST_LIST`, `MISSION_REQUEST_LIST`,
  `REQUEST_DATA_STREAM` göndererek dronedan bilgi çekmeye çalışın (ağ haritalama
  benzeri).
- **Test:** Logda hangi parametrelerin/yanıtların döndüğünü görün.

**Hafta 1 çıktısı:** 4 saldırı betiği, her biri dronu gözle görülür etkiliyor.

---

## 2. HAFTA — Köprü + tespit + panel + yapay zeka

### Adım 2.1 — Köprü (proxy) — `bridge/bridge.py` (YAZILACAK)
Drone ile yer istasyonu arasında oturur, **tüm paketleri aynalar** ve tespit
motoruna besler. Mimari: iki UDP bağlantısı (drone tarafı, GCS tarafı); gelen her
paketi diğer tarafa ilet + bir `on_message(msg, yon)` çağır.
- **İpucu:** `mavutil.mavlink_connection` ile iki uç; `recv_match(blocking=False)`
  ile her ikisini de dönüşümlü oku, karşıya `write()` ile yaz.
- **Neden önemli:** Hem tespit hem de Hafta 3'teki imzalama savunması burada olur.
- **Test:** Köprü araya girince sim ↔ dinleyici hâlâ çalışır; köprü logu paket
  sayar.

### Adım 2.2 — Kural tabanlı tespit — `detect/rules.py` (YAZILACAK)
Köprüden gelen her mesaja bakıp olay üretir. Kurallar:
1. Komut geldi ama **imza yok/yanlış** → "imzasız komut".
2. Kaynak `sysid` beklenmeyen (ör. 255, beyaz listede değil) → "sahte GCS".
3. Kritik komut (LAND/DISARM/RTL) → her zaman incele.
4. Mesaj hızı eşiği aştı (flood) → "DoS".
5. Konum/mod ani sıçrama → "spoof/anomali".
- **Çıktı:** `{"zaman","tur","aciklama","siddet","kaynak","attack_id","mitre"}`
  biçiminde olay sözlüğü. MITRE eşlemesi: enjeksiyon→T0855 benzeri ICS teknikleri
  veya genel T1565 (Data Manipulation).
- **Test:** Saldırı betiklerini çalıştırın, her biri için doğru olay düşsün.

### Adım 2.3 — ML tespit — `detect/ml.py` (YAZILACAK)
Normal telemetriden sapmayı yakalar (kuralların kaçırdığı ince anomaliler).
- **Adımlar:** (a) Sim'i saldırısız çalıştırıp telemetri öznitelikleri topla
  (irtifa değişimi, hız, mesaj aralığı) → `normal.csv`. (b) `IsolationForest`
  (scikit-learn) eğit. (c) Canlıda her pencere için anomali skoru üret; eşik
  üstü → olay.
- **Test:** Normalde düşük skor; spoof/flood sırasında skor fırlar.

### Adım 2.4 — Backend — `backend/app.py` (YAZILACAK)
FastAPI + WebSocket. Köprü/tespitten gelen olayları toplar, panele canlı yayınlar,
yapay zeka servisini çağırır.
- **Uçlar:** `GET /events` (geçmiş), `WS /ws` (canlı olay akışı),
  `POST /report` (bir olay için AI raporu üret).
- **İpucu:** Tespit motorunu backend içinden bir thread'de çalıştırın ya da olayları
  bir kuyruğa yazın; WebSocket ile push edin.
- **Test:** `uvicorn backend.app:app --reload`, tarayıcıdan `/docs` açılır.

### Adım 2.5 — SOC Paneli — `panel/` (YAZILACAK, React + Vite)
- **Kur:** `npm create vite@latest panel -- --template react`, sonra `npm install`.
- **Ekranlar:** (1) canlı telemetri + mini harita/konum, (2) olay akışı tablosu
  (renk kodlu şiddet), (3) MITRE ATT&CK kutuları, (4) seçili olay için **AI rapor
  kartı**, (5) Saldırı başlat / Savunma aç anahtarları.
- **Bağlantı:** WebSocket ile `/ws`'e bağlan, olay geldikçe listeye ekle.
- **Güvenli yazılım (OWASP):** girdi doğrulama, XSS'e karşı çıktı kaçışı, CORS'u
  yalnız panele aç — raporda OWASP Top 10 eşlemesi yazın.
- **Test:** Saldırı betiği → panelde anında kırmızı olay.

### Adım 2.6 — Yapay zeka raporlama — `backend/ai.py` (YAZILACAK)
Olay verisini alıp **Türkçe** özet + müdahale adımı üretir.
- **Girdi→Çıktı:** olay sözlüğü → "Ne oldu / Nasıl / Risk / Önerilen müdahale /
  ATT&CK" başlıklı kısa rapor.
- **Uygulama:** Bir LLM API'si (Anthropic/OpenAI). **Anahtar yoksa** şablon
  tabanlı yedek fonksiyon yazın ki demo internetsiz de çalışsın.
- **Test:** Enjeksiyon olayı için mantıklı Türkçe rapor döner.

**Hafta 2 çıktısı:** Saldırı → panelde alarm + yapay zeka özeti.

---

## 3. HAFTA — Savunma + cila + sunum

### Adım 3.1 — MAVLink imzalama savunması — `bridge/signing.py` (YAZILACAK)
MAVLink 2 HMAC mesaj imzalama. Paylaşılan anahtarla imzalı olmayan/komut
mesajlarını köprü **reddeder**.
- **İpucu:** pymavlink `setup_signing(secret_key)` destekler; köprüde gelen
  komutun imzasını doğrula, geçersizse düşür + olay üret ("sahte komut reddedildi").
- **Ek savunma:** komut hız sınırı, kaynak beyaz liste.
- **Test:** Savunma açıkken `inject_land.py` çalıştırın → drone **inmez**, panelde
  "reddedildi" olayı.

### Adım 3.2 — Demo akışı ve metrikler
`docs/DEMO.md` yazın: sunumdaki tam adım sırası (normal → saldırı → tespit+AI →
savunma → tekrar saldırı reddi). Panelde tespit süresi, saldırı sayısı gibi
metrikleri gösterin. İsteğe bağlı: olaylardan PDF rapor üretimi.

### Adım 3.3 — Ders + BG Rehberi eşlemesi — `docs/ESLEME.md`
Her proje parçasını ders konusuna ve Bilgi ve İletişim Güvenliği Rehberi
maddelerine bağlayın (ağ erişim kontrolü, kriptografik koruma, loglama/izleme,
olay yönetimi). Bu, sunumu hocanın ders çerçevesine oturtur.

### Adım 3.4 — Paketleme ve sunum provası
`README`'yi güncelleyin, `docker-compose.yml` ile tek komutla ayağa kaldırmayı
ekleyin (opsiyonel), sunumu baştan sona 2 kez prova edin.

**Hafta 3 çıktısı:** Baştan sona canlı demo + teslim paketi.

---

## Çalıştırma portları (özet)
| Bileşen | Port | Yön |
|---|---|---|
| Drone → bridge (telemetri) | 14560 | udpout→udpin |
| bridge → Drone (komut) | 14561 | udpout→udpin |
| Backend WebSocket | 8000 | HTTP/WS |
| Panel (Vite) | 5173 | HTTP |

## Yapay zeka asistanıyla çalışma ipucu
VS Code'da her adımı asistana şöyle verin: "`detect/rules.py` dosyasını yaz;
köprüden gelen MAVLink mesajını alsın, şu kuralları uygulasın, olay sözlüğü
döndürsün." Her dosyayı yazdıktan sonra yukarıdaki **Test** satırını çalıştırıp
doğrulayın; çalışan parçayı bir sonraki adıma taşıyın.
