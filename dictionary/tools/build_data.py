#!/usr/bin/env python3
"""Assemble the extracted pieces into the site data files and plain-text exports.

usage: build_data.py freq.json boxes.json pos.json out_dir
"""
import csv
import json
import os
import re
import sys
import unicodedata

FREQ, BOXES, POS, OUT = sys.argv[1:5]
entries = json.load(open(FREQ, encoding='utf-8'))
lists = json.load(open(BOXES, encoding='utf-8'))
posidx = json.load(open(POS, encoding='utf-8'))

POS_NAMES = {'adj': 'adjective', 'adv': 'adverb', 'conj': 'conjunction', 'n': 'noun', 'prep': 'preposition',
             'pron': 'pronoun', 'pn': 'proper noun', 'q': 'quantifier', 'v': 'verb', 'expression': 'expression'}
POS_FIX = {'N': 'n', 'ad': 'adj'}          # two typos in the printed book (ranks 870 and 3889)
SECTION_TO_TAG = {'Adjectives': 'adj', 'Adverbs': 'adv', 'Conjunctions': 'conj', 'Nouns': 'n', 'Prepositions': 'prep',
                  'Pronouns': 'pron', 'Proper nouns': 'pn', 'Quantifiers': 'q', 'Verbs': 'v'}


def clean(s):
    s = s.replace('ﷲ', 'الله')      # ﷲ ligature -> الله
    s = re.sub(r'[ \t]+', ' ', s).strip()
    return s


# thematic list membership
membership = {}
for L in lists:
    for w in L['words']:
        w['headword'] = clean(w['headword'])
        if w['rank'] is not None and w['rank'] <= 5000:
            membership.setdefault(w['rank'], []).append(L['num'])

# POS-specific glosses
pos_gloss = {}
for sec, items in posidx['index'].items():
    tag = SECTION_TO_TAG[sec]
    for it in items:
        pos_gloss.setdefault(it['rank'], {})[tag] = {'gloss': clean(it['gloss']), 'ipa': clean(it['ipa']),
                                                      'headword': clean(it['headword'])}

out_entries = []
for e in entries:
    tags = [POS_FIX.get(t, t) for t in e['pos'].split(',') if t]
    rec = {
        'rank': e['rank'],
        'headword': clean(e['headword']),
        'ipa': clean(e['ipa']),
        'gloss': clean(e['gloss']),
        'pos': e['pos'],
        'pos_tags': tags,
        'example_fa': clean(e['example_fa']),
        'example_en': clean(e['example_en']),
        'dp': e['dp'],
        'raw': e['raw'],
        'book_page': e['book_page'],
        'lists': membership.get(e['rank'], []),
        'pos_glosses': pos_gloss.get(e['rank'], {}),
    }
    out_entries.append(rec)

os.makedirs(OUT, exist_ok=True)
meta = {
    'source': 'Corey Miller & Karineh Aghajanian-Stewart, A Frequency Dictionary of Persian: Core Vocabulary for Learners (Routledge, 2018)',
    'entries': len(out_entries),
    'thematic_lists': len(lists),
    'pos_sections': {k: len(v) for k, v in posidx['index'].items()},
    'fields': {
        'rank': 'position in the dispersion-adjusted frequency list (1 = most frequent)',
        'headword': 'word family head in Persian script',
        'ipa': 'pronunciation (IPA, Iranian Persian)',
        'gloss': 'English equivalent(s); commas separate senses, slashes separate glosses sharing a pronunciation',
        'pos': 'parts of speech represented in the word family (adj, adv, conj, n, prep, pron, pn, q, v)',
        'example_fa': 'sample context from the corpus (Persian)',
        'example_en': 'English translation of the sample context',
        'dp': 'dispersion code 38-97 (100*exp(-DP)); values near 100 = evenly spread through the corpus',
        'raw': 'raw frequency: total count of the word family in the 150-million-word corpus',
        'book_page': 'page of the printed book',
        'lists': 'numbers of the thematic vocabulary lists the word belongs to',
        'pos_glosses': 'gloss/pronunciation given for the word under each part of speech in the part-of-speech index',
    },
    'notes': [
        'Rank 21 (بر) has no dispersion/raw-frequency line in the printed book.',
        'The printed part-of-speech of rank 870 (خانم) is "N" and of rank 3889 (ریز) is "ad"; pos_tags normalises these to n / adj, pos keeps the printed form.',
        'The part-of-speech index prints ranks 3193 and 3536 without the initial به (رسمیت شناختن, ثمر رساندن); the main entries have به رسمیت شناختن and به ثمر رساندن.',
        'The thematic list "Colors" prints the pronunciation of rank 16359 as "xormgji"; kept as printed.',
        'Spelling variants in the corpus sentences (Arabic ي/ك, missing or extra spaces, ZWNJ) are kept as printed; search normalises them.',
    ],
}

