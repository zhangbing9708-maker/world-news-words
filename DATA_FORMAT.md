# Data format

The site reads `data/news.json` (the stories), `data/glossary.json` (every tappable word in Japanese,
Chinese, Farsi and English), `data/alphabets.json` (the ABC tab) and `data/audio/fa/*.mp3` (Farsi audio).

After any change to the data:

1. `python3 tools/check_data.py --missing` lists story words that still need a glossary entry.
2. `python3 tools/make_audio.py` makes Farsi audio for every new entry and writes the audio ids back into
   the JSON (it downloads an open-source Persian voice from GitHub the first time). Commit the new
   `data/audio/fa/*.mp3` files together with the JSON.
3. `python3 tools/check_data.py` must print `OK` before anything is committed. Warnings (for example a
   missing audio file) do not block publishing, but should be fixed.

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
Person, company and place names get entries too.

### Basic entry (every word)

```json
"inflation": {
  "t": "inflation",
  "pos": "noun",
  "def": "a general rise in prices over time",
  "ipa": "/ɪnˈfleɪʃn/",
  "ja": { "w": "インフレ", "k": "インフレ", "r": "infure" },
  "zh": { "w": "通货膨胀", "p": "tōnghuò péngzhàng" },
  "fa": { "w": "تورم", "r": "tavarrom", "v": "تَوَرّم", "a": "<written by make_audio.py>" }
}
```

- **key**: lowercase English dictionary form (`search`, `japan`, `end up`, `united states`). Sense-specific
  keys use `#` (`share` = a part, `share#stock` = company shares); point a story's `senses` at them.
- **t**: the headword as displayed (capitals for names and acronyms: `Japan`, `WHO`, `Wall Street`).
- **pos**: one of `noun`, `verb`, `adjective`, `adverb`, `preposition`, `conjunction`, `pronoun`,
  `determiner`, `number`, `phrase`, `proper noun`, `abbreviation`.
- **def**: plain English for a learner, at most 10 words, for the sense used in the story. Verbs start
  with "to ...". Proper nouns say what they are ("country in northern Europe").
- **ipa**: British dictionary-style IPA between slashes, with stress marks.

**Japanese (`ja`)**: `w` the natural word a Japanese news article would use (verbs in dictionary form,
する-verbs with する, な-adjectives with な); `k` the full reading in kana only; `r` Hepburn romaji with
macrons (ō, ū; katakana ー becomes a macron). Foreign names in katakana, Japanese places in kanji.

**Chinese (`zh`)**: `w` Simplified Chinese (Mainland standard), the natural word a Chinese news article
would use for this sense; names in the standard Xinhua transliteration (`泽连斯基`). `p` Hanyu Pinyin with
tone marks, syllables of one word written together, words separated by spaces, apostrophe before a/o/e
syllables inside a word (`Xī'ān`), neutral tone unmarked, proper nouns capitalised.

**Farsi (`fa`)**: `w` standard Iranian Persian in Persian letters (`ی` and `ک`, never Arabic `ي` `ك`), ZWNJ
where Persian uses it, verbs in the infinitive. `r` lowercase Latin transliteration: `ā` long a, `a`,
`e`, `o` short vowels, `u` and `i` long vowels, `kh` خ, `gh` غ/ق, `sh` ش, `ch` چ, `zh` ژ, `'` for ع/ء,
ezafe as `-e`/`-ye`. `v` the same letters with vowel marks so the speech voice says the word like `r`
(fatha ـَ a, kasra ـِ e, damma ـُ o, tashdid ـّ doubled consonant). Rules learned from the voice:
add marks only (removing them must give `w`); put the tashdid **before** a vowel mark on the same
letter; never put a kasra on the letter before a final silent ه. `a` is filled in by `make_audio.py`.

### Rich entry (story key words)

Everything above, plus:

```json
"key": true,
"jaKanji": [ {"c": "原", "m": "origin"} ],
"zhChars": [ {"c": "通", "m": "through"}, {"c": "货", "m": "goods"} ],
"ex": {
  "en": "High oil prices can push up inflation.",
  "ja": "原油[げんゆ]の値段[ねだん]が高[たか]いとインフレが進[すす]む。",
  "zh": "油价高会推高通货膨胀。",
  "zhP": "yóujià gāo huì tuīgāo tōnghuò péngzhàng.",
  "fa": "قیمت بالای نفت می‌تواند تورم را بالا ببرد.",
  "faR": "gheymat-e bālā-ye naft mi-tavānad tavarrom rā bālā bebarad.",
  "faV": "<ex.fa with vowel marks, same rules as fa.v>",
  "faA": "<written by make_audio.py>"
}
```

- `jaKanji` / `zhChars`: one `{c, m}` per kanji of `ja.w` / Chinese character of `zh.w`, in order
  (meaning in 1-3 English words); `[]` when there are none.
- `ex.en`: one short, natural sentence (at most 12 words) on the story's topic, not copied from the story.
- `ex.ja`: Japanese translation with the reading in brackets after every run of kanji: `原油[げんゆ]`.
- `ex.zh` + `ex.zhP`: Chinese translation and its pinyin (words separated by spaces, Chinese punctuation).
- `ex.fa` + `ex.faR` + `ex.faV`: Persian translation, its transliteration, and the vowel-marked version.

## alphabets.json

Reference data for the ABC tab: `ja` (kana tables), `en` (letters and letter teams), `fa` (the 32 letters
with their four joined forms, and vowels), `zh` (tones, initials, finals). Each language has `name`,
`intro`, `sections` (`id`, `title`, `note`, `cols`, `cells`, with `null` for an empty slot) and `tips`.
Farsi example words carry `v` (vowel-marked, for the voice) and `a` (audio id from `make_audio.py`).
This file rarely changes; the daily update leaves it alone.
