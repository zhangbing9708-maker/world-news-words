"""Build the site's dictionary files from the frequency dictionary.

usage:  python3 tools/build_dict.py

Reads dictionary/dictionary.json (the 5,000 words of "A Frequency Dictionary of Persian", Routledge
2018, as extracted in the persian-frequency-dictionary project) and writes:

  data/dict.json           the words the site loads at start: rank, headword, the site's transliteration,
                           IPA, English meaning, parts of speech, thematic lists, dispersion, raw count,
                           the vowel-marked spelling for the voice (v) and, once make_audio.py has run,
                           the audio id (a). Also the 31 book lists and a few site-made categories.
                           The thematic lists name 573 more words beyond rank 5,000 (onion, flour, grape);
                           they are included too, marked "x": true, with their list rank and no example.
  data/dict-examples.json  the book's example sentence for each rank, loaded only when needed.

Audio ids already in data/dict.json are kept, so this script can be re-run after make_audio.py.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vowelize import vowelize  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "dictionary", "dictionary.json")
OUT = os.path.join(ROOT, "data", "dict.json")
OUT_EX = os.path.join(ROOT, "data", "dict-examples.json")
MAX_COST = 2.0          # alignments that had to guess this much are left without marks

NUMBER_GLOSS = re.compile(
    r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
    r"seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|"
    r"million|billion|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|half|quarter|dozen|"
    r"percent|zero|digit|number|amount|count|several|few|many|much|all|some|most|every|each|both|none|"
    r"majority|minority|minimum|maximum|at least|approximately|pair|couple|total|whole)\b", re.I)


def main():
    src = json.load(open(SOURCE, encoding="utf-8"))
    old = {}
    if os.path.exists(OUT):
        try:
            for e in json.load(open(OUT, encoding="utf-8")).get("entries", []):
                old[e["n"]] = e
        except ValueError:
            pass
    entries, examples, unmarked = [], {}, []
    for e in src["entries"]:
        v, r, cost = vowelize(e["headword"], e["ipa"])
        if cost >= MAX_COST:
            unmarked.append((e["rank"], e["headword"], e["ipa"], round(cost, 1)))
            v = e["headword"]
        tags = e.get("pos_tags") or [t.strip() for t in str(e.get("pos", "")).split(",") if t.strip()]
        o = {"n": e["rank"], "w": e["headword"].strip(), "r": r, "i": e["ipa"], "g": e["gloss"], "p": ",".join(tags),
             "l": list(e.get("lists") or [])}
        if v != o["w"]:
            o["v"] = v
        if e.get("dp") is not None:
            o["d"] = e["dp"]
        if e.get("raw") is not None:
            o["c"] = e["raw"]
        prev = old.get(e["rank"])
        if prev and prev.get("a") and prev.get("v", prev.get("w")) == o.get("v", o["w"]):
            o["a"] = prev["a"]
        entries.append(o)
        if e.get("example_fa"):
            examples[str(e["rank"])] = [e["example_fa"], e.get("example_en", "")]

    # words that appear only in the thematic lists (ranked beyond 5,000)
    by_rank = {o["n"]: o for o in entries}
    extra = {}
    for L in src["lists"]:
        for w in L["words"]:
            r = w.get("rank")
            if not isinstance(r, int) or r <= 5000:
                if isinstance(r, int) and r in by_rank and L["num"] not in by_rank[r]["l"]:
                    by_rank[r]["l"].append(L["num"])
                continue
            o = extra.get(r)
            if not o:
                v, tr, cost = vowelize(w["headword"], w["ipa"])
                if cost >= MAX_COST:
                    unmarked.append((r, w["headword"], w["ipa"], round(cost, 1)))
                    v = w["headword"]
                o = extra[r] = {"n": r, "w": w["headword"].strip(), "r": tr, "i": w["ipa"], "g": w["gloss"], "p": "", "l": [], "x": True}
                if v != o["w"]:
                    o["v"] = v
                prev = old.get(r)
                if prev and prev.get("a") and prev.get("v", prev.get("w")) == o.get("v", o["w"]):
                    o["a"] = prev["a"]
            if L["num"] not in o["l"]:
                o["l"].append(L["num"])
    entries.extend(sorted(extra.values(), key=lambda o: o["n"]))

    lists = [{"n": L["num"], "t": L["title"]} for L in src["lists"]]
    by_tags = lambda want: [o["n"] for o in entries if set(o["p"].split(",")) & want]
    cats = [
        {"id": "x-num", "t": "Numbers & amounts", "ranks": sorted({o["n"] for o in entries if "q" in o["p"].split(",") or NUMBER_GLOSS.search(o["g"])})},
        {"id": "x-fn", "t": "Little words", "note": "prepositions, conjunctions and pronouns", "ranks": by_tags({"prep", "conj", "pron"})},
        {"id": "x-adv", "t": "Adverbs", "ranks": by_tags({"adv"})},
        {"id": "x-adj", "t": "Adjectives", "ranks": [o["n"] for o in entries if o["p"] == "adj"]},
    ]
    out = {"source": src["meta"]["source"], "lists": lists, "cats": cats, "entries": entries}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump(examples, open(OUT_EX, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    with_audio = sum(1 for o in entries if o.get("a"))
    print(f"dict.json: {len(entries)} words ({len(extra)} from the lists beyond 5,000), {len(lists)} book lists, {len(cats)} site-made categories "
          f"({', '.join(c['t'] + ' ' + str(len(c['ranks'])) for c in cats)}), {with_audio} with audio; "
          f"{len(unmarked)} words left without vowel marks.")
    for u in unmarked:
        print("  unmarked:", *u)
    print(f"dict-examples.json: {len(examples)} examples; sizes {os.path.getsize(OUT) / 1e6:.2f} MB + {os.path.getsize(OUT_EX) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
