#include "HelpLang.h"

// Language state and names. The strings themselves are generated into
// HelpLang_gen.cpp; only the one-byte current-language index lives here.
//
// This is not persisted: a reference text is not worth a settings migration,
// and a wrong guess after a firmware update would be more confusing than a
// reset to English. Pick the language once from the reference index.

namespace {

const char *const kLangLabel[LANG_COUNT] PROGMEM = {
    [LANG_EN] = "English",
    [LANG_TR] = "Turkce",
};

HelpLang g_lang = LANG_EN;

}  // namespace

void helpSetLang(HelpLang lang) {
  if (lang < LANG_COUNT) g_lang = lang;
}

HelpLang helpGetLang() { return g_lang; }

const char *helpLangLabel(HelpLang lang) {
  if (lang >= LANG_COUNT) lang = LANG_EN;
  return reinterpret_cast<const char *>(pgm_read_ptr(&kLangLabel[lang]));
}