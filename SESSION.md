# Oturum durumu

Bu dosya, sohbet geçmişi sıkıştırıldığında veya oturum kapandığında kaldığı
yerden devam etmek için. Yeni bir bağlamta önce bunu oku.

## Cihaz

| | |
|---|---|
| Kart | ESP-2432S028R (CYD 2432S028), ESP32-WROOM-32 4MB |
| Seri | COM5, 115200 |
| Ekran | ILI9341, **240x320 dikey** |
| Buton | `KEY_W 240`, `BUTTON_PADDING 22` -> dugmelerde 196px kullanilabilir |
| Menu fontu | `MENU_FONT &FreeSans9pt7b` (degistirildi, eski: FreeMono9pt7b) |
| Metin ekrani fontu | varsayilan GLCD 6x8, `setFreeFont(NULL)`, 38 karakter/satir |
| Durum cubugu | `STATUS_BAR_WIDTH = TFT_HEIGHT/16 = 20` |
| Menu satirlari | `BUTTON_SCREEN_LIMIT 12`, `KEY_H 22` |

**Flash adresleri:** bootloader `0x1000`, partitions `0x8000`, ota-data `0xE000`,
firmware `0x10000`, spiffs `0x290000`. Her seferinde **sadece `0x10000`** yazilir.

## Araç yollari

```
esptool        C:\Users\Admin\.platformio\penv\Scripts\esptool.exe
xtensa g++     C:\Users\Admin\.platformio\packages\toolchain-xtensa-esp32\bin\xtensa-esp32-elf-g++.exe
gh             C:\Program Files\GitHub CLI   (PATH'te degil, eklenmeli)
Wireshark      C:\Program Files\Wireshark\tshark.exe, capinfos.exe, editcap.exe
repo           C:\Users\Admin\firmware\ESP32Marauder
calisma alani  C:\Users\Admin\Desktop\marauder_boot  (gomulu, gecici; kalici
              betikler artik tools/ ve lang/ altinda)
SD kart        D:  (USB okuyucu ile baglanir, kart cihazda takili kalir)
```

**Duzeltme (2026-10-09):** xtensa g++ **PATH'te degil ama kurulu**. C++ bicim
kontrolu icin:
`& "C:\Users\Admin\.platformio\packages\toolchain-xtensa-esp32\bin\xtensa-esp32-elf-g++.exe"`
Onceki not "yerel derleme yok" diyordu; g++ var, ancak **Arduino core 2.0.11
kurulu degil**, tam firmware derlenemez. Kucuk ornekleri `.exe` olarak derlemek
icin yine de yeterli.

## Derleme

Yerel derleme **yok**; core 2.0.11 gerekiyor, bilgisayarda 3.3.9 var.
GitHub Actions kullanilir: `.github/workflows/build-cyd-boot.yml`

Zorunlu sira ve tuzaklar `AGENTS.md` icinde. Ozu: push -> remote head dogrula ->
CI `headSha` = yerel HEAD -> flash.

## Cihazda su an ne var

Son basarili build: commit **`e8be2b8`**, firmware 1.736.992 bayt, COM5'e
yazildi ve dogrulandi. Icerir:

- Ozel renkli boot splash (logo + "HOLY MACHINE"), SD'den okunur
- `Device > Boot Log` — NVS'te 12 kayitlik halk tampon, reset nedeni + sure
- 802.11 frame ayristirma guvenlik duzeltmeleri (PR #1281, #1349, #1376)
  - SSID uzunlugu tasma korumasi (`SSID_LEN`)
  - `channel_activity` indeks korumasi
  - `malloc` sonucu kontrolu
- **pcapng yakalama + paket basina yorum** (`EAPOL M3 bssid=... sta=... ssid=...`)
- `Device > Quick Reference` — 5 bolum, EN/TR, sayfali metin ekrani
- `capformat <pcapng|pcap>` CLI komutu

## Tamamlanan isler

- Tur 1 guvenlik PR'lari (bellek guvenligi, SSID tasma, channel_activity)
- pcapng + yorumlar; aircrack-ng pcapng okuyamadigi icin `capformat pcap` secenegi
- Quick Reference: katalog + uretici + iki dil + sayfalama
- Boot log'da ASCII duzeltmesi (TFT_eSPI glif sinir kontrolu yapmiyor -> panik)
- Boot log ozeti artik kotu biten son oturumu gosteriyor

## Acik isler

1. **pcapng gercek dosyayla dogrulanmadi.** SD kart takip bir hedef agda
   `WiFi > Sniffers > EAPOL/PMKID Scan` calistir, dosyayi cikar, `capinfos` ile
   formati ve `tshark` ile yorumlari kontrol et. Aircrack-ng icin:
   `editcap -F libpcap x.pcapng x.pcap`
2. ~~Menude EAPOL/PMKID Scan deauth gondermiyor~~ **Kapatildi: kullanici
   sorun cozuldu deyip bu konuya dokunulmamasini istedi** (2026-10-09).
   Gercek durum buydu: deauth **gonderiyor**, `ForcePMKID` ayari acik oldugu
   icin (`settings -s ForcePMKID enable`). Ayar kalici oldugundan menudeki
   her taramada gider; `DEAUTH TX` ekranda gorunuyor. Degisiklik yapilmayacak,
   yalnizca not: ayar kapaliyken mod sessizce bos yakalar ve kullanici
   `DEAUTH TX: FALSE` yazisini okumak zorunda.
3. ~~Turkce glifler~~ **Kapatildi: kullanici Turkce karakterden vazgecsti**
   (2026-10-09). Katalog ASCII'de kalir: `Koklayicilar`, `BSSID'i`,
   `Saldirilar`. Ozel font uretme denemesi yapilmadi. Tek istisna olarak
   dosya icerigi etkilenmez: yakalanan ag adlari yorumlara ham bayt olarak
   yazildigi icin SSID'ler Turkce karakterleri kayipsiz tasir
   (orn. `Saygılarr`), yalnizca ekran cizimi kisitli.
4. ~~Quick Reference sayfalama~~ **Dogrulandi** (2026-10-09): `1/2 dokun:
   ileri` ile sayfa ilerletme calisiyor, son sayfadan sonra dizine donuyor.
5. Iptal edilenler: `[x]` butonu, Boot Log metin ekranina cevirme.

## Kalici tuslaklar

- Ekran metinleri **ASCII olmali**; aksi halde TFT_eSPI glif tablosunu sinir
  kontrolu olmadan indeksliyor (bkz. `tools/check_ascii_strings.py`). Artik
  kural degil, karar: Turkce glif uretmek denendi ve birakildi, donanim
  fontunda Turkce karakter yok ve eklemek icin ozel font gerekiyor
- **Yerelde C++ derlenemiyor** (toolchain yok). Derleme dogrulamasi yalnizca
  CI; makro arityasi gibi hatalar ancak orada yakalaniyor
- `lang/` altindaki kaynaklar **header-only**; sketch derleyicisi alt klasordeki
  `.cpp` dosyalarini derlemiyor
- Cataloglari elle degistirme: `lang/help.*.txt` -> `python lang/gen_help.py`
- Flash cihazda `Device > Boot Log` ekraninda gorunur; seri `bootlog` satirlari
  acilista basilir