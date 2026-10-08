#pragma once

#include <stdint.h>

// Kalici acilis/kapanis gunlugu.
//
// Amac: cihaz kendi kendine kapandiginda (brownout, panik, watchdog) sebebi
// suphesiz kalmamak. Her acilista:
//   - onceki calismanin bitis sebebi ve suresi NVS'ye yazilir,
//   - bu kayit ekranda kisa bir satir olarak gosterilir,
//   - seri porta tam gunluk basilir.
//
// Normal kapatma (bilerek yeniden baslatma) "NORMAL" olarak isaretlenir, boylece
// gercek sorunlar abnormal kayitlardan ayirt edilir.

namespace bootlog {

// Bir calisma oturumunun kaydi (16 bayt).
struct Event {
  uint32_t seq;         // artan sira numarasi
  uint32_t reason;      // esp_reset_reason() degeri
  uint32_t run_ms;      // onceki calismanin suresi (ms)
  uint32_t wallclock;   // time(NULL), yoksa 0
};

// setup() icinde, ekran ve diger herseyden once cagrilir.
void init();

// Ana dongude periyodik cagrilir: calisma suresini NVS'ye yazar, boylece
// bir sonraki acilista "ne kadar dayandi" bilgisi bulunur.
void heartbeat();

// Son kaydin kisa metnini dondurur. Ornek:
//   "CRASH BROWNOUT 4m12s"   (guc dususu: en olası sebep)
//   "CRASH PANIC 1m03s"      (kod hatasi)
//   "CRASH TASK_WDT 45s"     (takilma)
//   "POWER LOSS 3h07m"       (cihaz kendi kendine kapandi)
//   "REBOOT 12s"             (bilerek yeniden baslatildi)
//   "BOOT LOOP x3"           (arasi sirada kisa sureli acilislar)
// Bos string ise sorun yok.
const char *lastEvent();

// Ekran rengi: son kayit anormal mi? (kirmizi goster)
bool lastEventIsCritical();

// Tam gunlugu seri porta basar (USB'ye baglayinca calisir).
void dumpToSerial();

// Kaydi temizler (menu ekranindan "kaydi sil" ile cagrilabilir).
void clear();

}  // namespace bootlog