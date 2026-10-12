"""Vowel marks and transliteration for a Persian word from its IPA pronunciation.

The frequency dictionary gives each headword in Persian letters plus an IPA pronunciation (Iranian
Persian). The site's voice reads Persian letters, so short vowels have to be written as marks, and the
site shows pronunciations in its own simple transliteration (DATA_FORMAT.md). This module aligns the
letters with the IPA and produces both:

    vowelize("دولت", "dowlæt")  ->  ("دَولَت", "dowlat", 0)

The last value is the alignment cost: 0 means every letter and sound was accounted for; higher values
mean the alignment had to guess (a silent letter, an unwritten sound). Callers use a threshold.
Rules (learned from the voice, see DATA_FORMAT.md): marks only (removing them gives the word back);
a tashdid goes before the vowel mark on the same letter; no kasra on the letter before a final
silent ه (the ه itself stands for that e).
"""
import re
import sys

FATHA, KASRA, DAMMA, SHADDA = "َ", "ِ", "ُ", "ّ"
MARKS = re.compile(r"[ً-ْٰ]")
ZWNJ = "‌"

# Letter -> the consonant sounds it can stand for (IPA as used in the dictionary).
CONS = {
    "ب": "b", "پ": "p", "ت": "t", "ث": "s", "ج": "ʤ", "چ": "ʧ", "ح": "h", "خ": "x", "د": "d", "ذ": "z", "ر": "r",
    "ز": "z", "ژ": "ʒ", "س": "s", "ش": "ʃ", "ص": "s", "ض": "z", "ط": "t", "ظ": "z", "غ": "ɣq", "ف": "f", "ق": "ɣq",
    "ک": "k", "گ": "ɡg", "ل": "l", "م": "m", "ن": "n", "ه": "h", "ة": "th", "و": "vw", "ی": "j",
    "ع": "ʔɁ", "ء": "ʔɁ", "ئ": "ʔɁj", "ؤ": "ʔɁv", "أ": "ʔɁ", "إ": "ʔɁ",
}
GLOTTAL = set("عءئؤأإ")
SHORT = {"æ": FATHA, "e": KASRA, "o": DAMMA}
LONG = {"ا": "ɑ", "آ": "ɑ", "و": "u", "ی": "i"}
TRANS = {"ɑ": "ā", "æ": "a", "e": "e", "o": "o", "u": "u", "i": "i", "x": "kh", "ɣ": "gh", "q": "gh", "ɢ": "gh",
         "ʃ": "sh", "ʒ": "zh", "ʧ": "ch", "ʤ": "j", "ʔ": "'", "Ɂ": "'", "j": "y", "ɡ": "g", "g": "g", "w": "w"}


def first_variant(ipa):
    return str(ipa or "").split(",")[0].strip()


def transliterate(ipa):
    """IPA -> the site's simple transliteration (ā, kh, gh, sh, ch, zh, ')."""
    out = []
    for ch in first_variant(ipa):
        out.append(TRANS.get(ch, ch))
    r = "".join(out)
    for d in ("kh", "gh", "sh", "ch", "zh"):
        r = r.replace(d + d, d[0] + d)  # doubled consonant: tahaqqoq -> "tahaggh" style, not "ghgh"
    return r


def tokens(ipa):
    """Split the IPA into sounds; 'ow' and 'ej' before a consonant or the end become diphthong tokens."""
    s = first_variant(ipa)
    toks, i = [], 0
    while i < len(s):
        c = s[i]
        nxt = s[i + 1] if i + 1 < len(s) else ""
        after = s[i + 2] if i + 2 < len(s) else ""
        if c == "o" and nxt == "w" and (not after or after not in "ɑæeiou"):
            toks.append("ow"); i += 2; continue
        if c == "e" and nxt == "j" and (not after or after not in "ɑæeiou"):
            toks.append("ej"); i += 2; continue
        if c == " ":
            toks.append(" ")
        elif c in "ɑæeiou":
            toks.append(c)
        else:
            toks.append(c)
        i += 1
    return toks


