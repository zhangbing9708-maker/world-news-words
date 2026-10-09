# World News Words

**Live site: https://zhangbing9708-maker.github.io/world-news-words/**

Read today's world news in plain English and learn its words in **Japanese, Chinese, English or Farsi**.

- **News** – short summaries of the day's top stories, with links to the original reports. Tap any word
  to see it in the language you're learning, with its reading or pronunciation, meaning and, for key
  words, an example sentence.
- **Words** – words you add become flashcards with Anki-style spaced repetition (Again / Hard / Good /
  Easy). Sign in with Google to keep them in your own Google Drive and load them on any device, export
  them to Anki, or save a backup file.
- **ABC** – reference tables for Japanese hiragana and katakana, Chinese pinyin (tones, initials,
  finals), the English alphabet and the Persian alphabet (with each letter's joined forms), with example
  words and tap-to-listen.

Sound: Japanese, Chinese and English use the device's own voices. Most devices have no Persian voice, so
Farsi words, example sentences and alphabet examples play recorded MP3 files made with an open-source
Persian voice (Piper "gyro", run with sherpa-onnx) by `tools/make_audio.py`.

## Many people, one site

Each visitor's saved words are stored in their own browser (`localStorage`), so people never see or
change each other's words. The site has no server and no accounts of its own.

**Google Drive sync (optional).** On the Words tab, **Sign in with Google** saves the words to one file in
that person's own Google Drive, "World News Words – my words.json", and loads it on any device where they
sign in. The site asks only for the `drive.file` permission, so it can open nothing in Drive except the
file it made. Sign-in uses Google Identity Services in the browser (an access token that lasts about an
hour and is kept only in memory); syncing merges by card, so the newest review of each word wins and
deleted words stay deleted. A signed-in person's words are kept under their own storage key prefix, so two
people sharing one browser never mix words, and signing out removes the copy from the device once it is
safely in Drive. The OAuth client is a public web client ID (no secret) in the `world-news-words` Google
Cloud project; its authorised JavaScript origin is `https://zhangbing9708-maker.github.io`. See
[privacy.html](privacy.html).

Without signing in, use **Save backup** / **Load backup** to move words between devices.

## How the news is updated

A scheduled Claude task runs every morning (Perth time). It finds the latest world news, writes new
learner summaries, adds Japanese, Chinese, Farsi and English entries for any new words to
`data/glossary.json`, makes their Farsi audio with `tools/make_audio.py`, runs `tools/check_data.py`, and
pushes the change here. GitHub Pages then republishes the site.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The whole app (no build step) |
| `privacy.html` | Privacy policy (linked from the Google sign-in screen) |
| `data/news.json` | Stories, newest edition first |
| `data/glossary.json` | Every tappable word in Japanese, Chinese, Farsi and English |
| `data/alphabets.json` | The ABC tab's reference tables |
| `data/audio/fa/` | Recorded Farsi audio (MP3) |
| `tools/make_audio.py` | Makes Farsi audio for new words |
| `tools/check_data.py` | Validates the data; `--missing` lists words without translations |
| `tools/wordlib.py` | Word rules shared with the app (tokenizer, lookup) |
| `DATA_FORMAT.md` | Format and translation rules for the data |
