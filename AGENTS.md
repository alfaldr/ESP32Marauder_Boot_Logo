# Bu depoda çalışma kuralları

Sadece tekrar tekrar gerçekleşen hataları engelleyen kurallar. Her kural bir
gerçek hataya karşılık geliyor; tekrarlanmayan bir şey burada yok.

## Firmware değişikliği: zorunlu sıra

Push'tan flash'a kadar bu sırayı atlama. Sıra iki kez tersine döndüğü için
CI turu ve cihaz yazma işlemi kaybedildi.

```
1. Yerel testler    -> cd esp32_marauder/lang && python check_help.py
                      -> python check_help_fits.py
                      -> python tools/check_ascii_strings.py
                      -> python tools/check_syntax.py      (C++ bicim kontrolu)
2. commit
3. push            -> git push fork custom-boot-splash
4. DOGRULA          -> gh api .../branches/custom-boot-splash --jq .commit.sha
                       yerel HEAD ile ayni olana kadar bekle
5. CI tetikle ve headSha'yi YEREL HEAD ile karsilastir
6. CI yesilse indir, flash et
7. Cihazdaki baytlari yerel dosyayla karsilastir
```

**Adım 5 atlanırsa en sık hata oluyor.** İki kez "derleme başarılı" dedim ve
cihazda eski firmware vardı: push satırını atlamıştım, CI dürüstçe eski commit'i
derlemişti. Aynı SHA256'yı iki indirmede görünce fark ettim.

## Cihaza yazmadan önce sor

Kullanıcı "flashla" demedikçe cihaza yazma. Önce testleri koş, sonucu bildir.

## PowerShell'de cok satirli Python yazma

PowerShell, `python -c "..."` icindeki tirnaklari ve `\n` karakterlerini bozar;
Go'da degisen bir sey yazmadigini sanarsin. Cok satirli her Python islemini
bir `.py` dosyasina yazip calistir. `write` araci bunun icin.

## Tahmin etme, olc

Ekran olculerini (karakter genisligi, satir sayisi, usable pixel) koddan ya da
font dosyasindan **olcerek** al. Bu oturumda `KEY_W 240` oldugunu varsayip 44
karakter hedeflemistim; gercekte 17 idi ve kullanici ekranda kaydirma gordu.
`tools/measure_fonts.py` ve `lang/check_help_fits.py` bu isi yapiyor.

## C++ bicim hatasini once izole dene

Derleyici hatasi veren bir bicimi, firmware'e dokunmadan once 20 satirlik bir
ornekle dogrula. Iki tur kaybettik: `static` uye fonksiyon (`this` yok) ve
`&MenuFunctions::member` (pointer-to-member, duz isaretciye cevrilmez).
`desktop/marauder_boot/syntax/` altinda ikisinin de ornegi var.

**Yerel derleyici var.** PlatformIO'nun xtensa g++'su kurulu, PATH'te degil:

```
C:\Users\Admin\.platformio\packages\toolchain-xtensa-esp32\bin\xtensa-esp32-elf-g++.exe
```

`python tools/check_syntax.py` `desktop/marauder_boot/syntax/*.cpp` dosyalarini
`-fsyntax-only` ile derler. Tam baglanti **calismaz** (xtensa hedefi, `_close_r
is not implemented`), ve Arduino core 2.0.11 kurulu olmadigi icin tum firmware
derlenemez -- ama sozdizimi ve makro arityasi kontrolu tam calisir.

Bu kontrolu eklemeden once `HELP_ROW` 2 argumanli kalmis, 24 cagri 3 arguman
gecmisti ve hata ancak CI'da cikti. Simdi 8 saniyede yakalanir.

## Font: ASCII disi karakter yasak

Menu fontu 0x20..0x7E araliginda ve TFT_eSPI glif tablosunu **sinir kontrolu
olmadan** indeksliyor. U+015E gibi bir karakter tablonun 318 kayıt dışına
taşıyor, `xAdvance`/`xHeight` çöp değerlerden geliyor ve çizim döngüsü
taşmaya yol açıyor (bir kez panik bu yüzden oldu). `tools/check_ascii_strings.py`
tum kaynakları tarıyor; Türkçe için duz ASCII yaz (`i`, `s`, `c`, `g`).

## Dizin disi betiklerde

Arduino sketch derleyicisi alt klasordeki `.cpp` dosyalarini guvenilir
sekilde toplamiyor. Bu yuzden katalog `lang/` altinda ama **header-only**
(`inline` fonksiyonlar). Yeni bir kaynak dosyasi eklerken bunu hatirla.

## SD kart dosyalarini elle kontrol etme

SD kart Windows'ta `D:` olarak gorunuyor (USB okuyucu). Cihazin yazdigi dosyalar
seriden de alinabiliyor ve **iki yol bit bit ayni dosyayi uretiyor** -- dogrulandi
(SHA256 esit). Yani dosya dogrulamasi icin karti cikarmaya gerek yok:

```
powershell -File tools/grab_serial_capture.ps1    # pcap'i seriye alir
python tools/rebuild_from_serial.py               # BUF bloklarini birlestirir
"C:\Program Files\Wireshark\tshark.exe" -r tools/serial_capture.pcapng -Y eapol
```

Seri yolu SD'den daha **eksiksiz**: SD'de 6 EAPOL yakalanmissa seri ciktisinda da
ayni sayi gorunur, ama seri cikisinda dosya adlarinin hepsi tek dosyaya donusur.
SD'de dosya 80 bayt ise o tarama **hic paket yakalamamis** demektir.

## Cihazda yapilan isler nerede yazili

`SESSION.md` acik isleri tutar. Bir konu "cozuldu" dediginde **oraya da yaz**:
`Complete EAPOL` cihaz omru boyunca birikiyor (oturum sayaci degil), Turkce glif
istenmedi, sayfalama dogrulandi. Bunlar tekrar "bulunacak hata" gibi gorunmesin
diye kapatildi.