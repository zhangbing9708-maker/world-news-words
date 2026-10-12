#!/usr/bin/env python3
"""Extract the 5,000 entries of the main frequency index from
'A Frequency Dictionary of Persian' (Routledge 2018) using glyph positions.

The PDF text layer stores right-to-left text in visual (left-to-right) order.
We rebuild logical order ourselves so that:
  * the لا ligature (one glyph whose text is 'لا') stays intact,
  * sentence punctuation ends up at the end of the sentence,
  * digit / Latin islands inside Persian text keep their own order,
  * ZWNJ (stored as a zero-advance space glyph) is restored.

usage: extract_freq.py persian.pdf out.json
"""
import json
import re
import sys

import pdfplumber

PDF = sys.argv[1]
OUT = sys.argv[2]
FIRST_PAGE, LAST_PAGE = 19, 279          # 1-indexed PDF pages of the frequency index
HEADER_Y = 50                            # running head ("Frequency index 9") sits above this
LINE_TOL = 3.2

DIGITS = set('0123456789۰۱۲۳۴۵۶۷۸۹'
             '٠١٢٣٤٥٦٧٨٩')
POS_RE = r'(?:adj|adv|conj|n|prep|pron|pn|q|v|N|ad|expression)(?:,\s*(?:adj|adv|conj|n|prep|pron|pn|q|v))*'


def fshort(f):
    f = f.split('+')[-1]
    return (f.replace('TradeGothicLTStd', 'TG')
             .replace('TimesNewRomanPS', 'TNR')
             .replace('TimesNewRoman', 'TNR'))


def fclass(c):
    f = fshort(c['fontname'])
    if f == 'TG-Bold':
        return 'rank'
    if f.startswith('TNR-Bold'):
        return 'fa-bold'
    if f.startswith('TNR'):
        return 'tnr'
    if f == 'TG-LightObl':
        return 'gloss'
    if f == 'TG-Light':
        return 'en'
    if f.startswith('Symbol'):
        return 'sym'
    return 'other'


def is_arabic(ch):
    return ('؀' <= ch <= 'ۿ' or 'ݐ' <= ch <= 'ݿ'
            or 'ﭐ' <= ch <= '﷿' or 'ﹰ' <= ch <= '﻿')


def is_latin(ch):
    return ch.isalpha() and not is_arabic(ch)


ISLAND_RE = re.compile(r"[A-Za-z0-9\u06f0-\u06f9\u0660-\u0669]+(?:[.,:/\-'\u2019%\u060c\u066b\u066c][A-Za-z0-9\u06f0-\u06f9\u0660-\u0669]+)*")


def fix_islands(s):
    """After a naive full reversal of an RTL visual run, left-to-right islands
    (numbers, Latin words) are themselves reversed; put them back."""
    spans = [(m.start(), m.end()) for m in ISLAND_RE.finditer(s)]
    merged = []
    for st, en in spans:
        if merged:
            pst, pen = merged[-1]
            if st == pen + 1 and s[pen] == ' ' and any(is_latin(ch) for ch in s[pst:pen]) \
                    and any(is_latin(ch) for ch in s[st:en]):
                merged[-1] = (pst, en)
                continue
        merged.append((st, en))
    out = list(s)
    for st, en in merged:
        out[st:en] = reversed(out[st:en])
    return ''.join(out)


