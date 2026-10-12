#!/usr/bin/env python3
"""Extract the 31 thematic vocabulary lists (callout boxes) from the frequency index pages."""
import json
import re
import sys

import pdfplumber

sys.path.insert(0, __file__.rsplit('/', 1)[0])
import extract_freq as X  # reuse glyph helpers  # noqa: E402

PDF, OUT = sys.argv[1], sys.argv[2]
FIRST_PAGE, LAST_PAGE = 20, 279

lists = []
warnings = []


def box_objects(page):
    objs = [r for r in list(page.rects) + list(page.curves)
            if (r['x1'] - r['x0']) > 300 and (r['bottom'] - r['top']) > 40]
    merged = []
    for r in sorted(objs, key=lambda r: r['top']):
        if merged and r['top'] <= merged[-1]['bottom'] + 1:
            merged[-1]['bottom'] = max(merged[-1]['bottom'], r['bottom'])
        else:
            merged.append({'top': r['top'], 'bottom': r['bottom'], 'x0': r['x0'], 'x1': r['x1']})
    return merged


def parse_row_line(ln):
    cs = ln['chars']
    nonspace = [c for c in cs if c['text'].strip()]
    if not nonspace:
        return None
    first = nonspace[0]
    fc = X.fclass(first)
    if fc == 'rank' or (X.fshort(first['fontname']) == 'TG' and first['size'] > 10):
        return ('skip', None)
    txt = ''.join(c['text'] for c in cs).strip()
    if txt == '(continued)':
        return ('skip', None)
    row = {'rank': None, 'has_rank': False, 'head': [], 'ipa': '', 'gloss': ''}
    i = 0
    rank = ''
    while i < len(cs) and (not cs[i]['text'].strip() or (X.fclass(cs[i]) == 'en' and cs[i]['text'] in '0123456789N/A')):
        if cs[i]['text'].strip():
            rank += cs[i]['text']
        i += 1
    if rank.isdigit():
        row['rank'] = int(rank)
        row['has_rank'] = True
    elif rank == 'N/A':
        row['has_rank'] = True
    else:
        i = 0  # not a rank cell after all
    rest = cs[i:]
    arabic = [c for c in rest if any(X.is_arabic(ch) for ch in c['text'])]
    if arabic:
        ax0, ax1 = min(c['x0'] for c in arabic), max(c['x1'] for c in arabic)
        head = [c for c in rest if c['x0'] >= ax0 - 0.1 and c['x1'] <= ax1 + 0.1 and X.fclass(c) == 'tnr']
        row['head'] = head
        rest = [c for c in rest if c not in head]
    italic = [c for c in rest if X.fclass(c) == 'gloss' and c['text'].strip()]
    gx0 = min(c['x0'] for c in italic) if italic else 1e9
    ipa_glyphs = [c for c in rest if X.fclass(c) == 'tnr' or (X.fclass(c) == 'en' and c['x1'] <= gx0 + 0.5)]
    gloss_glyphs = [c for c in rest if X.fclass(c) == 'gloss' or (X.fclass(c) == 'en' and c['x1'] > gx0 + 0.5)]
    row['ipa'] = ''.join(c['text'] for c in sorted(ipa_glyphs, key=lambda c: c['x0'])).strip()
    row['gloss'] = ''.join(c['text'] for c in sorted(gloss_glyphs, key=lambda c: c['x0'])).strip()
    other = [c for c in rest if X.fclass(c) not in ('tnr', 'gloss', 'en') and c['text'].strip()]
    if other:
        warnings.append(f"row {row['rank']}: unexpected glyphs: {[(c['text'], X.fshort(c['fontname'])) for c in other]}")
    if any(X.fclass(c) == 'en' for c in ipa_glyphs if c['text'].strip()):
        warnings.append(f"row {row['rank']}: IPA partly in upright font -> {row['ipa']!r}")
    return ('row', row)


