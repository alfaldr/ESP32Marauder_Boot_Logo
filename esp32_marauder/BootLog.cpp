#include "BootLog.h"

#include <Arduino.h>
#include <Preferences.h>
#include <esp_system.h>
#include <esp_timer.h>

#include <stdio.h>
#include <string.h>

namespace bootlog {

namespace {

constexpr const char *NAMESPACE = "bootlog";
constexpr const char *KEY_EVENTS = "ev";
constexpr const char *KEY_HEARTBEAT = "hb";
constexpr const char *KEY_SEQ = "seq";
constexpr const char *KEY_CLEAN = "clean";

constexpr size_t EVENT_COUNT = 12;
constexpr uint32_t HEARTBEAT_INTERVAL_MS = 10000;
constexpr uint32_t SHORT_RUN_MS = 45000;   // bundan kisa calisma = ani sonlanma
constexpr uint32_t UNATTENDED_RUN_MS = 120000;  // bunu asan oturumdan sonra guc
                                             // kaybi "kimse yokken" sayilir
constexpr uint32_t LOOP_THRESHOLD = 3;     // ustuste kisa acilis sayisi

Event g_events[EVENT_COUNT];
size_t g_count = 0;
uint32_t g_seq = 0;
uint32_t g_last_heartbeat = 0;
bool g_previous_clean = true;
uint32_t g_short_run_streak = 0;
char g_note[48];
bool g_critical = false;

// esp_reset_reason() degerlerini okunabilir metne cevirir (IDF 4.4 sirasi).
const char *reasonName(uint32_t reason) {
  switch (reason) {
    case 0: return "UNKNOWN";
    case 1: return "POWERON";
    case 2: return "EXT_PIN";
    case 3: return "SOFTWARE";
    case 4: return "PANIC";
    case 5: return "INT_WDT";
    case 6: return "TASK_WDT";
    case 7: return "WDT";
    case 8: return "DEEPSLEEP";
    case 9: return "BROWNOUT";
    case 10: return "SDIO";
    default: return "OTHER";
  }
}

// Bu bitis normal mi? Bilerek yeniden baslatma ve temiz guc dongusu sorun degildir.
bool isClean(uint32_t reason) {
  return reason == 1 || reason == 2 || reason == 3 || reason == 8;
}

// Gercek arza olan bitisler. Bunlar kirmizi gösterilir.
bool isCritical(uint32_t reason) {
  switch (reason) {
    case 4:   // PANIC  - kod hatasi
    case 5:   // INT_WDT
    case 6:   // TASK_WDT - takilma
    case 7:   // WDT
    case 9:   // BROWNOUT - guc dususu
    case 10:  // SDIO
      return true;
    default:
      return false;
  }
}

// Bu bitis, cihazin calisirken kendiliginden oldu mu, yoksa biri mi
// dokundu? ESP_RST_POWERON hem BOOT tusuna basmayi hem de fisi cekmeyi
// kapsar; ikisini ayirt etmek firmware icin mumkun degil. Tek ayirt
// edebildigimiz sey, oturumun ne kadar surdugu:
//   - kisa suren bir oturumdan sonra: biri kapatmis/resetlemis olma ihtimali yuksek
//   - uzun suren bir oturumdan sonra: kimse yokken guc kesildi ihtimali yuksek
bool looksUnattended(const Event &event) {
  return event.reason == 1 && event.run_ms >= UNATTENDED_RUN_MS;
}

void formatDuration(char *out, size_t len, uint32_t ms) {
  uint32_t total_seconds = ms / 1000;
  uint32_t hours = total_seconds / 3600;
  uint32_t minutes = (total_seconds % 3600) / 60;
  uint32_t seconds = total_seconds % 60;

  if (hours > 0) {
    snprintf(out, len, "%uh%02um", hours, minutes);
  } else if (minutes > 0) {
    snprintf(out, len, "%um%02us", minutes, seconds);
  } else {
    snprintf(out, len, "%us", seconds);
  }
}

void buildNote() {
  g_note[0] = '\0';
  g_critical = false;

  if (g_short_run_streak >= LOOP_THRESHOLD) {
    snprintf(g_note, sizeof(g_note), "BOOT LOOP x%u", (unsigned)g_short_run_streak);
    g_critical = true;
    return;
  }

  if (g_count == 0) {
    return;
  }

  const Event &event = g_events[g_count - 1];
  char duration[16];
  formatDuration(duration, sizeof(duration), event.run_ms);

  if (isCritical(event.reason)) {
    snprintf(g_note, sizeof(g_note), "CRASH %s %s", reasonName(event.reason), duration);
    g_critical = true;
    return;
  }

  switch (event.reason) {
    case 1:   // guc kesildi veya fiziksel reset
    case 2:
      // Arada ayirt edemedigimiz durum. Uzun suren oturumdan sonra
      // kimsenin basinda olmadigi bir guc kaybi olabilir; o zaman uyari.
      if (looksUnattended(event)) {
        snprintf(g_note, sizeof(g_note), "POWER LOST %s", duration);
        g_critical = true;
      } else {
        snprintf(g_note, sizeof(g_note), "POWER CYCLE %s", duration);
      }
      break;
    case 3:
      snprintf(g_note, sizeof(g_note), "REBOOT %s", duration);
      break;
    case 8:
      snprintf(g_note, sizeof(g_note), "SLEEP %s", duration);
      break;
    default:
      snprintf(g_note, sizeof(g_note), "POWERON %s", duration);
      break;
  }
}

void load(Preferences &prefs) {
  size_t stored = prefs.getBytesLength(KEY_EVENTS);
  if (stored == sizeof(g_events)) {
    prefs.getBytes(KEY_EVENTS, g_events, sizeof(g_events));
    g_count = EVENT_COUNT;
  } else if (stored == sizeof(Event) && stored > 0) {
    Event single;
    if (prefs.getBytes(KEY_EVENTS, &single, sizeof(single)) == sizeof(single)) {
      g_events[0] = single;
      g_count = 1;
    }
  }

  g_seq = prefs.getUInt(KEY_SEQ, 0);
  g_previous_clean = prefs.getBool(KEY_CLEAN, true);

  // Art arda kisa suren acilislari say (boot loop tespiti).
  g_short_run_streak = 0;
  for (size_t index = g_count; index > 0; --index) {
    const Event &event = g_events[index - 1];
    if (event.run_ms < SHORT_RUN_MS && event.run_ms != 0) {
      ++g_short_run_streak;
    } else {
      break;
    }
  }
}

void store(Preferences &prefs) {
  prefs.putBytes(KEY_EVENTS, g_events, sizeof(g_events));
  prefs.putUInt(KEY_SEQ, g_seq);
  prefs.putBool(KEY_CLEAN, g_previous_clean);
}

void append(uint32_t reason, uint32_t run_ms, uint32_t wallclock) {
  if (g_count < EVENT_COUNT) {
    ++g_count;
  } else {
    memmove(&g_events[0], &g_events[1], sizeof(Event) * (EVENT_COUNT - 1));
    g_count = EVENT_COUNT;
  }

  Event &event = g_events[g_count - 1];
  event.seq = g_seq;
  event.reason = reason;
  event.run_ms = run_ms;
  event.wallclock = wallclock;
}

}  // namespace

void init() {
  g_note[0] = '\0';
  g_critical = false;

  Preferences prefs;
  if (!prefs.begin(NAMESPACE, false)) {
    // NVS acilamazsa sessizce gec: firmware normal calismaya devam etmeli.
    return;
  }

  load(prefs);

  // Onceki oturumun ne kadar dayandigi: periyodik olarak yazilan heartbeat.
  uint64_t previous_heartbeat = prefs.getULong64(KEY_HEARTBEAT, 0);
  uint32_t previous_run_ms = static_cast<uint32_t>(previous_heartbeat / 1000ULL);

  const uint32_t reason = static_cast<uint32_t>(esp_reset_reason());
  const uint32_t wallclock = static_cast<uint32_t>(time(nullptr));

  append(reason, previous_run_ms, wallclock);
  ++g_seq;

  // Bu oturumun sayacini sifirla.
  prefs.putULong64(KEY_HEARTBEAT, 0);
  store(prefs);

  g_last_heartbeat = 0;
  buildNote();

  prefs.end();

  if (Serial) {
    Serial.println();
    Serial.println(F("[bootlog] son acilis nedenleri (yeni -> eski):"));
    for (size_t index = g_count; index > 0; --index) {
      const Event &event = g_events[index - 1];
      char duration[16];
      formatDuration(duration, sizeof(duration), event.run_ms);
      Serial.printf("  #%u %-10s run=%-8s %s\n",
                    (unsigned)event.seq,
                    reasonName(event.reason),
                    duration,
                    isClean(event.reason) ? "(temiz)" : "(ANORMAL DIŞI)");
    }
    Serial.print(F("[bootlog] ozet: "));
    Serial.println(g_note[0] ? g_note : "temiz");
    Serial.println();
  }
}

void heartbeat() {
  const uint32_t now = millis();
  if (now - g_last_heartbeat < HEARTBEAT_INTERVAL_MS) {
    return;
  }
  g_last_heartbeat = now;

  static Preferences prefs;
  static bool open = false;
  if (!open) {
    open = prefs.begin(NAMESPACE, false);
  }
  if (!open) {
    return;
  }
  prefs.putULong64(KEY_HEARTBEAT, esp_timer_get_time());
}

const char *lastEvent() {
  return g_note;
}

bool lastEventIsCritical() {
  return g_critical;
}

uint8_t count() {
  return static_cast<uint8_t>(g_count);
}

bool describe(uint8_t index, char *out, size_t len) {
  if (index >= g_count || out == nullptr || len == 0) {
    return false;
  }

  const Event &event = g_events[g_count - 1 - index];
  char duration[16];
  formatDuration(duration, sizeof(duration), event.run_ms);

  const char *label = "POWER CYCLE";
  bool critical = false;

  if (isCritical(event.reason)) {
    label = reasonName(event.reason);
    critical = true;
  } else {
    switch (event.reason) {
      case 1:
      case 2:
        if (looksUnattended(event)) {
          label = "POWER LOST";
          critical = true;
        } else {
          label = "POWER CYCLE";
        }
        break;
      case 3:
        label = "REBOOT";
        break;
      case 8:
        label = "SLEEP";
        break;
      default:
        label = "POWERON";
        break;
    }
  }

  snprintf(out, len, "#%u %s %s",
           (unsigned)event.seq, label, duration);
  return critical;
}

bool describeIsCritical(uint8_t index) {
  if (index >= g_count) {
    return false;
  }
  const Event &event = g_events[g_count - 1 - index];
  if (isCritical(event.reason)) {
    return true;
  }
  return looksUnattended(event);
}

void dumpToSerial() {
  if (!Serial) {
    return;
  }
  Serial.println(F("[bootlog] tam kayit:"));
  for (size_t index = 0; index < g_count; ++index) {
    const Event &event = g_events[index];
    char duration[16];
    formatDuration(duration, sizeof(duration), event.run_ms);
    Serial.printf("  #%u %-10s run=%-8s clock=%lu\n",
                  (unsigned)event.seq, reasonName(event.reason), duration,
                  (unsigned long)event.wallclock);
  }
}

void clear() {
  memset(g_events, 0, sizeof(g_events));
  g_count = 0;
  g_seq = 0;
  g_short_run_streak = 0;
  g_note[0] = '\0';

  Preferences prefs;
  if (prefs.begin(NAMESPACE, false)) {
    prefs.clear();
    prefs.end();
  }
}

}  // namespace bootlog