def visual_to_logical(glyphs, rank=None):
    """glyphs: the char dicts of one right-to-left run on one line.

    The content stream emits the run's glyphs in visual (left-to-right) order,
    which is more reliable than sorting by x0 (justified lines overlap glyphs
    slightly, and combining marks are drawn before their base).  Glyphs from
    other fonts (quotation marks set in the Latin font) are merged in by x."""
    core = [g for g in glyphs if fclass(g) in ('tnr', 'fa-bold')]
    if not core:
        return ''
    cx0, cx1 = min(g['x0'] for g in core), max(g['x1'] for g in core)
    # a ZWNJ is a zero-advance space glyph that may come from the Latin font;
    # keep such spaces (inside the run's extent) in stream order with the run
    main = sorted([g for g in glyphs if fclass(g) in ('tnr', 'fa-bold')
                   or (g['text'] == ' ' and cx0 + 0.5 < g['x0'] < cx1 - 0.5)], key=lambda g: g['idx'])
    for a, b in zip(main, main[1:]):
        tol = 6.0 if (a['x1'] - a['x0'] < 0.01 or '\u064b' <= a['text'][0] <= '\u065f') else 2.0
        if b['x0'] < a['x0'] - tol:
            warn(f"rank {rank}: stream order not visual ({a['text']!r}@{a['x0']:.1f} -> {b['text']!r}@{b['x0']:.1f}); using x-sort")
            main = sorted(main, key=lambda g: (g['x0'], g['idx']))
            break
    seq = list(main)
    for g in sorted([g for g in glyphs if g not in main], key=lambda g: g['x0']):
        pos = next((i for i, h in enumerate(seq) if h['x0'] > g['x0'] + 0.3), len(seq))
        seq.insert(pos, g)
    texts = []
    for i, g in enumerate(seq):
        t = g['text']
        if t == ' ' and i + 1 < len(seq) and seq[i + 1]['x0'] - g['x0'] < 0.6:
            t = '\u200c'  # zero-advance space glyph => ZWNJ (ActualText in the PDF)
        texts.append(t)
    s = ''.join(reversed(texts))
    s = fix_islands(s)
    return s.strip()


def ltr_text(glyphs):
    return ''.join(g['text'] for g in glyphs)


def group_lines(chars, tol=LINE_TOL):
    chars = sorted(chars, key=lambda c: (c['top'], c['x0'], c['idx']))
    lines = []
    for c in chars:
        if lines and c['top'] - lines[-1]['ref'] <= tol:
            lines[-1]['chars'].append(c)
        else:
            lines.append({'ref': c['top'], 'chars': [c]})
    for ln in lines:
        ln['chars'].sort(key=lambda c: (c['x0'], c['idx']))
        ln['top'] = min(c['top'] for c in ln['chars'])
    return lines


def classify_line(ln):
    cs = ln['chars']
    nonspace = [c for c in cs if c['text'].strip()]
    if not nonspace:
        return 'blank'
    first = nonspace[0]
    if fclass(first) == 'rank' and first['text'] in DIGITS:
        return 'header'
    if fclass(first) == 'sym' and first['text'] == '•':
        return 'bullet'
    txt = ''.join(c['text'] for c in cs).strip()
    if all(fclass(c) in ('en', 'sym') for c in nonspace):
        if re.fullmatch(r'\d+(?:\s*\|\s*|\s+)\d+\.?', txt):
            return 'dp'
        if txt == '|':
            return 'pipe'
    return 'cont'


warnings = []


def warn(msg):
    warnings.append(msg)


def parse_header(ln, entry):
    cs = ln['chars']
    i = 0
    while i < len(cs) and not cs[i]['text'].strip():
        i += 1
    rank = ''
    while i < len(cs) and fclass(cs[i]) == 'rank' and (cs[i]['text'] in DIGITS or cs[i]['text'] == ' '):
        rank += cs[i]['text']
        i += 1
    entry['rank'] = int(rank.strip())
    rest = cs[i:]
    arabic = [c for c in rest if any(is_arabic(ch) for ch in c['text'])]
    if not arabic:
        warn(f"rank {entry['rank']}: no Arabic headword glyphs")
        entry['headword'] = ''
        entry['_hruns'] = [(c['text'], fclass(c)) for c in rest]
        return
    bx0, bx1 = min(c['x0'] for c in arabic), max(c['x1'] for c in arabic)
    head = [c for c in rest if c['x0'] >= bx0 - 0.1 and c['x1'] <= bx1 + 0.1]
    odd = [c for c in head if fclass(c) != 'fa-bold' and c['text'].strip()]
    if odd:
        warn(f"rank {entry['rank']}: non-bold glyph inside headword: {[(c['text'], fshort(c['fontname'])) for c in odd]}")
    nonar = [c for c in head if c['text'].strip() and not any(is_arabic(ch) for ch in c['text'])]
    if nonar:
        warn(f"rank {entry['rank']}: non-Arabic glyph inside headword span: {[(c['text'], fshort(c['fontname'])) for c in nonar]}")
    before = [c for c in rest if c['x1'] <= bx0 + 0.1 and c['text'].strip() and c['x1'] - c['x0'] > 0.01]
    if before:
        warn(f"rank {entry['rank']}: glyphs between rank and headword: {[(c['text'], fshort(c['fontname'])) for c in before]}")
    entry['headword'] = visual_to_logical(head, entry['rank'])
    entry['_hruns'] = [(c['text'], fclass(c)) for c in rest if c['x0'] >= bx1 - 0.1 and c not in head]


