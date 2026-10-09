#pragma once

#include <pgmspace.h>
#include <stdint.h>

// ---------------------------------------------------------------------------
// Help catalogue.
//
// The menu clips a node label wider than KEY_W - 2*BUTTON_PADDING and scrolls
// it sideways. On the CYD that is 240 - 44 = 196 px, and the menu font
// (FreeSans9pt7b) advances about 10 px per lowercase glyph, so anything past
// that scrolls. The menu is scrolled vertically anyway, so a sideways
// scrolling label is unpleasant to read, and every string is therefore wrapped
// to the button's pixel width at build time instead of at runtime.
//
// Everything here is header-only and inline. The Arduino sketch builder does
// not reliably compile .cpp sources in subfolders, and a header has no such
// dependency: one definition however many translation units include it.
//
// The catalogue itself lives in lang/help.<lang>.txt and is compiled into
// HelpLang_gen.h by lang/gen_help.py. Translators edit the text files only;
// they never touch code. Adding a language is one .txt file plus one entry in
// the generator's LANGS map.
//
// The font has no glyphs above 127, so Turkish needs a plain transliteration
// ('i' for dotless i, 's' for s-cedilla, and so on). The generator rejects
// non-ASCII outright so an accented character cannot turn into boxes on the
// device unnoticed. Proper Turkish would mean generating a font carrying those
// eight glyphs.
// ---------------------------------------------------------------------------

enum HelpLang : uint8_t {
  LANG_EN = 0,
  LANG_TR = 1,
  LANG_COUNT,
};

// Not persisted on purpose: a reference text is not worth a settings
// migration, and a wrong guess after a firmware update would be more confusing
// than falling back to English. Pick the language from the reference index.
inline HelpLang g_help_lang = LANG_EN;

inline void helpSetLang(HelpLang lang) {
  if (lang < LANG_COUNT) g_help_lang = lang;
}

inline HelpLang helpGetLang() { return g_help_lang; }

// Endonym, so a language is readable whatever the current locale is.
inline const char *helpLangLabel(HelpLang lang) {
  switch (lang) {
    case LANG_TR: return "Turkce";
    case LANG_EN:
    default: return "English";
  }
}

// HelpId, helpText() and helpLines() come from the generated header.
#include "HelpLang_gen.h"