with pdfplumber.open(PDF) as pdf:
    for pno in range(FIRST_PAGE, LAST_PAGE + 1):
        page = pdf.pages[pno - 1]
        for box in box_objects(page):
            chars = [dict(c, idx=i) for i, c in enumerate(page.chars)
                     if box['top'] - 1 <= c['top'] <= box['bottom'] + 1 and c['top'] > 50]
            title_chars = [c for c in chars if X.fshort(c['fontname']) == 'TG' and c['size'] > 10]
            title = ''.join(c['text'] for c in sorted(title_chars, key=lambda c: c['x0'])).strip()
            if title:
                m = re.match(r'^(\d+)\s+(.*)$', title)
                lists.append({'num': int(m.group(1)), 'title': m.group(2).strip(), 'pages': [pno], 'words': []})
            elif lists:
                lists[-1]['pages'].append(pno)
            else:
                warnings.append(f"p{pno}: box without title before any list")
                continue
            cur = lists[-1]
            segs = sorted([(round(l['top'], 1), l['x0'], l['x1']) for l in page.lines
                           if box['top'] <= l['top'] <= box['bottom'] and l['x1'] - l['x0'] < 200])
            segs = [sg for sg in segs if abs(sg[0] - segs[0][0]) < 1.5] if segs else []
            if len(segs) == 8:
                mid = (segs[3][2] + segs[4][1]) / 2
            else:
                mid = (box['x0'] + box['x1']) / 2
                warnings.append(f"p{pno} list {cur['num']}: header rules not found ({len(segs)}), using box centre")
            groups = [[c for c in chars if c['x0'] < mid], [c for c in chars if c['x0'] >= mid]]
            for g in groups:
                last = None
                last_top = None
                for ln in X.group_lines(g):
                    parsed = parse_row_line(ln)
                    if not parsed or parsed[0] == 'skip':
                        continue
                    row = parsed[1]
                    is_cont = (not row['has_rank']) and last_top is not None and (
                        (not row['head']) or (not row['gloss']) or (ln['top'] - last_top) < 10.0)
                    if not row['has_rank'] and not is_cont:
                        warnings.append(f"p{pno} list {cur['num']}: row without rank after {last['rank'] if last else None}: {row['ipa']!r} {row['gloss']!r}")
                    if is_cont:
                        if last is None:
                            warnings.append(f"p{pno} list {cur['num']}: continuation row without previous row: {row}")
                            continue
                        if row['head']:
                            last['headword'] = (last['headword'] + ' ' + X.visual_to_logical(row['head'], rank=f"box{last['rank']}")).strip()
                        if row['ipa']:
                            last['ipa'] = (last['ipa'] + ' ' + row['ipa']).strip()
                        if row['gloss']:
                            sep = '' if last['gloss'].endswith('-') else ' '
                            last['gloss'] = (last['gloss'] + sep + row['gloss']).strip()
                        continue
                    last_top = ln['top']
                    word = {'rank': row['rank'],
                            'headword': X.visual_to_logical(row['head'], rank=f"box{row['rank']}"),
                            'ipa': row['ipa'], 'gloss': row['gloss']}
                    cur['words'].append(word)
                    last = word

for L in lists:
    for w in L['words']:
        w['gloss'] = re.sub(r'\s*,\s*', ', ', w['gloss']).strip(' ,')
        w['ipa'] = re.sub(r'\s*,\s*', ', ', w['ipa']).strip()
        if not w['headword'] or not w['ipa'] or not w['gloss']:
            warnings.append(f"list {L['num']} rank {w['rank']}: empty field {w}")

json.dump(lists, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(OUT + '.warnings.txt', 'w', encoding='utf-8').write('\n'.join(warnings + X.warnings))
print("lists:", len(lists), [(L['num'], L['title'], len(L['words']), L['pages']) for L in lists])
print("warnings:", len(warnings) + len(X.warnings))
