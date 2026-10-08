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
//   CRASH BROWNOUT 4m12s   gercek arza: guc dususu (kirmizi)
//   CRASH TASK_WDT 45s     takilma (kirmizi)
//   POWER LOST 3h07m       uzun suren oturumdan sonra guc kesildi (kirmizi)
//   POWER CYCLE 40s        kisa oturum sonrasi guc gitti: biri resetlemis
//   REBOOT 12s             firmware'in kendi yeniden baslatmasi
//   SLEEP 2m00m            derin uyku
//   BOOT LOOP x3           arasi sirada kisa sureli acilislar (kirmizi)
//
// Not: ESP_RST_POWERON hem BOOT tusuna basmayi hem de fisi cekmeyi kapsar,
// firmware bu ikisini ayirt edemez. Ayirt edilebilen tek sey oturum suresi:
// kisa suren bir oturumdan sonra "POWER CYCLE", uzun surenden sonra
// "POWER LOST" yazilir.
const char *lastEvent();

// Ekran rengi: son kayit anormal mi? (kirmizi goster)
bool lastEventIsCritical();

// Tam gunlugu seri porta basar (USB'ye baglayinca calisir).
void dumpToSerial();

// Menude gostermek icin: kayit sayisi ve tek satirlik aciklama.
// index 0 = en yeni kayit.
uint8_t count();
bool describe(uint8_t index, char *out, size_t len);
bool describeIsCritical(uint8_t index);

// Kaydi temizler (menu ekranindan "kaydi sil" ile cagrilabilir).
void clear();

}  // namespace bootlog