def parse_head_cont(ln, entry):
    cs = ln['chars']
    odd = [c for c in cs if fclass(c) not in ('tnr', 'gloss', 'en') and c['text'].strip()]
    if odd:
        warn(f"rank {entry['rank']}: unexpected glyphs in header continuation: {[(c['text'], fshort(c['fontname'])) for c in odd]}")
    if any(is_arabic(ch) for c in cs for ch in c['text']):
        warn(f"rank {entry['rank']}: Arabic text in header continuation: {ltr_text(cs)!r}")
    entry['_hruns'].append((' ', 'nl'))
    entry['_hruns'] += [(c['text'], fclass(c)) for c in cs]


def parse_example_line(ln, entry):
    cs = [c for c in ln['chars'] if not (fclass(c) == 'sym' and c['text'] == '•')]
    arabic = [c for c in cs if any(is_arabic(ch) for ch in c['text'])]
    last_ar_x1 = max(c['x1'] for c in arabic) if arabic else None
    dash_idx = None
    for i, c in enumerate(cs):
        if c['text'] == '—' and (last_ar_x1 is None or c['x0'] >= last_ar_x1 - 0.5):
            dash_idx = i
            break
    if dash_idx is not None:
        fa_glyphs, en_glyphs = cs[:dash_idx], cs[dash_idx + 1:]
    elif arabic:
        fa_glyphs, en_glyphs = cs, []
    else:
        fa_glyphs, en_glyphs = [], cs
    while fa_glyphs and not fa_glyphs[0]['text'].strip():
        fa_glyphs = fa_glyphs[1:]
    while fa_glyphs and not fa_glyphs[-1]['text'].strip():
        fa_glyphs = fa_glyphs[:-1]
    if fa_glyphs:
        odd = [c for c in fa_glyphs if fclass(c) != 'tnr' and c['text'].strip()]
        if any(c['text'].isalnum() for c in odd):
            warn(f"rank {entry['rank']}: non-Times alphanumerics inside Persian run: {[(c['text'], fshort(c['fontname'])) for c in odd]}")
        fa = visual_to_logical(fa_glyphs, entry['rank'])
        if any(is_latin(ch) for ch in fa) or '%' in fa:
            warn(f"rank {entry['rank']}: Latin/percent inside Persian example (check island order): {fa}")
        entry['_fa_parts'].append(fa)
    if en_glyphs:
        odd = [c for c in en_glyphs if fclass(c) not in ('en', 'gloss') and c['text'].strip()]
        if odd:
            warn(f"rank {entry['rank']}: unexpected glyphs in English translation: {[(c['text'], fshort(c['fontname'])) for c in odd]}")
        t = ltr_text(en_glyphs).strip()
        if t:
            entry['_en_parts'].append(t)


