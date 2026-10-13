"""Check World News Words data (English news, Farsi words) before publishing.

usage:
  python3 tools/check_data.py            validate data/news.json and data/glossary.json
  python3 tools/check_data.py --missing  print (as JSON) every story word that has no glossary entry

Exit code 1 means something must be fixed before committing.
"""
import hashlib
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
PERSIAN = re.compile(r"^[؀-ۿ‌‏\s\-]+$")
PERSIAN_SENT = re.compile(r"^[؀-ۿ‌‏\s\-.,،؛؟!«»:0-9۰-۹()$%]+$")
ARABIC_ONLY = re.compile(r"[يك]")
LATIN = re.compile(r"^[a-zāīūēō' \-]+$")
LATIN_SENT = re.compile(r"^[A-Za-zāīūēōĀĪŪ' \-.,?!:;0-9()$%]+$")
HARAKAT = re.compile(r"[\u064B-\u0652\u0670]")
AUDIO_DIR = os.path.join(ROOT, "data", "audio", "fa")
ALPHABETS = os.path.join(ROOT, "data", "alphabets.json")
DICT = os.path.join(ROOT, "data", "dict.json")
GRAMMAR = os.path.join(ROOT, "data", "grammar.json")
ROLES = {"S", "O", "C", "M", "A", "V"}


def has_audio(i):
    return bool(i) and os.path.exists(os.path.join(AUDIO_DIR, str(i) + ".mp3"))


def spoken_id(text):
    """The audio id tools/make_audio.py gives a text (a hash of what the voice is asked to say)."""
    t = re.sub(r"\s+", " ", str(text or "").replace("ـ", "")).strip()
    return hashlib.sha1(t.encode("utf-8")).hexdigest()[:12]


def check_grammar(g, errs, warns):
    """data/grammar.json (the Grammar tab): every example's parts spell its sentence, roles are known,
    the vowel-marked text has the same letters, and its recording is there and up to date."""
    def sentence(s, where, parts=True):
        if not isinstance(s, dict) or not all(isinstance(s.get(k), str) and s.get(k).strip() for k in ("fa", "faV", "r", "en")):
            errs.append(f"grammar.json {where}: needs fa, faV, r and en")
            return
        if ARABIC_ONLY.search(s["fa"]):
            errs.append(f"grammar.json {where}: use Persian ی and ک in {s['fa']!r}")
        if HARAKAT.sub("", s["faV"]) != HARAKAT.sub("", s["fa"]):
            errs.append(f"grammar.json {where}: faV has different letters from fa ({s['faV']!r} / {s['fa']!r})")
        if not s.get("a"):
            warns.append(f"grammar.json {where}: no audio (run python3 tools/make_audio.py)")
        elif s["a"] != spoken_id(s["faV"]):
            errs.append(f"grammar.json {where}: the recording is for an older faV (run python3 tools/make_audio.py)")
        elif not has_audio(s["a"]):
            warns.append(f"grammar.json {where}: audio file {s['a']}.mp3 is missing (run python3 tools/make_audio.py)")
        p = s.get("p")
        if not parts:
            return
        if not isinstance(p, list) or not p:
            errs.append(f"grammar.json {where}: no parts (p)")
            return
        for x in p:
            if not (isinstance(x, list) and len(x) in (4, 5) and x[0] in ROLES and all(isinstance(v, str) and v for v in x[1:])):
                errs.append(f"grammar.json {where}: bad part {x!r}")
                return
        if " ".join(x[1] for x in p) != re.sub(r"[.؟?!]$", "", s["fa"]):
            errs.append(f"grammar.json {where}: the parts don't spell {s['fa']!r}")
        for x in s.get("e") or []:
            if not (isinstance(x, list) and len(x) == 2 and x[0] in ROLES and isinstance(x[1], str) and x[1]):
                errs.append(f"grammar.json {where}: bad English part {x!r}")
    pats = g.get("patterns") or []
    if len(pats) < 6:
        errs.append(f"grammar.json: {len(pats)} patterns (expected the 6–7 basic sentence patterns)")
    for r in g.get("roles") or []:
        if r.get("k") not in ROLES:
            errs.append(f"grammar.json: unknown role {r.get('k')!r}")
    sentence((g.get("compare") or {}).get("s"), "compare")
    for pt in pats:
        where = f"pattern {pt.get('n')}"
        if not pt.get("name") or not all(k in ROLES for k in (pt.get("order") or ["?"]) + (pt.get("en") or ["?"])):
            errs.append(f"grammar.json {where}: needs a name and role orders (order, en)")
        if not pt.get("ex"):
            errs.append(f"grammar.json {where}: no examples")
        for i, s in enumerate(pt.get("ex") or []):
            sentence(s, f"{where} example {i + 1}")
    for i, s in enumerate((g.get("detail") or {}).get("steps") or []):
        sentence(s, f"detail step {i + 1}")
    for f in g.get("features") or []:
        for i, s in enumerate(f.get("ex") or []):
            sentence(s, f"feature '{f.get('title')}' example {i + 1}", parts=bool(isinstance(s, dict) and s.get("p")))
        for i, s in enumerate((f.get("table") or {}).get("rows") or []):
            sentence(s, f"feature '{f.get('title')}' table row {i + 1}", parts=False)
    for i, q in enumerate(g.get("practice") or []):
        s = q.get("s")
        sentence(s, f"practice {i + 1}")
        n = len((s or {}).get("p") or [])
        for alt in q.get("alt") or []:
            if sorted(alt) != list(range(n)):
                errs.append(f"grammar.json practice {i + 1}: alternative order {alt} is not an order of its {n} parts")


