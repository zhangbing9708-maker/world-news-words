# World News Words

**Live site: https://zhangbing9708-maker.github.io/world-news-words/**

Read today's world news in plain English and learn its words in **Japanese, English or Farsi**.

- **News** – short summaries of the day's top stories, with links to the original reports. Tap any word
  to see it in the language you're learning, with its reading or pronunciation, meaning and, for key
  words, an example sentence.
- **Words** – words you add become flashcards with Anki-style spaced repetition (Again / Hard / Good /
  Easy). Export them to Anki, or save a backup to move them to another device.

## Many people, one site

Each visitor's saved words are stored in their own browser (`localStorage`), so people never see or
change each other's words. There are no accounts and nothing personal is sent anywhere. The trade-off:
words stay on that one browser and device. Use **Save backup** / **Load backup** on the Words tab to
move them.

## How the news is updated

A scheduled Claude task runs every morning (Perth time). It finds the latest world news, writes new
learner summaries, adds translations for any new words to `data/glossary.json`, runs
`tools/check_data.py`, and pushes the change here. GitHub Pages then republishes the site.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The whole app (no build step) |
| `data/news.json` | Stories, newest edition first |
| `data/glossary.json` | Every tappable word in Japanese, Farsi and English |
| `tools/check_data.py` | Validates the data; `--missing` lists words without translations |
| `tools/wordlib.py` | Word rules shared with the app (tokenizer, lookup) |
| `DATA_FORMAT.md` | Format and translation rules for the data |