def split_header_runs(entry):
    """Turn the glyph runs after the headword into ipa / gloss / pos.

    Normally: IPA is set in Times, the gloss in italic Trade Gothic and the
    POS in upright Trade Gothic.  The book is not always consistent, so the
    split is done on the text in reading order with the fonts as hints.
    """
    runs = entry.pop('_hruns')
    merged = []
    for t, f in runs:
        if merged and merged[-1][1] == f:
            merged[-1][0] += t
        else:
            merged.append([t, f])
    full = ''.join(t for t, f in merged)
    full = re.sub(r'\s+', ' ', full).strip()
    m = re.search(r'(?:^|\s)(' + POS_RE + r')\s*$', full)
    if m:
        pos = m.group(1)
        head = full[:m.start()].strip()
    else:
        pos = ''
        head = full
        warn(f"rank {entry['rank']}: no POS found in header text {full!r}")
    # IPA = leading Times run, extended over comma-separated pronunciations
    # that were (mis)typeset in another font
    ipa = ''
    i = 0
    if merged and merged[0][1] != 'tnr' and len(merged) > 1 and merged[1][1] == 'tnr' \
            and not merged[0][0].endswith(' ') and merged[0][0].strip().isalpha():
        ipa += merged[0][0]
        i = 1
    def looks_ipa(tok):
        return any(ch in '\u00e6\u0251\u0283\u0292\u0294\u0241\u0263\u02a4\u02a7\u0261' for ch in tok)

    while i < len(merged):
        t, f = merged[i]
        if f == 'tnr':
            ipa += t
            i += 1
            continue
        if f == 'nl':
            i += 1
            continue
        stripped = t.strip()
        if not stripped:
            nxt = merged[i + 1] if i + 1 < len(merged) else None
            if nxt and (nxt[1] == 'tnr' or ipa.rstrip().endswith(',')
                        or (nxt[1] == 'en' and looks_ipa(nxt[0].split()[0] if nxt[0].split() else ''))):
                ipa += ' '
                i += 1
                continue
            break
        if stripped == ',':
            ipa += ','
            i += 1
            continue
        mm = re.match(r'\s*([^\s,]+)(,?)', t)
        if mm and not any(ch.isupper() for ch in mm.group(1)) and \
                (ipa.rstrip().endswith(',') or (f == 'en' and looks_ipa(mm.group(1)))):
            ipa += ' ' + mm.group(1) + mm.group(2)
            rest = t[mm.end():]
            merged[i][0] = rest
            if not rest.strip():
                i += 1
            continue
        break
    ipa = re.sub(r'\s+', ' ', ipa).strip()
    ipa = re.sub(r'\s*,\s*', ', ', ipa)
    gloss_raw = ''.join(t for t, f in merged[i:])
    gloss_raw = re.sub(r'\s+', ' ', gloss_raw).strip()
    if pos:
        gm = re.search(r'(?:^|\s)' + re.escape(pos) + r'\s*$', gloss_raw)
        if gm:
            gloss_raw = gloss_raw[:gm.start()].strip()
        elif re.search(r'(?:^|\s)' + POS_RE + r'\s*$', gloss_raw):
            gloss_raw = re.sub(r'(?:^|\s)' + POS_RE + r'\s*$', '', gloss_raw).strip()
    gloss = gloss_raw.replace('ɡ', 'g')      # IPA g glyph used inside an English word
    gloss = re.sub(r'\s*,\s*', ', ', gloss)
    gloss = re.sub(r'\s*/\s*', '/', gloss)
    if ')' in gloss and '(' in gloss and gloss.index(')') < gloss.index('('):
        gloss = gloss.translate(str.maketrans('()', ')('))
    if gloss.count('(') == 2 and gloss.count(')') == 0:
        k = gloss.index('(', gloss.index('(') + 1)
        gloss = gloss[:k] + ')' + gloss[k + 1:]
    if '(' in gloss or ')' in gloss:
        gloss = re.sub(r'\(\s*', '(', gloss)
        gloss = re.sub(r'\s*\)', ')', gloss)
        if gloss.count('(') != gloss.count(')'):
            warn(f"rank {entry['rank']}: unbalanced parentheses in gloss {gloss!r}")
    entry['ipa'] = ipa
    entry['gloss'] = gloss.strip(' ,')
    entry['pos'] = re.sub(r'\s+', '', pos)
    if not ipa or not gloss:
        warn(f"rank {entry['rank']}: empty ipa/gloss from header text {full!r}")
    if any(ch.isupper() and ch != '\u0241' for ch in ipa) or any(is_arabic(ch) for ch in ipa):
        warn(f"rank {entry['rank']}: suspicious IPA {ipa!r} from {full!r}")
    fonts = {f for t, f in merged if t.strip()}
    if 'en' in fonts:
        en_text = ''.join(t for t, f in merged if f == 'en').strip(' ,')
        if en_text not in (pos, ''):
            warn(f"rank {entry['rank']}: mixed fonts in header: {[(t, f) for t, f in merged if t.strip()]} -> ipa={ipa!r} gloss={gloss!r} pos={pos!r}")


def finish_entry(entry):
    if entry is None:
        return None
    split_header_runs(entry)
    fa = ' '.join(p for p in entry.pop('_fa_parts') if p)
    en_parts = entry.pop('_en_parts')
    en = ' '.join(p for p in en_parts if p)
    en = re.sub(r'^[—–-]\s*', '', en).strip()
    en = re.sub(r'\s+', ' ', en)
    if '—' in en:
        warn(f"rank {entry['rank']}: dash remaining inside English translation: {en}")
    entry['example_fa'] = fa
    entry['example_en'] = en
    for k in ('headword', 'ipa', 'gloss', 'pos', 'example_fa', 'example_en'):
        if not entry.get(k):
            warn(f"rank {entry['rank']}: missing {k}")
    if 'dp' not in entry:
        warn(f"rank {entry['rank']}: missing dp/raw")
        entry['dp'] = None
        entry['raw'] = None
    return entry


