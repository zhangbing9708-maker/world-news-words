#!/usr/bin/env python3
"""Extract the alphabetical index (PDF pp. 280-327) and the part-of-speech index (pp. 328-377)."""
import json
import re
import sys

import pdfplumber

sys.path.insert(0, __file__.rsplit('/', 1)[0])
import extract_freq as X  # noqa: E402

PDF, OUT_ALPHA, OUT_POS, MAIN_JSON = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
MAIN = {e['rank']: e['headword'] for e in json.load(open(MAIN_JSON, encoding='utf-8'))}
ALPHA_PAGES = range(280, 328)
POS_PAGES = range(328, 378)
warnings = []


def column_groups(chars, splits):
    cols = [[] for _ in range(len(splits) + 1)]
    for c in chars:
        k = sum(1 for s in splits if c['x0'] >= s)
        cols[k].append(c)
    return cols


def parse_index_line(ln, kind):
    """Return dict with keys head(glyphs), ipa, gloss, pos, rank, is_new."""
    cs = ln['chars']
    arabic = [c for c in cs if any(X.is_arabic(ch) for ch in c['text'])]
    rec = {'head': [], 'ipa': '', 'gloss': '', 'pos': '', 'rank': None, 'is_new': bool(arabic)}
    rest = cs
    if arabic:
        ax0, ax1 = min(c['x0'] for c in arabic), max(c['x1'] for c in arabic)
        head = [c for c in cs if c['x0'] >= ax0 - 0.1 and c['x1'] <= ax1 + 0.1 and X.fclass(c) in ('fa-bold', 'tnr')]
        rec['head'] = head
        rest = [c for c in cs if c not in head]
    if kind == 'pos':
        # leading rank digits (upright, small)
        i = 0
        rank = ''
        while i < len(rest) and (not rest[i]['text'].strip() or (X.fclass(rest[i]) == 'en' and rest[i]['text'].isdigit())):
            rank += rest[i]['text'].strip()
            i += 1
        if rank:
            rec['rank'] = int(rank)
            rest = rest[i:]
        rec['is_new'] = bool(rank)
    rest = sorted(rest, key=lambda c: c['x0'])
    runs = []
    for c in rest:
        f = X.fclass(c)
        if runs and runs[-1][1] == f:
            runs[-1][0] += c['text']
        else:
            runs.append([c['text'], f])
    for t, f in runs:
        if f == 'tnr':
            rec['ipa'] += t
        elif f == 'gloss':
            rec['gloss'] += t
        elif f == 'en':
            if kind == 'pos':
                rec['gloss'] += t   # upright glyphs inside a gloss (font slip)
            else:
                rec['pos'] += t
        elif t.strip():
            warnings.append(f"{kind}: unexpected glyphs {t!r} ({f})")
    if kind == 'alpha':
        m = re.search(r'(\d+)\s*$', rec['pos'])
        if m:
            rec['rank'] = int(m.group(1))
            rec['pos'] = rec['pos'][:m.start()]
    rec['ipa'] = rec['ipa'].strip()
    rec['gloss'] = rec['gloss'].strip()
    rec['pos'] = rec['pos'].strip()
    return rec


def finish(rec_entries):
    for e in rec_entries:
        e['gloss'] = re.sub(r'\s*,\s*', ', ', e['gloss']).strip(' ,')
        e['ipa'] = re.sub(r'\s*,\s*', ', ', re.sub(r'\s+', ' ', e['ipa'])).strip()
        if 'pos' in e:
            e['pos'] = re.sub(r'\s+', '', e['pos'])
    return rec_entries


