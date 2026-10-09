"""Check World News Words data before publishing.

usage:
  python3 tools/check_data.py            validate data/news.json and data/glossary.json
  python3 tools/check_data.py --missing  print (as JSON) every story word that has no glossary entry

Exit code 1 means something must be fixed before committing.
"""
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wordlib import tokens, sentences, needs_entry, is_acronym, norm, lookup  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS = os.path.join(ROOT, "data", "news.json")
GLOSSARY = os.path.join(ROOT, "data", "glossary.json")

TAGS = {"World", "Politics", "Business", "Health", "Science", "Technology", "Environment", "Culture", "Sport"}
POS = {"noun", "verb", "adjective", "adverb", "preposition", "conjunction", "pronoun", "determiner",
       "number", "phrase", "proper noun", "abbreviation"}
MAX_STORIES = 60
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG = re.compile(r"^[a-z0-9][a-z0-9\-]{5,120}$")
KANA = re.compile(r"^[ぁ-ゟ゠-ヿー\s・]+$")
KANJI = re.compile(r"[㐀-䶿一-鿿々]")
ROMAJI = re.compile(r"^[a-zāīūēō' \-]+$")
PERSIAN = re.compile(r"^[؀-ۿ‌‏\s\-]+$")
PERSIAN_SENT = re.compile(r"^[؀-ۿ‌‏\s\-.,،؛؟!«»:0-9۰-۹()$%]+$")
ARABIC_ONLY = re.compile(r"[يك]")
LATIN = re.compile(r"^[a-zāīūēō' \-]+$")
LATIN_SENT = re.compile(r"^[A-Za-zāīūēōĀĪŪ' \-.,?!:;0-9()$%]+$")
CJK = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF]")
ZH_W = re.compile(r"^[\u3400-\u4DBF\u4E00-\u9FFF·A-Za-z0-9]+$")
PINYIN = re.compile(r"^[A-Za-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüÜĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙ'’ ·\-0-9]+$")
PINYIN_SENT = re.compile(r"^[A-Za-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüÜĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙ'’ ·\-0-9.,?!:;，。？！：；、“”\"()（）%]+$")
HARAKAT = re.compile(r"[\u064B-\u0652\u0670]")
AUDIO_DIR = os.path.join(ROOT, "data", "audio", "fa")
ALPHABETS = os.path.join(ROOT, "data", "alphabets.json")
RUBY_BAD = re.compile(r"[㐀-䶿一-鿿々]+(?!\[)(?![㐀-䶿一-鿿々])")


def has_audio(i):
    return bool(i) and os.path.exists(os.path.join(AUDIO_DIR, str(i) + ".mp3"))


