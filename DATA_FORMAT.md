# Data format

The site teaches Farsi from English news. It reads `data/news.json` (the stories), `data/glossary.json`
(every tappable word, in English and Farsi), `data/dict.json` and `data/dict-examples.json` (the frequency
dictionary: ranks, categories, examples), `data/alphabets.json` (the Persian alphabet on the Dictionary tab),
`data/grammar.json` (the Grammar tab's sentence patterns) and `data/audio/fa/*.mp3` (recorded Farsi audio).

After any change to the data:

1. `python3 tools/check_data.py --missing` lists story words that still need a glossary entry.
2. `python3 tools/make_audio.py` makes Farsi audio for every new entry (glossary, alphabet, dictionary and
   grammar) and writes the audio ids back into the JSON (it downloads an open-source Persian voice from GitHub the
   first time). Commit the new `data/audio/fa/*.mp3` files together with the JSON.
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
"ex": {
  "en": "High oil prices can push up inflation.",
  "fa": "قیمت بالای نفت می‌تواند تورم را بالا ببرد.",
  "faR": "gheymat-e bālā-ye naft mi-tavānad tavarrom rā bālā bebarad.",
  "faV": "<ex.fa with vowel marks, same rules as fa.v>",
  "faA": "<written by make_audio.py>"
}
```

- `ex.en`: one short, natural sentence (at most 12 words) on the story's topic, not copied from the story.
- `ex.fa` + `ex.faR` + `ex.faV`: Persian translation, its transliteration, and the vowel-marked version.

## dict.json and dict-examples.json

Built by `python3 tools/build_dict.py` from `dictionary/dictionary.json`; never edited by hand, and the
weekly news update leaves them alone. `dict.json`:

```json
{ "source": "...", "lists": [ {"n": 1, "t": "Animals"} ],
  "cats": [ {"id": "x-num", "t": "Numbers & amounts", "ranks": [12, 20]} ],
  "entries": [ {"n": 1275, "w": "غذا", "r": "ghazā", "i": "ɣæzɑ", "g": "food", "p": "n", "l": [10],
                "v": "غَذا", "a": "<audio id>", "d": 80, "c": 1234} ] }
```

- `n` rank (1–5,000 from the book's frequency index; list-only words keep the book's rank above 5,000 and
  carry `"x": true`), `w` headword, `r` the site's transliteration and `v` the vowel-marked spelling (both
  made from the IPA `i` by `tools/vowelize.py`), `g` the book's gloss, `p` parts of speech
  (`adj adv conj n prep pron pn q v`, comma-separated), `l` thematic list numbers, `a` audio id (from
  `make_audio.py`), `d` dispersion, `c` raw count.
- Levels are rank bands: 1–1,000 Beginner, 1,001–3,000 Intermediate, 3,001–5,000 Advanced, else "5,000+".
- `dict-examples.json` maps a rank to `[example_fa, example_en]` and is loaded only when a word is opened.
- The site links each glossary entry to a dictionary word by the normalised Farsi headword (`fa.w`), or
  the main word of a phrase; so keep `fa.w` in the dictionary's spelling (infinitives for verbs, ZWNJ
  where Persian uses it) to get the right rank and level in the news.

## alphabets.json

Reference data for the alphabet view on the Dictionary tab: `fa` holds the 32 Persian letters (with their four joined forms) and the
vowels, as `name`, `intro`, `sections` (`id`, `title`, `note`, `cols`, `cells`, with `null` for an empty slot)
and `tips`. Example words carry `v` (vowel-marked, for the voice) and `a` (audio id from `make_audio.py`).
This file rarely changes; the daily update leaves it alone.

## grammar.json

The Grammar tab: the basic sentence patterns of Persian school grammar (two-, three- and four-part sentences)
next to their English counterparts. It is written by hand and kept indented for editing; the weekly news
update leaves it alone.

- `intro`, `roles` (`k`, `en`, `fa`, `r`, `about`), `compare` (`s`, `note`), `patterns` (`n`, `name`, `fa`, `r`,
  `kind`, `order` and `en`: the roles in Farsi and in English order, `note`, `ex`), `detail` (`title`, `text`,
  `steps`, `note`), `features` (`title`, `text`, `ex`, optional `table` with `title` and `rows`), `practice`
  (`pattern`, `s`, optional `alt`: other accepted orders as lists of part indexes) and `source`.
- Roles: `S` subject (نهاد), `O` object (مفعول), `C` complement (مسند), `M` preposition phrase the verb needs
  (متمم), `A` adverbial (قید), `V` verb (فعل).
- A sentence: `fa` (plain Persian, with ZWNJ), `faV` (the same letters with vowel marks, for the voice; no kasra
  before a final silent ه), `r` (transliteration in the site's style), `en`, `p` (parts in Farsi order:
  `[role, Persian, transliteration, English gloss, dictionary headword]`; joined with spaces they must spell
  `fa` without its final full stop), `e` (English parts `[role, text]`) and `a` (audio id). Phrases and the
  rows of a table have no parts.
- After changing any `faV`, run `python3 tools/make_audio.py`: `tools/check_data.py` fails while a recording
  is out of date. `make_audio.py` rewrites the file only when an audio id changes.

## Older data

Until October 2026 the site also taught Japanese, Chinese and English, and every entry carried `ja`, `zh`,
`jaKanji`, `zhChars` and Japanese/Chinese example sentences. Those fields are no longer written or read
(`tools/check_data.py` rejects them); the git history still has them.