json.dump({'meta': meta, 'entries': out_entries, 'lists': lists},
          open(os.path.join(OUT, 'dictionary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

with open(os.path.join(OUT, 'entries.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(['rank', 'headword', 'ipa', 'gloss', 'pos', 'example_fa', 'example_en', 'dp', 'raw', 'book_page', 'thematic_lists'])
    for e in out_entries:
        w.writerow([e['rank'], e['headword'], e['ipa'], e['gloss'], e['pos'], e['example_fa'], e['example_en'],
                    '' if e['dp'] is None else e['dp'], '' if e['raw'] is None else e['raw'], e['book_page'],
                    ','.join(str(n) for n in e['lists'])])

with open(os.path.join(OUT, 'thematic_lists.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(['list_number', 'list_title', 'rank', 'headword', 'ipa', 'gloss'])
    for L in lists:
        for wd in L['words']:
            w.writerow([L['num'], L['title'], '' if wd['rank'] is None else wd['rank'], wd['headword'], wd['ipa'], wd['gloss']])

with open(os.path.join(OUT, 'pos_index.tsv'), 'w', encoding='utf-8', newline='') as f:
    w = csv.writer(f, delimiter='\t', lineterminator='\n')
    w.writerow(['part_of_speech', 'rank', 'headword', 'ipa', 'gloss'])
    for sec, items in posidx['index'].items():
        for it in items:
            w.writerow([sec, it['rank'], clean(it['headword']), clean(it['ipa']), clean(it['gloss'])])

# plain-text rendering of the whole frequency index
with open(os.path.join(OUT, 'dictionary.txt'), 'w', encoding='utf-8') as f:
    f.write('A FREQUENCY DICTIONARY OF PERSIAN — Core Vocabulary for Learners\n')
    f.write('Corey Miller and Karineh Aghajanian-Stewart (Routledge, 2018)\n')
    f.write('Frequency index: rank, headword, pronunciation, gloss, part of speech; example sentence — translation; dispersion | raw count\n\n')
    for e in out_entries:
        f.write(f"{e['rank']} {e['headword']} {e['ipa']} {e['gloss']} {e['pos']}\n")
        f.write(f"    • {e['example_fa']} — {e['example_en']}\n")
        if e['dp'] is not None:
            f.write(f"    {e['dp']} | {e['raw']}\n")
        f.write('\n')
    f.write('\n\nTHEMATIC VOCABULARY LISTS (rank, headword, pronunciation, gloss)\n')
    for L in lists:
        f.write(f"\n{L['num']} {L['title']}\n")
        for wd in L['words']:
            f.write(f"    {wd['rank'] if wd['rank'] is not None else 'N/A'} {wd['headword']} {wd['ipa']} {wd['gloss']}\n")
    f.write('\n\nPART OF SPEECH INDEX (rank, headword, pronunciation, gloss)\n')
    for sec, items in posidx['index'].items():
        f.write(f"\n{sec}: {len(items)} words\n")
        for it in items:
            f.write(f"    {it['rank']} {clean(it['headword'])} {clean(it['ipa'])} {clean(it['gloss'])}\n")

# compact JS payload for the site: rows as arrays, POS-index glosses only where they add information
rows = []
for e in out_entries:
    pg = {}
    for tag, d in e['pos_glosses'].items():
        if d['gloss'] != e['gloss'] or d['ipa'] != e['ipa']:
            pg[tag] = [d['gloss'], d['ipa']] if d['ipa'] != e['ipa'] else [d['gloss']]
    rows.append([e['rank'], e['headword'], e['ipa'], e['gloss'], e['pos_tags'], e['example_fa'], e['example_en'],
                 e['dp'], e['raw'], e['book_page'], e['lists'], pg])
site = {'meta': meta,
        'fields': ['rank', 'headword', 'ipa', 'gloss', 'pos_tags', 'example_fa', 'example_en', 'dp', 'raw', 'book_page', 'lists', 'pos_glosses'],
        'entries': rows,
        'lists': [{'num': L['num'], 'title': L['title'], 'words': [[w['rank'], w['headword'], w['ipa'], w['gloss']] for w in L['words']]} for L in lists]}
with open(os.path.join(OUT, 'data.js'), 'w', encoding='utf-8') as f:
    f.write('window.PERSIAN_DICT = ')
    json.dump(site, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';\n')
print("entries", len(out_entries), "lists", len(lists), "pos sections", {k: len(v) for k, v in posidx['index'].items()})
print("size data.js", os.path.getsize(os.path.join(OUT, 'data.js')))