def align(word, ipa):
    """Dynamic-programming alignment of letters to sounds. Returns (cost, ops) or None.
    ops: list of (letter_index, kind, mark) where kind is 'cons' / 'long' / 'skip' / 'space' and
    mark is the vowel mark (and optional shadda) to write after the letter."""
    L = list(word)
    T = tokens(ipa)
    n, m = len(L), len(T)
    INF = 10 ** 9
    # best[i][j] = (cost, back pointer)
    best = [[(INF, None)] * (m + 1) for _ in range(n + 1)]
    best[0][0] = (0, None)

    def relax(i, j, cost, i2, j2, op):
        c = best[i][j][0] + cost
        if c < best[i2][j2][0]:
            best[i2][j2] = (c, (i, j, op))

    is_vowel = lambda t: t in ("ɑ", "æ", "e", "o", "u", "i", "ow", "ej")
    for i in range(n + 1):
        for j in range(m + 1):
            if best[i][j][0] >= INF:
                continue
            if i == n and j == m:
                continue
            letter = L[i] if i < n else None
            tok = T[j] if j < m else None
            prev_letter = L[i - 1] if i > 0 else None
            next_letter = L[i + 1] if i + 1 < n else None
            is_final = (i == n - 1) or (next_letter in (" ", ZWNJ))
            is_initial = (i == 0) or (prev_letter in (" ", ZWNJ))
            # --- letter that produces nothing
            if letter is not None:
                if letter == ZWNJ or MARKS.match(letter):
                    relax(i, j, 0, i + 1, j, (i, "skip", ""))
                elif letter == " ":
                    if tok == " ":
                        relax(i, j, 0, i + 1, j + 1, (i, "space", ""))
                    relax(i, j, 0.5, i + 1, j, (i, "skip", ""))
                elif letter in GLOTTAL:
                    relax(i, j, 0.4, i + 1, j, (i, "skip", ""))      # silent ع etc.
                elif letter == "و" and prev_letter == "خ":
                    relax(i, j, 0.3, i + 1, j, (i, "skip", ""))      # خواهر, خواستن
                elif letter == "ا" and is_initial:
                    relax(i, j, 0.2, i + 1, j, (i, "skip", ""))      # alef carrying i/u: ایران, او
                elif letter == "ا" and next_letter in ("ی", "و"):
                    relax(i, j, 0.6, i + 1, j, (i, "skip", ""))      # بنابراین
                else:
                    relax(i, j, 2.5, i + 1, j, (i, "skip", ""))      # unexplained silent letter
            # --- sound that no letter writes
            if tok is not None:
                if tok == " ":
                    relax(i, j, 0.5, i, j + 1, (i, "skipsound", ""))
                else:
                    relax(i, j, 2.5, i, j + 1, (i, "skipsound", ""))
            if letter is None or tok is None or letter in (" ", ZWNJ) or MARKS.match(letter):
                continue
            if letter == "ا" and next_letter == "\u064b" and tok == "æ" and j + 1 < m and T[j + 1] == "n":
                relax(i, j, 0, i + 1, j + 2, (i, "long", ""))         # tanvin: -an
            # --- long vowels and diphthongs on ا آ و ی
            if letter in LONG and tok == LONG[letter]:
                relax(i, j, 0 if letter != "ا" or not is_initial else 0.6, i + 1, j + 1, (i, "long", ""))
            if letter == "ا" and is_initial and tok in SHORT:
                relax(i, j, 0, i + 1, j + 1, (i, "cons", SHORT[tok]))   # اَ اِ اُ
            if letter == "و" and tok == "o":
                relax(i, j, 0.3, i + 1, j + 1, (i, "long", ""))          # تو, دو
            if letter == "و" and tok == "ow":
                relax(i, j, 0.2, i + 1, j + 1, (i, "diph", FATHA))       # fatha goes on the letter before
            if letter == "ی" and tok == "ej":
                relax(i, j, 0.2, i + 1, j + 1, (i, "diph", FATHA))
            if letter == "ی" and tok == "e" and is_final:
                relax(i, j, 1.0, i + 1, j + 1, (i, "long", ""))
            if letter == "ی" and tok == "ɑ" and is_final:
                relax(i, j, 0.5, i + 1, j + 1, (i, "long", ""))          # حتی = hattā
            if letter == "ی" and tok == "i" and j + 1 < m and T[j + 1] == "j":
                # ی standing for i + y (میان mijān); doubled y gets a shadda (رسمیّت rasmiyyat)
                k = 2
                if j + 2 < m and T[j + 2] == "j":
                    k = 3
                nxt = T[j + k] if j + k < m else None
                shadda = SHADDA if k == 3 else ""
                if nxt in SHORT:
                    relax(i, j, 0.2, i + 1, j + k + 1, (i, "cons", shadda + SHORT[nxt]))
                relax(i, j, 0.2, i + 1, j + k, (i, "cons", shadda))
            if letter == "ی" and tok == "ej" and j + 1 < m and T[j + 1] == "j":
                nxt = T[j + 2] if j + 2 < m else None                 # سیّد seyyed
                if nxt in SHORT:
                    relax(i, j, 0.3, i + 1, j + 3, (i, "diph", SHADDA + SHORT[nxt]))
                relax(i, j, 0.3, i + 1, j + 2, (i, "diph", SHADDA))
            if letter == "ی" and tok in ("ʔ", "Ɂ"):
                nxt = T[j + 1] if j + 1 < m else None                 # ی as a hamza seat: شناسایی
                if nxt in SHORT:
                    relax(i, j, 0.5, i + 1, j + 2, (i, "cons", SHORT[nxt]))
                relax(i, j, 0.5, i + 1, j + 1, (i, "cons", ""))
            if letter == "ی" and tok == "j" and j + 1 < m and T[j + 1] == "i":
                relax(i, j, 0.3, i + 1, j + 2, (i, "cons", ""))        # حرفه‌ای -yi
            if letter in GLOTTAL and tok in SHORT:
                relax(i, j, 0.2, i + 1, j + 1, (i, "cons", SHORT[tok]))  # عَلی, عُضو
            if letter == "ا" and not is_initial and tok in SHORT:
                relax(i, j, 0.6, i + 1, j + 1, (i, "cons", SHORT[tok]))  # حدّاَقل
            if letter == "ن" and tok == "m" and next_letter == "ب":
                nxt = T[j + 1] if j + 1 < m else None                 # دنبال dombāl
                if nxt in SHORT:
                    relax(i, j, 0.2, i + 1, j + 2, (i, "cons", SHORT[nxt]))
                relax(i, j, 0.2, i + 1, j + 1, (i, "cons", ""))
            if letter == "ه" and tok == "e" and is_final:
                relax(i, j, 0, i + 1, j + 1, (i, "long", ""))            # silent final heh = e
            if letter == "ه" and tok == "æ" and is_final:
                relax(i, j, 0.8, i + 1, j + 1, (i, "long", ""))          # نه = na
            if letter == "ة" and tok == "e" and is_final:
                relax(i, j, 0.5, i + 1, j + 1, (i, "long", ""))
            if letter == "ی" and tok == "i" and is_final and prev_letter == "ا" and is_initial:
                pass
            # --- consonant letters, optionally doubled, optionally followed by a short vowel
            sounds = CONS.get(letter, "")
            if tok in sounds or (letter == "ا" and is_initial and tok in ("ʔ", "Ɂ")):
                cost = 0 if tok in sounds else 0.3
                ks = [1]
                if j + 1 < m and T[j + 1] == tok and tok != "w":
                    ks.append(2)                                      # doubled consonant -> shadda
                for k in ks:
                    nxt = T[j + k] if j + k < m else None
                    shadda = SHADDA if k == 2 else ""
                    heh_final = next_letter == "ه" and (i + 1 == n - 1 or (i + 2 < n and L[i + 2] in (" ", ZWNJ)))
                    if nxt in SHORT and not (nxt == "e" and heh_final):
                        relax(i, j, cost, i + 1, j + k + 1, (i, "cons", shadda + SHORT[nxt]))
                    if nxt == "e" and heh_final:
                        relax(i, j, cost + 1.0, i + 1, j + k + 1, (i, "cons", shadda + KASRA))
                    relax(i, j, cost, i + 1, j + k, (i, "cons", shadda))
            elif sounds and tok not in ("ɑ", "æ", "e", "o", "u", "i", "ow", "ej", " "):
                # consonant mismatch (e.g. q for ɣ, h for ح): substitution
                nxt = T[j + 1] if j + 1 < m else None
                if nxt in SHORT:
                    relax(i, j, 3.0, i + 1, j + 2, (i, "cons", SHORT[nxt]))
                relax(i, j, 3.0, i + 1, j + 1, (i, "cons", ""))
    if best[n][m][0] >= INF:
        return None
    ops, i, j = [], n, m
    while best[i][j][1] is not None:
        pi, pj, op = best[i][j][1]
        ops.append(op)
        i, j = pi, pj
    ops.reverse()
    return best[n][m][0], ops


