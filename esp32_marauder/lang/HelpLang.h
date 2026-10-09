#pragma once

#include <pgmspace.h>
#include <stdint.h>

// ---------------------------------------------------------------------------
// Help catalogue.
//
// The menu clips a node label wider than KEY_W - 2*BUTTON_PADDING and scrolls
// it sideways. On the CYD that is 240 - 44 = 196 px, and FreeMono9pt7b advances
// about 11 px per character, so 18 characters already triggers the marquee.
// Since the menu is scrolled vertically anyway, a sideways scrolling label is
// unpleasant, so every string is wrapped to HELP_LINE_MAX at build time
// instead of at runtime.
//
// The catalogue lives in lang/help.<lang>.txt and is compiled into
// HelpLang_gen.{h,cpp} by lang/gen_help.py. Translators edit the text files
// only; they never touch code. Adding a language is one new .txt file plus one
// entry in gen_help.py's LANGS map.
//
// The font is ASCII-only, so Turkish and similar need a plain transliteration
// ('i' for 'ı', 's' for 'ş', ...). The generator rejects non-ASCII outright so
// a stray accented character cannot turn into boxes on the device.
// ---------------------------------------------------------------------------

#define HELP_LINE_MAX 17

// Text lives in flash, so it must be read through pgm_read_ptr.
#define HELP_FMT(line) (reinterpret_cast<const char *>(pgm_read_ptr(line)))

enum HelpLang : uint8_t {
  LANG_EN = 0,
  LANG_TR = 1,
  LANG_COUNT,
};

// HelpId is generated; see HelpLang_gen.h.
#include "HelpLang_gen.h"

// One wrapped line, in flash. Never nullptr.
const char *helpText(HelpId id);

// Every line of the field starting at `base`, in order. Continuation ids are
// allocated contiguously, so this walks forward and stops at the first empty
// one. Returns how many were written, capped at `max`.
uint8_t helpLines(HelpId base, const char **out, uint8_t max);

void helpSetLang(HelpLang lang);
HelpLang helpGetLang();

// Endonym, so the language is readable whatever the current locale is.
const char *helpLangLabel(HelpLang lang);