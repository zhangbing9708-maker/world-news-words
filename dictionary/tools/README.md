# Extraction scripts

Requires Python 3 with `pdfplumber` and poppler's `pdftotext` (for the cross-check only).

```
python3 extract_freq.py     persian.pdf work/freq.json
python3 extract_boxes.py    persian.pdf work/boxes.json
python3 extract_indexes.py  persian.pdf work/alpha.json work/pos.json work/freq.json
python3 validate_freq.py    persian.pdf work/freq.json        # cross-check against pdftotext
python3 build_data.py       work/freq.json work/boxes.json work/pos.json ../data
```

`persian.pdf` is the book's PDF (not included). Each extractor writes a `*.warnings.txt`
next to its output listing anything it had to work around.