def check_entry(k, e, errs, warns=None):
    warns = warns if warns is not None else []
    where = f"glossary entry '{k}'"
    if k != k.lower():
        errs.append(f"{where}: key must be lowercase")
    for f in ("t", "pos", "def", "ipa", "ja", "fa"):
        if f not in e:
            errs.append(f"{where}: missing '{f}'")
    if e.get("pos") not in POS:
        errs.append(f"{where}: pos '{e.get('pos')}' not allowed")
    ipa = str(e.get("ipa", ""))
    if not (ipa.startswith("/") and ipa.endswith("/") and len(ipa) > 2):
        errs.append(f"{where}: ipa must be /.../")
    ja, fa = e.get("ja") or {}, e.get("fa") or {}
    if not ja.get("w"):
        errs.append(f"{where}: ja.w missing")
    if not KANA.match(str(ja.get("k", ""))):
        errs.append(f"{where}: ja.k must be kana only: {ja.get('k')!r}")
    if not ROMAJI.match(str(ja.get("r", ""))):
        errs.append(f"{where}: ja.r bad romaji: {ja.get('r')!r}")
    if not PERSIAN.match(str(fa.get("w", ""))) or ARABIC_ONLY.search(str(fa.get("w", ""))):
        errs.append(f"{where}: fa.w must be Persian script (ی and ک): {fa.get('w')!r}")
    if not LATIN.match(str(fa.get("r", ""))):
        errs.append(f"{where}: fa.r bad transliteration: {fa.get('r')!r}")
    zh = e.get("zh") or {}
    if not ZH_W.match(str(zh.get("w", ""))):
        errs.append(f"{where}: zh.w must be Simplified Chinese: {zh.get('w')!r}")
    if not PINYIN.match(str(zh.get("p", ""))):
        errs.append(f"{where}: zh.p must be pinyin with tone marks: {zh.get('p')!r}")
    if fa.get("v") and HARAKAT.sub("", fa["v"]) != HARAKAT.sub("", str(fa.get("w", ""))):
        errs.append(f"{where}: fa.v must be fa.w plus vowel marks only")
    if not fa.get("v"):
        warns.append(f"{where}: no fa.v (vowel-marked spelling for the audio)")
    if not has_audio(fa.get("a")):
        warns.append(f"{where}: no Farsi audio (run python3 tools/make_audio.py)")
    if e.get("key"):
        zc = e.get("zhChars")
        want_zh = CJK.findall(str(zh.get("w", "")))
        if not isinstance(zc, list) or [x.get("c") for x in zc if isinstance(x, dict)] != want_zh:
            errs.append(f"{where}: zhChars must list each character of zh.w {want_zh}")
        exz = e.get("ex") or {}
        if not CJK.search(str(exz.get("zh", ""))):
            errs.append(f"{where}: ex.zh missing")
        if not PINYIN_SENT.match(str(exz.get("zhP", ""))):
            errs.append(f"{where}: ex.zhP must be pinyin: {exz.get('zhP')!r}")
        if exz.get("faV") and HARAKAT.sub("", exz["faV"]) != HARAKAT.sub("", str(exz.get("fa", ""))):
            errs.append(f"{where}: ex.faV must be ex.fa plus vowel marks only")
        if not has_audio(exz.get("faA")):
            warns.append(f"{where}: no Farsi audio for the example (run python3 tools/make_audio.py)")
        jk = e.get("jaKanji")
        want = KANJI.findall(str(ja.get("w", "")))
        if not isinstance(jk, list) or [x.get("c") for x in jk if isinstance(x, dict)] != want:
            errs.append(f"{where}: jaKanji must list each kanji of ja.w {want}")
        ex = e.get("ex") or {}
        for f in ("en", "ja", "fa", "faR"):
            if not ex.get(f):
                errs.append(f"{where}: ex.{f} missing")
        exja = str(ex.get("ja", ""))
        if RUBY_BAD.search(exja):
            errs.append(f"{where}: ex.ja has kanji without [reading]: {exja!r}")
        for m in re.finditer(r"\[([^\]]*)\]", exja):
            if not KANA.match(m.group(1)):
                errs.append(f"{where}: ex.ja reading not kana: {m.group(1)!r}")
        if not PERSIAN_SENT.match(str(ex.get("fa", ""))) or ARABIC_ONLY.search(str(ex.get("fa", ""))):
            errs.append(f"{where}: ex.fa must be Persian script: {ex.get('fa')!r}")
        if not LATIN_SENT.match(str(ex.get("faR", ""))):
            errs.append(f"{where}: ex.faR bad transliteration: {ex.get('faR')!r}")


def story_lookup(glossary, story, word):
    senses = story.get("senses") or {}
    s = senses.get(word) or senses.get(norm(word))
    if s and s in glossary["entries"]:
        return s
    return lookup(glossary, word)


