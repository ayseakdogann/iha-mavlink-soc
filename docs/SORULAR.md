# Sunum Soruları (5 şıklı, cevaplı)

Hocaya e-postayla gönderilecek iki çoktan seçmeli soru. Her soru 5 şıklı,
doğru cevap ve kısa gerekçe ile.

---

## Soru 1

MAVLink 2 protokolüyle haberleşen bir İHA sisteminde, saldırgan ağa sahte bir
`COMMAND_LONG` mesajı (örneğin `NAV_LAND`) enjekte ederek drone'u kaçırmıştır.
Bu saldırıyı **önlemek** için aşağıdakilerden hangisi en doğru ve yeterli
tedbirdir?

- A) Trafiği şifrelemek (yalnızca gizlilik sağlamak)
- B) Drone'un GPS alıcısını daha hassas bir modelle değiştirmek
- C) **MAVLink 2 mesaj imzalama (HMAC-SHA256) ile kaynak kimliğini ve mesaj bütünlüğünü doğrulamak; imzasız komutları reddetmek**
- D) Telemetri güncelleme hızını artırmak
- E) Yer istasyonu arayüzünü yeniden tasarlamak

**Doğru cevap: C**

**Gerçek:** Saldırının kök nedeni kimlik doğrulama/bütünlük eksikliğidir;
protokol "bu komutu kim gönderdi?" sorusuna cevap veremez. Şifreleme (A) yalnızca
gizlilik verir, enjeksiyonu engellemez — saldırgan yine geçerli görünen bir komut
üretebilir. İmzalama, hem komutun değiştirilmediğini hem de paylaşılan anahtara
sahip meşru operatörden geldiğini kanıtlar; imzasız/sahte komut köprüde düşürülür.
MITRE ATT&CK for ICS'te bu saldırı **T0855 Unauthorized Command Message** olarak
sınıflandırılır.

---

## Soru 2

Bir İHA SOC'unda saldırgan kısa sürede çok sayıda `HEARTBEAT` mesajı göndererek
hattı ve işleme kapasitesini boğmaktadır. Bu olay MITRE ATT&CK for ICS
çerçevesinde hangi tekniğe karşılık gelir ve hangi güvenlik ilkesini hedef alır?

- A) T0855 Unauthorized Command Message — Gizlilik
- B) **T0814 Denial of Service — Erişilebilirlik**
- C) T0830 Adversary-in-the-Middle — Bütünlük
- D) T0888 Remote System Information Discovery — Gizlilik
- E) T0856 Spoof Reporting Message — İnkâr edilemezlik

**Doğru cevap: B**

**Gerçek:** Yüksek hızlı mesaj seliyle sistemi hizmet veremez hâle getirmek
**Denial of Service** saldırısıdır (T0814) ve bilgi güvenliğinin **erişilebilirlik**
(availability) ilkesini hedef alır. SOC bunu mesaj hızı eşiğini (ör. 200 mesaj/s)
aşan trafikle tespit eder. Diğer şıklardaki teknikler sırasıyla komut enjeksiyonu
(T0855), araya girme/sahtecilik (T0830) ve keşif (T0888) saldırılarına aittir; bu
senaryoyla eşleşmezler.

---

*Not: Eşleme ayrıntıları için bkz. [ESLEME.md](ESLEME.md).*