def check_entry(k, e, errs, warns=None):
    warns = warns if warns is not None else []
    where = f"glossary entry '{k}'"
    if k != k.lower():
        errs.append(f"{where}: key must be lowercase")
    for f in ("t", "pos", "def", "ipa", "fa"):
        if f not in e:
            errs.append(f"{where}: missing '{f}'")
    for f in ("ja", "zh", "jaKanji", "zhChars"):
        if f in e:
            errs.append(f"{where}: '{f}' is not used any more (the site teaches Farsi only); leave it out")
    if e.get("pos") not in POS:
        errs.append(f"{where}: pos '{e.get('pos')}' not allowed")
    ipa = str(e.get("ipa", ""))
    if not (ipa.startswith("/") and ipa.endswith("/") and len(ipa) > 2):
        errs.append(f"{where}: ipa must be /.../")
    fa = e.get("fa") or {}
    if not PERSIAN.match(str(fa.get("w", ""))) or ARABIC_ONLY.search(str(fa.get("w", ""))):
        errs.append(f"{where}: fa.w must be Persian script (ی and ک): {fa.get('w')!r}")
    if not LATIN.match(str(fa.get("r", ""))):
        errs.append(f"{where}: fa.r bad transliteration: {fa.get('r')!r}")
    if fa.get("v") and HARAKAT.sub("", fa["v"]) != HARAKAT.sub("", str(fa.get("w", ""))):
        errs.append(f"{where}: fa.v must be fa.w plus vowel marks only")
    if not fa.get("v"):
        warns.append(f"{where}: no fa.v (vowel-marked spelling for the audio)")
    if not has_audio(fa.get("a")):
        warns.append(f"{where}: no Farsi audio (run python3 tools/make_audio.py)")
    if e.get("key"):
        ex = e.get("ex") or {}
        for f in ("en", "fa", "faR"):
            if not ex.get(f):
                errs.append(f"{where}: ex.{f} missing")
        for f in ("ja", "zh", "zhP"):
            if f in ex:
                errs.append(f"{where}: ex.{f} is not used any more; leave it out")
        if not PERSIAN_SENT.match(str(ex.get("fa", ""))) or ARABIC_ONLY.search(str(ex.get("fa", ""))):
            errs.append(f"{where}: ex.fa must be Persian script: {ex.get('fa')!r}")
        if not LATIN_SENT.match(str(ex.get("faR", ""))):
            errs.append(f"{where}: ex.faR bad transliteration: {ex.get('faR')!r}")
        if ex.get("faV") and HARAKAT.sub("", ex["faV"]) != HARAKAT.sub("", str(ex.get("fa", ""))):
            errs.append(f"{where}: ex.faV must be ex.fa plus vowel marks only")
        if not ex.get("faV"):
            warns.append(f"{where}: no ex.faV (vowel-marked example for the audio)")
        if not has_audio(ex.get("faA")):
            warns.append(f"{where}: no Farsi audio for the example (run python3 tools/make_audio.py)")


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
            if not isinstance(alpha.get("fa"), dict) or not alpha["fa"].get("sections"):
                errs.append("alphabets.json: 'fa' missing")
            for l in sorted(set(alpha) - {"fa"}):
                errs.append(f"alphabets.json: '{l}' is not used any more (the site teaches Farsi only)")
            for sec in (alpha.get("fa") or {}).get("sections", []):
                for c in sec.get("cells", []):
                    if c and not has_audio((c.get("ex") or {}).get("a")):
                        warns.append(f"alphabets.json: no audio for Farsi example {(c.get('ex') or {}).get('w')!r}")
        except ValueError as ex:
            errs.append(f"alphabets.json: not valid JSON ({ex})")
    if os.path.exists(DICT):
        try:
            dct = json.load(open(DICT, encoding="utf-8"))
            ents = dct.get("entries") or []
            if len(ents) < 5000:
                errs.append(f"dict.json: only {len(ents)} words (expected the 5,000 of the frequency dictionary); run tools/build_dict.py")
            ranks = set()
            for e in ents:
                if not all(isinstance(e.get(k), str) and e.get(k) for k in ("w", "r", "g")) or not isinstance(e.get("n"), int):
                    errs.append(f"dict.json: bad entry {str(e)[:60]}")
                    break
                if e["n"] in ranks:
                    errs.append(f"dict.json: rank {e['n']} appears twice")
                ranks.add(e["n"])
            no_audio = sum(1 for e in ents if not has_audio(e.get("a")))
            if no_audio:
                warns.append(f"dict.json: {no_audio} words have no audio (run python3 tools/make_audio.py)")
            if not dct.get("lists") or not dct.get("cats"):
                errs.append("dict.json: lists or cats missing; run tools/build_dict.py")
        except ValueError as ex:
            errs.append(f"dict.json: not valid JSON ({ex})")
    else:
        errs.append("data/dict.json is missing; run python3 tools/build_dict.py")
    if os.path.exists(GRAMMAR):
        try:
            check_grammar(json.load(open(GRAMMAR, encoding="utf-8")), errs, warns)
        except ValueError as ex:
            errs.append(f"grammar.json: not valid JSON ({ex})")
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
                errs.append(f"{where}: key word '{k}' needs a rich entry (\"key\": true and an ex example)")
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
