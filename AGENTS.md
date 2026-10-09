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
`lang/measure_fonts.py` ve `check_help_fits.py` bu isi yapiyor.

## C++ bicim hatasini once izole dene

Derleyici hatasi veren bir bicimi, firmware'e dokunmadan once 20 satirlik bir
ornekle dogrula. Iki tur kaybettik: `static` uye fonksiyon (`this` yok) ve
`&MenuFunctions::member` (pointer-to-member, duz isaretciye cevrilmez).
`desktop/marauder_boot/syntax/` altinda ikisinin de ornegi var.

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