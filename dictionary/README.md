# Persian Core Vocabulary — searchable frequency dictionary

A static website for searching and exploring the 5,000 words of
*A Frequency Dictionary of Persian: Core Vocabulary for Learners*
(Corey Miller & Karineh Aghajanian-Stewart, Routledge, 2018), rebuilt from the book's PDF.

Nothing was added, corrected or translated: every headword, pronunciation, gloss,
part of speech, example sentence, translation and frequency figure is the book's own text.

## Using it

* **Online:** enable GitHub Pages for this repository (Settings → Pages → *Deploy from a branch* →
  branch `main`, folder `/ (root)` → Save). The site is then served at
  `https://<user>.github.io/<repo>/`. On a free GitHub plan Pages is only available for public
  repositories; a private repository needs GitHub Pro (the published site is public either way).
* **Offline:** download the repository and open `index.html` in a browser. Everything is
  self-contained (`data/data.js` holds the dictionary); only the web fonts come from Google Fonts
  and the page falls back to system fonts without them.

Search accepts Persian script, rough transliteration (`khane`, `shodan`, `ghermez`), IPA (`xɑne`),
English (`house`) or a rank number (`128`). Filters: part of speech, rank range, thematic list;
sorting by rank, Persian alphabet, raw frequency, dispersion or English gloss. Click an entry for
its dispersion code, raw count, thematic lists, part-of-speech-specific glosses, book page and
neighbours by rank. The address bar keeps the current search (`#q=…&pos=…&w=…`) so a view can be
bookmarked or shared.

## Files

| File | Contents |
|---|---|
| `index.html`, `style.css`, `app.js` | the site (no build step, no dependencies) |
| `data/data.js` | compact payload loaded by the site |
| `data/dictionary.txt` | the whole frequency index, thematic lists and part-of-speech index as plain text |
| `data/entries.tsv` | the 5,000 main entries, one per line (tab-separated) |
| `data/thematic_lists.tsv` | the 31 thematic lists (2,003 words) |
| `data/pos_index.tsv` | the part-of-speech index (6,337 lines) |
| `data/dictionary.json` | everything above with field documentation in `meta` |
| `tools/` | the extraction and validation scripts used to produce the data |

### Entry fields

`rank` · `headword` · `ipa` (pronunciation, Iranian Persian) · `gloss` (commas separate senses; a slash
separates glosses sharing one pronunciation) · `pos` (`adj adv conj n prep pron pn q v`) ·
`example_fa` / `example_en` · `dp` (dispersion code 38–97, 100·e^−DP; near 100 = spread evenly
through the corpus) · `raw` (count of the word family in the 150-million-word corpus) · `book_page` ·
`lists` (thematic list numbers) · `pos_glosses` (gloss given in the part-of-speech index).

## How the text was extracted

The PDF's text layer stores right-to-left text in visual (left-to-right) order and `pdftotext`
garbles it: the لا ligature comes out reversed, sentence punctuation and digits move, and the
thematic boxes get interleaved with entries. The scripts in `tools/` therefore read glyph positions
with `pdfplumber` and rebuild each line themselves:

* Persian runs are taken in content-stream order (which is the visual order), reversed, and
  left-to-right islands (numbers, Latin words) are restored; ZWNJ — stored in the PDF as a
  zero-advance space glyph — is put back.
* Fields are separated by the book's fonts (bold Times for headwords, Times for IPA, italic Trade
  Gothic for glosses, upright Trade Gothic for parts of speech) with fallbacks for the places where the
  book's typesetting slips between fonts.
* Validation: all 5,000 ranks are present and consecutive; every entry has every field (rank 21 has no
  dispersion/raw line in the book); each entry was cross-checked against an independent `pdftotext`
  extraction (character multisets of headword and example, numbers, English text) and the alphabetical
  and part-of-speech indexes were cross-checked against the main list (headword per rank; section
  counts equal the counts printed in the book); samples were compared against the page images.

### Quirks of the printed book, kept as printed

* Rank 21 (بر) has no dispersion / raw-frequency line.
* The part of speech printed for rank 870 (خانم) is `N`, and for rank 3889 (ریز) `ad`; `pos_tags`
  normalises these to `n` / `adj`, `pos` keeps the printed form.
* The part-of-speech index lists ranks 3193 and 3536 without the initial به (رسمیت شناختن, ثمر رساندن);
  the main entries read به رسمیت شناختن and به ثمر رساندن.
* The thematic list *Colors* prints the pronunciation of rank 16359 as `xormgji`.
* The alphabetical index prints rank 1417 as عباالله (the main list has عبدالله); the alphabetical index is
  not published here, it was used only for cross-checking.
* Spelling variants inside the corpus sentences (Arabic ي/ك, inconsistent spaces and ZWNJ) are the
  book's; search normalises them.
* In rank 462's example the order of the two Latin aircraft names next to an Arabic comma
  (`SR-71،F-117`) is the reading that reproduces the printed line under the Unicode bidirectional
  algorithm; the printed page itself is ambiguous.

## Copyright

The dictionary content is © 2018 Corey Miller and Karineh Aghajanian-Stewart / Routledge, all rights
reserved, extracted here for personal study. The site code (`index.html`, `style.css`, `app.js`,
`tools/`) may be reused freely.
