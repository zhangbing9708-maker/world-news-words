#!/usr/bin/env python3
"""Cross-check freq.json against pdftotext output (independent extraction path)."""
import json
import re
import subprocess
import sys
from collections import Counter

PDF, JSON = sys.argv[1], sys.argv[2]
txt = subprocess.run(['pdftotext', '-f', '19', '-l', '279', PDF, '-'], capture_output=True, text=True).stdout
lines = txt.split('\n')

RLE, PDFM = '‫', '‬'
HEAD = re.compile(r'^(\d+) (?:[ً-ٟ]\s*)?' + RLE + r' ?(.*?)' + PDFM + r' ?(.*)$')
entries_pt = {}
cur = None
for ln in lines:
    m = HEAD.match(ln)
    if m and (cur is None or cur['rank'] < int(m.group(1)) <= cur['rank'] + 3):
        cur = {'rank': int(m.group(1)), 'head': m.group(2).strip(), 'rest': m.group(3).strip(), 'body': []}
        entries_pt[cur['rank']] = cur
        continue
    if cur is not None:
        cur['body'].append(ln)

mine = json.load(open(JSON, encoding='utf-8'))
print("pdftotext entries:", len(entries_pt), " mine:", len(mine))
AR = '؀-ۿ'
AR_RE = re.compile('[' + AR + ']')
AR_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩',
                          '۰۱۲۳۴۵۶۷۸۹')


def unify(s):
    # pdftotext maps Persian yeh/kaf/digits to Arabic code points; ignore that and ZWNJ
    s = s.replace('ي', 'ی').replace('ك', 'ک').replace('‌', '')
    return s.translate(AR_DIGITS)


def arabic_only(s):
    return ''.join(ch for ch in unify(s) if '؀' <= ch <= 'ۿ')


def norm_lig(s):
    return s.replace('لا', 'ال')   # pdftotext reverses the لا ligature glyph


def letters(s):
    return re.sub(r'[^A-Za-z0-9]', '', s).lower()


PUNCT_SPLIT = re.compile(r'[،؛:«»()\[\]"]')


def segs(s):
    """Arabic text split at punctuation, as sorted letter strings
    (pdftotext reorders the pieces around punctuation marks)."""
    parts = PUNCT_SPLIT.split(unify(s))
    return sorted(''.join(re.findall('[' + AR + ']+', p)) for p in parts if AR_RE.search(p))


FURNITURE = re.compile(r'(?m)^\x0c?(Frequency index \d+|\d+|\d+ A Frequency Dictionary of Persian|A Frequency Dictionary of Persian)$')

problems = []
for e in mine:
    r = e['rank']
    p = entries_pt.get(r)
    if not p:
        problems.append((r, 'no pdftotext entry'))
        continue
    if arabic_only(norm_lig(e['headword'])) != arabic_only(p['head']):
        problems.append((r, f"headword {e['headword']!r} vs {p['head']!r}"))
    rest_mine = f"{e['ipa']} {e['gloss']} {e['pos']}"
    pt_rest = p['rest']
    body = p['body']
    k = 0
    pre_ar = ''
    while k < len(body) and not body[k].startswith('•') and not re.fullmatch(r'\d+ \| \d+\.?', body[k].strip()):
        if AR_RE.search(body[k]):
            pre_ar += body[k] + '\n'
        else:
            pt_rest += ' ' + body[k]
        k += 1
    if letters(rest_mine) != letters(pt_rest):
        problems.append((r, f"header text {rest_mine!r} vs {pt_rest.strip()!r}"))
    body_text = pre_ar + '\n'.join(body[k:])
    ar_mine = Counter(arabic_only(e['example_fa']))
    ar_pt = Counter(arabic_only(body_text))
    if ar_mine != ar_pt:
        diff = (ar_mine - ar_pt) + (ar_pt - ar_mine)
        problems.append((r, f"Arabic char multiset differs: {dict(diff)}\n   mine: {e['example_fa']}\n   pt  : {' '.join(re.findall('[' + AR + chr(0x200c) + ']+', body_text))}"))
    elif segs(norm_lig(e['example_fa'])) != segs(body_text):
        problems.append((r, f"Arabic order differs:\n   mine: {e['example_fa']}\n   pt  : {' '.join(re.findall('[' + AR + chr(0x200c) + ']+', body_text))}"))
    en_pt = re.sub('[' + AR + r'‌‫‬•]', '', body_text)
    en_pt = FURNITURE.sub('', en_pt)
    en_pt = re.sub(r'\d+ \| \d+\.?', '', en_pt)
    if letters(e['example_en']) not in letters(en_pt) or len(letters(en_pt)) > len(letters(e['example_en'])) + 60:
        problems.append((r, f"English differs:\n   mine: {e['example_en']}\n   pt  : {en_pt.strip()!r}"))
    m = re.search(r'(\d+) \| (\d+)', body_text)
    if m:
        if e['dp'] != int(m.group(1)) or e['raw'] != int(m.group(2)):
            problems.append((r, f"dp/raw {e['dp']}/{e['raw']} vs {m.group(1)}/{m.group(2)}"))
    elif e['dp'] is not None:
        problems.append((r, 'pdftotext has no dp line but mine has'))

print("problems:", len(problems))
for r, msg in problems:
    print(r, msg)