def main():
    want_missing = "--missing" in sys.argv
    news = json.load(open(NEWS, encoding="utf-8"))
    glossary = json.load(open(GLOSSARY, encoding="utf-8"))
    entries, forms = glossary.get("entries", {}), glossary.get("forms", {})
    errs, missing, warns = [], [], []

    for k, e in entries.items():
        check_entry(k, e, errs, warns)
    if os.path.exists(ALPHABETS):
        try:
            alpha = json.load(open(ALPHABETS, encoding="utf-8"))
            for l in ("ja", "en", "fa", "zh"):
                if not isinstance(alpha.get(l), dict) or not alpha[l].get("sections"):
                    errs.append(f"alphabets.json: '{l}' missing")
            for sec in (alpha.get("fa") or {}).get("sections", []):
                for c in sec.get("cells", []):
                    if c and not has_audio((c.get("ex") or {}).get("a")):
                        warns.append(f"alphabets.json: no audio for Farsi example {(c.get('ex') or {}).get('w')!r}")
        except ValueError as ex:
            errs.append(f"alphabets.json: not valid JSON ({ex})")
    for f, k in forms.items():
        if f != f.lower() and not is_acronym(f):
            errs.append(f"glossary form '{f}': must be lowercase (only all-capital acronyms keep capitals)")
        if k not in entries:
            errs.append(f"glossary form '{f}' -> '{k}': no such entry")

    stories = news.get("stories")
    if not DATE.match(str(news.get("updated", ""))):
        errs.append("news.json: 'updated' must be YYYY-MM-DD")
    if not isinstance(stories, list) or not stories:
        errs.append("news.json: 'stories' must be a non-empty list")
        stories = []
    if len(stories) > MAX_STORIES:
        errs.append(f"news.json: {len(stories)} stories; keep at most {MAX_STORIES} (drop the oldest editions)")
    seen_ids, seen_urls = set(), set()
    for st in stories:
        sid = st.get("id", "?")
        where = f"story '{sid}'"
        if not SLUG.match(str(sid)):
            errs.append(f"{where}: id must be a lowercase slug like 2026-10-09-short-topic")
        if sid in seen_ids:
            errs.append(f"{where}: duplicate id")
        seen_ids.add(sid)
        url = str(st.get("url", ""))
        if not url.startswith("https://"):
            errs.append(f"{where}: url must start with https://")
        if url in seen_urls:
            errs.append(f"{where}: duplicate url (same article twice)")
        seen_urls.add(url)
        for f in ("edition", "date"):
            v = str(st.get(f, ""))
            if not DATE.match(v):
                errs.append(f"{where}: {f} must be YYYY-MM-DD")
            else:
                try:
                    date.fromisoformat(v)
                except ValueError:
                    errs.append(f"{where}: {f} is not a real date")
        if not isinstance(st.get("rank"), int):
            errs.append(f"{where}: rank must be a whole number (1 = top story of its edition)")
        if st.get("tag") not in TAGS:
            errs.append(f"{where}: tag must be one of {sorted(TAGS)}")
        for f in ("title", "source", "place"):
            if not isinstance(st.get(f), str) or not st.get(f).strip():
                errs.append(f"{where}: '{f}' must be a non-empty string")
        summ, why = st.get("summary"), st.get("why", [])
        if not isinstance(summ, list) or not 2 <= len(summ) <= 4 or not all(isinstance(x, str) and x.strip() for x in summ):
            errs.append(f"{where}: summary must be a list of 2-4 sentences")
        if not isinstance(why, list) or len(why) > 3 or not all(isinstance(x, str) and x.strip() for x in why):
            errs.append(f"{where}: why must be a list of 0-3 sentences")
        kws = st.get("keywords")
        if not isinstance(kws, list) or not 3 <= len(kws) <= 6:
            errs.append(f"{where}: keywords must list 3-6 glossary keys")
            kws = []
        for k in kws:
            e = entries.get(k)
            if not e:
                errs.append(f"{where}: key word '{k}' has no glossary entry")
            elif not e.get("key"):
                errs.append(f"{where}: key word '{k}' needs a rich entry (\"key\": true, jaKanji, ex)")
        for f, k in (st.get("senses") or {}).items():
            if k not in entries:
                errs.append(f"{where}: sense '{f}' -> '{k}': no such entry")
        for s in sentences(st):
            for t in tokens(s):
                if not needs_entry(t):
                    continue
                if story_lookup(glossary, st, t) is None:
                    missing.append({"form": t if is_acronym(t) else norm(t), "sentence": s, "story": sid})

    if want_missing:
        uniq, out = set(), []
        for m in missing:
            if m["form"] not in uniq:
                uniq.add(m["form"])
                out.append(m)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    if missing:
        words = sorted({m["form"] for m in missing})
        errs.append(f"{len(words)} story word(s) have no glossary entry: {', '.join(words[:60])}"
                    + (" ..." if len(words) > 60 else "") + "  (run with --missing for details)")
    if errs:
        print(f"FAIL: {len(errs)} problem(s)")
        print("\n".join(errs[:120]))
        sys.exit(1)
    for w in warns[:30]:
        print("WARN:", w)
    if len(warns) > 30:
        print(f"WARN: ... {len(warns) - 30} more")
    print(f"OK: {len(stories)} stories, {len(entries)} glossary entries, {len(forms)} forms; every story word is covered."
          + (f" {len(warns)} warning(s)." if warns else ""))


if __name__ == "__main__":
    main()