def page_boxes(page):
    boxes = []
    for r in list(page.rects) + list(page.curves):
        if (r['x1'] - r['x0']) > 300 and (r['bottom'] - r['top']) > 40:
            boxes.append((r['top'] - 1, r['bottom'] + 1))
    merged = []
    for bt, bb in sorted(boxes):
        if merged and bt <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], bb))
        else:
            merged.append((bt, bb))
    return merged


def main():
    entries = []
    boxes_found = []
    with pdfplumber.open(PDF) as pdf:
        entry = None
        state = None
        for pno in range(FIRST_PAGE, LAST_PAGE + 1):
            page = pdf.pages[pno - 1]
            chars = [dict(c, idx=i) for i, c in enumerate(page.chars)]
            chars = [c for c in chars if c['top'] > HEADER_Y]
            if pno == FIRST_PAGE:
                chars = [c for c in chars if c['top'] > 132]  # title + key box
            boxes = page_boxes(page) if pno != FIRST_PAGE else []
            for (bt, bb) in boxes:
                boxes_found.append((pno, bt, bb))

            def in_box(c):
                return any(bt <= c['top'] <= bb for (bt, bb) in boxes)

            body = [c for c in chars if not in_box(c)]
            right_ranks = [c['x0'] for c in body if fclass(c) == 'rank' and c['text'] in DIGITS and c['x0'] > 150]
            split = (min(right_ranks) - 1.5) if right_ranks else 10000
            cols = [[c for c in body if c['x0'] < split],
                    [c for c in body if c['x0'] >= split]]
            for ci, col in enumerate(cols):
                for ln in group_lines(col):
                    kind = classify_line(ln)
                    if kind in ('blank', 'pipe'):
                        continue
                    if kind == 'header':
                        if entry:
                            entries.append(finish_entry(entry))
                        entry = {'_fa_parts': [], '_en_parts': [], 'page': pno, 'book_page': pno - 11}
                        parse_header(ln, entry)
                        state = 'head'
                    elif kind == 'bullet':
                        if entry is None:
                            warn(f"p{pno} col{ci}: bullet before any entry: {ltr_text(ln['chars'])!r}")
                            continue
                        state = 'ex'
                        parse_example_line(ln, entry)
                    elif kind == 'dp':
                        txt = ''.join(c['text'] for c in ln['chars']).strip()
                        m = re.fullmatch(r'(\d+)(?:\s*\|\s*|\s+)(\d+)\.?', txt)
                        if entry is None:
                            warn(f"p{pno}: dp line before any entry: {txt}")
                            continue
                        if 'dp' in entry:
                            warn(f"rank {entry['rank']}: second dp line {txt}")
                        entry['dp'] = int(m.group(1))
                        entry['raw'] = int(m.group(2))
                        state = 'done'
                    else:
                        if entry is None:
                            warn(f"p{pno} col{ci}: stray line before any entry: {ltr_text(ln['chars']).strip()!r}")
                            continue
                        if state == 'head':
                            parse_head_cont(ln, entry)
                        elif state == 'ex':
                            parse_example_line(ln, entry)
                        else:
                            txt = ltr_text(ln['chars']).strip()
                            warn(f"rank {entry['rank']} p{pno}: text after dp line: {txt!r}")
        entries.append(finish_entry(entry))
    entries = [e for e in entries if e]
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)
    with open(OUT + '.warnings.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(warnings))
    with open(OUT + '.boxes.json', 'w') as f:
        json.dump(boxes_found, f)
    print(f"entries: {len(entries)}  warnings: {len(warnings)}  boxes: {len(boxes_found)}")
    ranks = [e['rank'] for e in entries]
    missing = sorted(set(range(1, 5001)) - set(ranks))
    dups = sorted({r for r in ranks if ranks.count(r) > 1})
    print("missing ranks:", missing[:50], "count", len(missing))
    print("duplicate ranks:", dups[:50])
    bad_order = [(a, b) for a, b in zip(ranks, ranks[1:]) if b != a + 1]
    print("non-consecutive:", bad_order[:20])


if __name__ == '__main__':
    main()
