# Windows'ta Sıfırdan Kurulum ve İlk Demo

Bu rehber, Windows 10/11'de hiçbir şey kurulu değilmiş gibi başlayıp **çalışan ilk
demoya** (simülatör + sahte iniş saldırısı) kadar götürür. Her adımda komut ve
**beklenen çıktı** var. Sırayla yapın.

---

## 1. Python kur (varsa atla)

1. PowerShell aç (Başlat → "PowerShell" yaz → Enter) ve kontrol et:
   ```powershell
   python --version
   ```
   - `Python 3.11+` çıkıyorsa Python var, **Adım 2'ye geç**.
   - "not recognized" veya Microsoft Store açılıyorsa Python yok → devam.
2. https://www.python.org/downloads/ → **Download Python 3.12.x** (Windows).
3. Kurulumda **ÖNEMLİ:** en alttaki **"Add python.exe to PATH"** kutusunu işaretle,
   sonra **Install Now**.
4. PowerShell'i **kapat/yeniden aç** ve doğrula:
   ```powershell
   python --version
   ```
   **Beklenen:** `Python 3.12.x`

---

## 2. VS Code ve eklentiler

1. https://code.visualstudio.com/ → **Download for Windows** → kur.
2. VS Code'u aç, sol taraftaki **Extensions** (Ctrl+Shift+X):
   - **Python** (Microsoft) — kur.
   - **Pylance** (Python ile birlikte gelir) — kur.
3. (İsteğe bağlı, kodu GitHub'a koymak isterseniz) **Git**: https://git-scm.com/download/win

---

## 3. Projeyi aç

1. Bu thread'den **`iha-soc.zip`**'i indir (Downloads klasörüne iner).
2. Dosya Gezgini'nde zip'e sağ tık → **Tümünü ayıkla (Extract All)** → örn.
   `C:\Users\melih\Desktop\iha-soc` olacak şekilde çıkar.
3. VS Code → **File → Open Folder** → çıkardığın **`iha-soc`** klasörünü seç.
4. Sol panelde `sim/`, `attacks/`, `docs/`, `README.md` görünmeli.

---

## 4. Sanal ortam (venv) ve paketler

VS Code'da terminal aç: **Terminal → New Terminal** (Ctrl+`). Alt kısımda
PowerShell açılır, yol `...\iha-soc` olmalı.

```powershell
python -m venv .venv
```
**Beklenen:** birkaç saniye, hata yok, klasörde `.venv` oluşur.

Şimdi ortamı etkinleştir:
```powershell
.venv\Scripts\Activate.ps1
```

> **Hata alırsan** ("running scripts is disabled on this system"): PowerShell
> betiklerine izin ver, sonra tekrar etkinleştir:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> .venv\Scripts\Activate.ps1
> ```
> "Y" sorarsa **Y** yaz.

**Beklenen:** satır başında `(.venv)` görünür.

Paketleri kur:
```powershell
pip install -r requirements.txt
```
**Beklenen:** pymavlink, scikit-learn, fastapi vb. iner, sonda
`Successfully installed ...` yazar. (Birkaç dakika sürebilir.)

Doğrula:
```powershell
python -c "from pymavlink import mavutil; print('pymavlink hazir')"
```
**Beklenen:** `pymavlink hazir`

---

## 5. VS Code'un doğru Python'u kullanması

1. Sağ altta "`.venv` ortamını seç" bildirimi çıkarsa **Evet**.
2. Çıkmazsa: **Ctrl+Shift+P** → "Python: Select Interpreter" → listede
   **`.venv`** olanı seç.
3. Yeni açtığın her terminalde başta **`(.venv)`** olmalı. Olmadıysa
   `.venv\Scripts\Activate.ps1` ile etkinleştir.

---

## 6. İLK DEMO — simülatör + sahte iniş saldırısı

İki terminale ihtiyacın var.

**Terminal 1 — drone simülatörü:**
```powershell
python sim\drone_sim.py
```
**Beklenen:**
```
[sim] drone başladı, telemetri -> 127.0.0.1:14560, komut <- 127.0.0.1:14561
```
> Windows Güvenlik Duvarı "Python'a izin ver?" derse **İzin ver** (Erişime izin ver).
> Bu terminali açık bırak.

**Terminal 2 — yeni terminal aç** (terminal panelinde **+**), `(.venv)` olduğundan
emin ol. Önce uçuşu gör (saldırıdan önce irtifa artıyor mu):
```powershell
python -c "from pymavlink import mavutil; m=mavutil.mavlink_connection('udpin:127.0.0.1:14560'); print([round(m.recv_match(type='GLOBAL_POSITION_INT',blocking=True).alt/1000,1) for _ in range(4)], 'm')"
```
**Beklenen:** artan irtifa, örn. `[5.0, 10.0, 15.0, 20.0] m`

Şimdi **saldırı** — sahte "iniş" komutu:
```powershell
python attacks\inject_land.py --target 127.0.0.1:14561 --cmd LAND
```
**Beklenen (Terminal 2):**
```
[saldiri] sahte LAND komutu -> 127.0.0.1:14561 (sysid=255)
[saldiri] gonderildi (1/3) ... (3/3)
[saldiri] tamam.
```
**Beklenen (Terminal 1 — simülatör):**
```
[sim] komut -> mod=LAND
[sim] komut -> mod=LAND
[sim] komut -> mod=LAND
```

🎯 **Bu kadar!** İmzalama yokken drone sahte komutu kabul etti ve inmeye başladı —
yani kaçırıldı. İlk demo çalışıyor. Simülatörü **Ctrl+C** ile durdurabilirsin.

`--cmd DISARM` veya `--cmd RTL` ile de dene.

---

## 7. Sık karşılaşılan sorunlar

| Belirti | Çözüm |
|---|---|
| `python` komutu açılmıyor / Store açılıyor | Adım 1'i tekrar, "Add to PATH" işaretli kur; PowerShell'i yeniden aç |
| `Activate.ps1` çalışmıyor | Adım 4'teki `Set-ExecutionPolicy` komutu |
| `ModuleNotFoundError: pymavlink` | `(.venv)` aktif değil veya `pip install -r requirements.txt` yapılmadı |
| Saldırıda hiçbir şey olmuyor | Simülatör açık mı? Port doğru mu (`--target 127.0.0.1:14561`)? |
| Güvenlik duvarı uyarısı | "Erişime izin ver" (yerel bağlantı, güvenli) |

---

## 8. Sıradaki adımlar

İlk demo çalıştıktan sonra `docs/UYGULAMA.md`'yi aç ve **Hafta 1 → Adım 1.3**'ten
devam et (GPS spoof, flood, keşif saldırıları), sonra Hafta 2 (köprü, tespit
motoru, panel, yapay zeka). Her adımın kendi testi var; bir adım çalışınca
diğerine geç.

Takıldığın an buraya yaz: hata mesajını ve hangi adımda olduğunu söyle, birlikte
çözelim.
