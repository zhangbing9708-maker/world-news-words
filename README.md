# World News Words

**Live site: https://zhangbing9708-maker.github.io/world-news-words/**

Read the week's world news in plain English and learn its words in **Farsi (Persian)**, with a weekly plan built
around the 5,000 most common Persian words.

- **Today** – your plan: pick a level (Beginner, Intermediate, Advanced: how many words a day and which
  frequency band), a category of words for the week (the dictionary's 31 thematic lists, or site-made ones
  such as Numbers & amounts), and a few interests. Each week gets a day's worth of words from your
  category for every day, preferring words that appear in the current news. The day then reads top to
  bottom like a worksheet:
  1. **Today's reading** – the two stories that use the most of today's words (then the rest of the week's),
     with only this week's words underlined and numbered to match the vocabulary list, plus each of today's
     words in a real Persian sentence from the dictionary.
  2. **Vocabulary** – today's words, numbered, then any other words of the week the stories use.
  3. **Practice** – the daily challenge (meaning, Farsi and listening questions, which tracks what you've
     learned and your streak) and three exercises with answers to reveal: match the words, write them in
     Farsi, and complete the dictionary's sentences (from the middle of the week these review earlier days).

  At the bottom, **Print or save as PDF** makes a practice sheet in the same order, with the answers on the
  last page. The plan and progress are saved with your Google sign-in.
- **News** – short summaries of the week's top stories, with links to the original reports. Every story
  shows a level from how common its words are, and the words of this week's plan are underlined.
  Tap any word to see it in Farsi with its transliteration, meaning, rank, recorded pronunciation and, for
  key words, an example sentence.
- **Words** – words you add become flashcards with Anki-style spaced repetition (Again / Hard / Good /
  Easy). Sign in with Google to keep them in your own Google Drive and load them on any device, export
  them to Anki, or save a backup file.
- **Dictionary** – search the 5,000 words of *A Frequency Dictionary of Persian* (Persian script, rough
  spelling, English or rank), filter by category, level and part of speech, hear each word, read the book's
  example sentence and add words to your flashcards. The Persian alphabet (32 letters with their joined
  forms, the vowels, example words) lives here too.
- **Grammar** – how Farsi sentences are built. Persian school grammar sorts simple sentences by how many
  parts the verb needs (two, three or four), giving seven basic patterns that line up with English's.
  Each pattern shows its Farsi and English word order and example sentences with every part in its role's
  colour (subject, object, complement, preposition phrase, adverbial, verb), a word-by-word gloss,
  transliteration and recorded audio; tap a part to open its word in the dictionary. Then where time and
  place go, notes on dropped subjects, را, questions, negation, ezafe and compound verbs, and a practice
  that has you tap the words of a sentence into Farsi order.

Sound: most devices have no Persian voice, so every dictionary word, news word, example sentence,
grammar example and alphabet example plays a recorded MP3 made with an open-source Persian voice (Piper "gyro", run with
sherpa-onnx) by `tools/make_audio.py`. Dictionary words are vowel-marked from their IPA by
`tools/vowelize.py` so the voice reads them correctly.

Until October 2026 the site also taught Japanese, Chinese and English; that version is in the git history.
Words saved in those languages stay in people's browsers, backups and Drive files, but are no longer shown.

## The frequency dictionary

`dictionary/dictionary.json` is the data of the
[persian-frequency-dictionary](https://github.com/zhangbing9708-maker/persian-frequency-dictionary) project,
now merged into this repo: the 5,000 entries of *A Frequency Dictionary of Persian: Core Vocabulary for
Learners* (Corey Miller & Karineh Aghajanian-Stewart, Routledge, 2018) with rank, headword, IPA, gloss,
part of speech, example sentence, dispersion and raw count, plus the book's 31 thematic lists (which also
name 573 words beyond rank 5,000). `dictionary/tools/` holds the scripts that extracted it from the book's
PDF, and `dictionary/README.md` the notes on that extraction.

`tools/build_dict.py` turns it into what the site loads: `data/dict.json` (every word with the site's
transliteration, vowel-marked spelling, audio id, lists, and four site-made categories: Numbers & amounts,
Little words, Adverbs, Adjectives) and `data/dict-examples.json` (the example sentences, loaded on
demand). Levels are rank bands: 1–1,000 Beginner, 1,001–3,000 Intermediate, 3,001–5,000 Advanced, and
"5,000+" for everything rarer. News words are linked to the dictionary by their Farsi headword (or the main
word of a phrase), which covers about 84% of them; the rest count as 5,000+.

The dictionary content is © 2018 the authors / Routledge, extracted for personal study; the site code and
tools may be reused freely.

## Many people, one site

Each visitor's saved words are stored in their own browser (`localStorage`), so people never see or
change each other's words. The site has no server and no accounts of its own.

**Google Drive sync (optional).** On the Words tab, **Sign in with Google** saves the words to one file in
that person's own Google Drive, "World News Words – my words.json", and loads it on any device where they
sign in; the same file carries the person's plan (level, category, interests) and challenge progress. The
site asks only for the `drive.file` permission, so it can open nothing in Drive except the file it made. Sign-in uses Google Identity Services in the browser (an access token that lasts about an
hour and is kept only in memory); syncing merges by card, so the newest review of each word wins and
deleted words stay deleted. A signed-in person's words are kept under their own storage key prefix, so two
people sharing one browser never mix words, and signing out removes the copy from the device once it is
safely in Drive. The OAuth client is a public web client ID (no secret) in the `world-news-words` Google
Cloud project; its authorised JavaScript origin is `https://zhangbing9708-maker.github.io`. See
[privacy.html](privacy.html).

Without signing in, use **Save backup** / **Load backup** to move words between devices.

## Export to Anki

**Export to Anki** on the Words tab makes an Anki deck file (`.apkg`), built in the browser: a small Anki
collection made with [sql.js](https://github.com/sql-js/sql.js) (SQLite in WebAssembly, in `lib/`) and
zipped with the recorded Farsi MP3s from `data/audio/fa/`. Each word becomes a note in the deck
"World News Words::Farsi" with its transliteration, meaning, example sentence, audio and the news sentence it
came from. Cards follow the **Card front** choice (Farsi first, or English first). Note ids are stable, so
importing a newer export updates earlier cards instead of duplicating them, and Anki keeps its own review
history. If the browser can't run WebAssembly, the button falls back to a tab-separated text file for Anki's
**File → Import**.

## How the news is updated

A scheduled Claude task runs every Monday morning (Perth time). It finds the week's most important world
news, writes 12–14 learner summaries spread across the site's topics (so every learner's interests find a
match), adds English and Farsi entries for any new words to `data/glossary.json`, makes their Farsi audio
with `tools/make_audio.py`, runs `tools/check_data.py`, and pushes the change here. GitHub Pages then
republishes the site, and each person's device builds their plan for the week from it.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The whole app (no build step) |
| `privacy.html` | Privacy policy (linked from the Google sign-in screen) |
| `data/news.json` | Stories, newest edition first |
| `data/glossary.json` | Every tappable news word, in English and Farsi |
| `data/dict.json`, `data/dict-examples.json` | The frequency dictionary as the site loads it (built by `tools/build_dict.py`) |
| `data/alphabets.json` | The Persian alphabet for the Dictionary tab |
| `data/grammar.json` | The Grammar tab: sentence patterns, examples and practice (written by hand) |
| `data/audio/fa/` | Recorded Farsi audio (MP3) for dictionary words, news words and examples |
| `dictionary/` | The dictionary's source data, extraction scripts and notes |
| `lib/` | sql.js 1.13.0 (MIT licence, see `lib/sql.js-LICENSE.txt`), used only for the Anki export |
| `tools/build_dict.py` | Builds `data/dict.json` from `dictionary/dictionary.json` |
| `tools/vowelize.py` | Vowel marks and transliteration for a Persian word from its IPA |
| `tools/make_audio.py` | Makes Farsi audio for new words |
| `tools/check_data.py` | Validates the data; `--missing` lists words without an entry |
| `tools/wordlib.py` | Word rules shared with the app (tokenizer, lookup) |
| `DATA_FORMAT.md` | Format and translation rules for the data |
