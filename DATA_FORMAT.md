# Data format

The site reads two files: `data/news.json` (the stories) and `data/glossary.json` (every tappable word
in Japanese, Farsi and English). Run `python3 tools/check_data.py` after any change; it must print `OK`
before the change is committed. `python3 tools/check_data.py --missing` lists story words that still
need a glossary entry.

## news.json

```json
{
  "updated": "2026-10-09",
  "stories": [
    {
      "id": "2026-10-08-short-topic-slug",
      "edition": "2026-10-09",
      "rank": 1,
      "date": "2026-10-08",
      "tag": "World",
      "place": "Ukraine",
      "source": "ABC News",
      "url": "https://...",
      "title": "Plain-English headline",
      "summary": ["2-4 short sentences"],
      "why": ["0-3 sentences of background: why it matters"],
      "keywords": ["five", "glossary", "keys"],
      "senses": {"work": "work#writing"}
    }
  ]
}
```

- `edition`: the day the story was added (the daily update's date, Perth time). The page groups stories
  by edition, newest first, and orders each edition by `rank` (1 = top story).
- `date`: when the source published it. `tag`: one of World, Politics, Business, Health, Science,
  Technology, Environment, Culture, Sport.
- `summary` and `why` are original, plain English (about B1-B2 level), neutral and factual, with numbers
  and names from the source. Never copy sentences from the source.
- `keywords`: 3-6 glossary keys; each must be a rich entry (see below).
- `senses` (optional): when a word in this story needs a different sense from the global `forms`
  mapping, map the word (lowercase, as written) to a sense-specific entry key such as `work#writing`.
- Keep at most 60 stories: drop the oldest editions first.

## glossary.json

```json
{ "updated": "2026-10-09", "entries": { "<key>": { ... } }, "forms": { "<surface form>": "<key>" } }
```

The glossary only grows: keep old entries even after their stories are gone. Every word in every story
(except a few function words such as "the", "of", "and"; see `tools/wordlib.py`) must resolve to an entry
through `forms`, a story's `senses`, or the plural/possessive fallbacks in `tools/wordlib.py`.
Person, company and place names get entries too (katakana and Persian spellings help learners).

Sense-specific keys use `#`: `share` (a part) and `share#stock` (company shares). Point a story's `senses`
at the right one when a word is ambiguous.

## Basic entry (every word)

```json
"search": {
  "t": "search",
  "pos": "verb",
  "def": "to look carefully for something",
  "ipa": "/sɜːtʃ/",
  "ja": { "w": "探す", "k": "さがす", "r": "sagasu" },
  "fa": { "w": "جستجو کردن", "r": "jostoju kardan" }
}
```

- **key**: lowercase English dictionary form (`search`, `bee`, `japan`, `end up`, `united states`).
- **t**: the headword as displayed (capitals for names and acronyms: `Japan`, `WHO`, `Wall Street`).
- **pos**: one of `noun`, `verb`, `adjective`, `adverb`, `preposition`, `conjunction`, `pronoun`,
  `determiner`, `number`, `phrase`, `proper noun`, `abbreviation`.
- **def**: plain English for a learner, at most 10 words, for the sense used in the given sentence.
  Verbs start with "to ...". Proper nouns say what they are ("country in northern Europe").
- **ipa**: British dictionary-style IPA between slashes, with stress marks: `/ˈæltɪtjuːd/`.

### Japanese (`ja`)
- `w`: the natural, common word a Japanese news article would use for this sense.
  Nouns as nouns; verbs in dictionary form, する-verbs with する (`調査する`); い-adjectives in
  dictionary form (`高い`); な-adjectives with な (`静かな`).
- `k`: full reading in hiragana (katakana for katakana words). Kana only, no kanji, no romaji.
- `r`: Hepburn romaji, lowercase, macrons for long vowels: し=shi, ち=chi, つ=tsu, ふ=fu, じ=ji,
  おう/おお=ō, うう=ū, えい=ei, ん=n. Katakana long marks ー become macrons (`ニュース` = `nyūsu`).
- Proper nouns: the standard Japanese name (katakana for foreign places; kanji for Japanese places
  such as `福島`, and for China/Taiwan/Korea places normally written in kanji such as `北京`).

### Farsi (`fa`)
- Standard Iranian Persian (Farsi), not Arabic or Dari. Persian letters only (`ی` not `ي`, `ک` not `ك`).
- Use ZWNJ (U+200C) where Persian normally does: `می‌کند`, `خانه‌ها`.
- Verbs in the infinitive (`جستجو کردن`); nouns singular; adjectives in base form.
- Proper nouns: the usual Persian spelling used by BBC Persian (`ژاپن`, `اوکراین`, `کرملین`).
- `r`: lowercase Latin transliteration: `ā` = آ / long a, `a` short a, `e` short e, `o` short o,
  `u` long u, `i` long i, `kh` = خ, `gh` = غ and ق, `sh` = ش, `ch` = چ, `zh` = ژ, `'` for ع / ء when
  pronounced, ezafe as `-e` / `-ye`. Examples: زنبور عسل = `zanbur-e asal`, ارتفاع = `ertefā'`.

## forms

Map **every** surface form you were given, exactly as listed, to the key that covers it, even when
the form equals the key. Inflections map to the base entry (`killing` → `kill`, `buses` → `bus`,
`rose` → `rise`, `japan's` → `japan`, `28-year-old` → `year-old`).

- Forms are lowercase, **except all-capital acronyms**, which are listed in capitals and must be
  mapped in capitals: `"US": "united states"`, `"WHO": "world health organization"`, `"AI": "ai"`,
  `"ID": "id card"` (or `"id"`), `"G7": "g7"`.

### Phrases
When a word is part of a real fixed expression in its sentence (phrasal verb such as `shut down`,
compound noun such as `bond yield`, `per cent`, `health care`, multi-word name such as
`strait of hormuz`, `wall street`, `world health organization`), also add a phrase entry and map the
phrase as written (lowercase) to it, e.g. `"shut down": "shut down"`, `"per cent": "per cent"`.
Still map each single token to a single-word entry (`shut` → `shut`, `down` → `down`), except that
single words of a multi-word proper name map to the name's entry (`hormuz` → `strait of hormuz`,
`kalimantan` → `west kalimantan`).