def vowelize(word, ipa):
    """Return (vowel-marked word, transliteration, cost). On failure the word comes back unmarked with cost 99."""
    word = str(word or "").strip()
    r = transliterate(ipa)
    if not word or not first_variant(ipa):
        return word, r, 99
    res = align(word, ipa)
    if res is None:
        return word, r, 99
    cost, ops = res
    L = list(word)
    marks = [""] * len(L)
    if MARKS.search(word):
        return word, r, cost
    for (i, kind, mark) in ops:
        if kind == "cons" and mark:
            marks[i] = mark
        elif kind == "diph":
            if mark and mark != FATHA:
                marks[i] = mark                                       # shadda (+ vowel) on the ی itself
            # fatha on the nearest consonant letter before this و / ی
            k = i - 1
            while k >= 0 and L[k] in (ZWNJ,):
                k -= 1
            if k >= 0 and L[k] not in (" ",):
                if SHADDA in marks[k]:
                    marks[k] = SHADDA + FATHA
                else:
                    marks[k] = FATHA
    out = "".join(L[i] + marks[i] for i in range(len(L)))
    assert MARKS.sub("", out) == MARKS.sub("", word)
    return out, r, cost


def main():
    if len(sys.argv) >= 3:
        print(vowelize(sys.argv[1], sys.argv[2]))
        return
    tests = [("دولت", "dowlæt"), ("خانه", "xɑne"), ("اول", "ævvæl"), ("ایران", "irɑn"), ("بودن", "budæn"),
             ("کردن", "kærdæn"), ("خواهر", "xɑhær"), ("و", "vɑv, væ"), ("تورم", "tævæррom".replace("рр", "rr")),
             ("می‌خواستن", "mixɑstæn"), ("ملی", "melli"), ("عدد", "ʔædæd"), ("ساعت", "sɑʔæt"), ("نه", "næ, noh"),
             ("کی", "kej"), ("به رسمیت شناختن", "be ræsmijjæt ʃenɑxtæn"), ("جمعه", "ʤomʔe"), ("شش", "ʃeʃ"), ("دو", "do, dow")]
    for w, p in tests:
        print(w, p, "->", vowelize(w, p))


if __name__ == "__main__":
    main()