alpha = []
with pdfplumber.open(PDF) as pdf:
    for pno in ALPHA_PAGES:
        page = pdf.pages[pno - 1]
        chars = [dict(c, idx=i) for i, c in enumerate(page.chars) if c['top'] > 50]
        if pno == ALPHA_PAGES[0]:
            chars = [c for c in chars if c['top'] > 150]  # title + key box
        bold_x = sorted(set(round(c['x0']) for c in chars if X.fclass(c) == 'fa-bold'))
        gaps = [(b - a, a, b) for a, b in zip(bold_x, bold_x[1:])]
        big = max(gaps) if gaps else None
        split = (big[2] - 3) if big and big[0] > 60 else 10000
        cols = column_groups(chars, [split])
        for col in cols:
            last = None
            for ln in X.group_lines(col):
                if not ''.join(c['text'] for c in ln['chars']).strip():
                    continue
                rec = parse_index_line(ln, 'alpha')
                if rec['is_new']:
                    e = {'headword': X.visual_to_logical(rec['head'], rank=f"alpha p{pno}"), 'ipa': rec['ipa'],
                         'gloss': rec['gloss'], 'pos': rec['pos'], 'rank': rec['rank'], 'page': pno}
                    alpha.append(e)
                    last = e
                else:
                    if last is None:
                        warnings.append(f"alpha p{pno}: continuation without entry: {''.join(c['text'] for c in ln['chars'])!r}")
                        continue
                    if rec['ipa']:
                        last['ipa'] += ' ' + rec['ipa']
                    if rec['gloss']:
                        sep = '' if last['gloss'].endswith('-') else ' '
                        last['gloss'] += sep + rec['gloss']
                    if rec['pos']:
                        last['pos'] += rec['pos']
                    if rec['rank'] is not None:
                        if last['rank'] is not None:
                            warnings.append(f"alpha p{pno}: second rank for {last['headword']}: {rec['rank']}")
                        last['rank'] = rec['rank']
    merged = []
    for e in alpha:
        if merged and e['rank'] is None and not merged[-1]['ipa'] and not merged[-1]['gloss']:
            prev = merged[-1]
            prev['headword'] = prev['headword'] + ' ' + e['headword']
            prev['ipa'] = e['ipa']
            prev['gloss'] = e['gloss']
            prev['pos'] = (prev['pos'] + e['pos']).strip()
            warnings.append(f"alpha: merged wrapped headword -> {prev['headword']!r}")
            continue
        merged.append(e)
    alpha = finish(merged)

    pos_index = {}
    section = None
    with_counts = {}
    for pno in POS_PAGES:
        page = pdf.pages[pno - 1]
        chars = [dict(c, idx=i) for i, c in enumerate(page.chars) if c['top'] > 50]
        if pno == POS_PAGES[0]:
            chars = [c for c in chars if c['top'] > 150]
        # section headings (12pt)
        heads = [c for c in chars if c['size'] > 10]
        # rank right edges -> three columns
        xs = sorted(c['x1'] for c in chars if c['text'].isdigit() and X.fclass(c) == 'en' and c['size'] < 7)
        groups = []
        for x in xs:
            if groups and x - groups[-1][-1] < 20:
                groups[-1].append(x)
            else:
                groups.append([x])
        groups = [g for g in groups if len(g) >= 3]
        rights = [max(g) for g in groups]
        splits = [r - 19 for r in rights[1:]]
        near = [c for c in chars if any(abs(c['x0'] - sp) < 4 for sp in splits) and c['text'].strip()]
        if near:
            warnings.append(f"pos p{pno}: glyphs near column split: {[(c['text'], round(c['x0'],1)) for c in near][:8]}")
        body = [c for c in chars if c['size'] <= 10]
        cols = [[] for _ in range(len(splits) + 1)]
        for c in body:
            k = sum(1 for sp in splits if c['x0'] >= sp)
            # 7.5pt text that starts left of the column's rank edge is overflow from the previous column
            if k > 0 and c['size'] >= 7 and c['x0'] < rights[k] - 1:
                k -= 1
            cols[k].append(c)
        # headings are placed in the columns too; process in reading order (column by column)
        for ci, col in enumerate(cols):
            col_heads = [c for c in heads if (ci == 0 or c['x0'] >= splits[ci - 1]) and (ci == len(splits) or c['x0'] < splits[ci])]
            items = sorted(X.group_lines(col) + X.group_lines(col_heads, tol=6), key=lambda ln: ln['top'])
            last = None
            pending_head = ''
            for ln in items:
                txt = ''.join(c['text'] for c in ln['chars']).strip()
                if not txt:
                    continue
                if any(c['size'] > 10 for c in ln['chars']):
                    pending_head = (pending_head + ' ' + txt).strip()
                    m = re.match(r'^(.*?):\s*(\d+)\s*words$', pending_head)
                    if m:
                        section = m.group(1).strip()
                        with_counts[section] = int(m.group(2))
                        pos_index.setdefault(section, [])
                        last = None
                        pending_head = ''
                    continue
                if pending_head:
                    warnings.append(f"pos p{pno}: unexpected heading {pending_head!r}")
                    pending_head = ''
                rec = parse_index_line(ln, 'pos')
                if rec['is_new']:
                    if section is None:
                        warnings.append(f"pos p{pno}: entry before any section: {txt!r}")
                        continue
                    e = {'rank': rec['rank'], 'headword': X.visual_to_logical(rec['head'], rank=f"pos p{pno}"),
                         'ipa': rec['ipa'], 'gloss': rec['gloss'], 'page': pno}
                    if rec['pos']:
                        warnings.append(f"pos p{pno}: upright text in entry {rec['rank']}: {rec['pos']!r}")
                        e['gloss'] = (e['gloss'] + ' ' + rec['pos']).strip()
                    pos_index[section].append(e)
                    last = e
                else:
                    if last is None:
                        warnings.append(f"pos p{pno}: continuation without entry: {txt!r}")
                        continue
                    if rec['head']:
                        part = X.visual_to_logical(rec['head'], rank=f"pos p{pno}")
                        joined = last['headword'] + part
                        ref = MAIN.get(last['rank'])
                        if ref and ref.replace('\u200c', '').replace(' ', '') == joined.replace('\u200c', '').replace(' ', '') \
                                and ' ' not in ref and '\u200c' not in ref:
                            last['headword'] = joined   # a single word broken across lines
                        else:
                            last['headword'] = last['headword'] + ' ' + part
                    if rec['ipa']:
                        last['ipa'] += ' ' + rec['ipa']
                    if rec['gloss']:
                        sep = '' if last['gloss'].endswith('-') else ' '
                        last['gloss'] += sep + rec['gloss']
                    if rec['pos']:
                        last['gloss'] += ' ' + rec['pos']
    for k in pos_index:
        finish(pos_index[k])

json.dump(alpha, open(OUT_ALPHA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump({'counts': with_counts, 'index': pos_index}, open(OUT_POS, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(OUT_POS + '.warnings.txt', 'w', encoding='utf-8').write('\n'.join(warnings + X.warnings))
print("alpha entries:", len(alpha))
print("pos sections:", {k: (len(v), with_counts.get(k)) for k, v in pos_index.items()})
print("warnings:", len(warnings) + len(X.warnings))