### Sense
Choose the sense used in the sentence (news). "a Russian strike on a bus stop" → military attack
(攻撃 / حمله), not a workers' strike. "shares slipped" → company shares (株 / سهام).

## Rich entry (story key words only)

Key-word entries have everything a basic entry has, plus `jaKanji` and `ex`, and `"key": true`:

```json
"inflation": {
  "t": "inflation",
  "pos": "noun",
  "def": "a general rise in prices over time",
  "ipa": "/ɪnˈfleɪʃn/",
  "ja": { "w": "インフレ", "k": "インフレ", "r": "infure" },
  "fa": { "w": "تورم", "r": "tavarrom" },
  "jaKanji": [],
  "ex": {
    "en": "High oil prices can push up inflation.",
    "ja": "原油[げんゆ]の値段[ねだん]が高[たか]いとインフレが進[すす]む。",
    "fa": "قیمت بالای نفت می‌تواند تورم را بالا ببرد.",
    "faR": "gheymat-e bālā-ye naft mi-tavānad tavarrom rā bālā bebarad."
  },
  "key": true
}
```

- `jaKanji`: one `{ "c": kanji, "m": core meaning in 1-3 English words }` for each kanji in `ja.w`,
  in order; `[]` when there are none.
- `ex.en`: one short, natural English sentence (at most 12 words) using the word in the same sense,
  on the story's topic but **not copied** from the story.
- `ex.ja`: natural Japanese translation that uses `ja.w`. Put the hiragana reading in square
  brackets right after **every** run of kanji: `原油[げんゆ]の値段[ねだん]`. No brackets after kana.
- `ex.fa`: natural Persian translation that uses `fa.w` (or its correct inflected form).
- `ex.faR`: transliteration of `ex.fa` using the same scheme as `fa.r`.
- Map the key word's own forms in `forms` (e.g. `"wounding": "wound"`, `"front line": "front line"`).
