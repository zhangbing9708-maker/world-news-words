"""Shared word rules for World News Words. Mirrors the tokenizer and lookup in index.html."""
import re

TOKEN = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*")
HAS_LETTER = re.compile(r"[^\W\d_]")

# Words that never get a glossary entry (shown as plain, untappable text).
STOPWORDS = set("""
a an the and or but nor of in on at by for from to with as into onto than then that this these those
which who whom whose what it its it's they them their theirs there he him his she her hers we us our
you your i me my is are was were be been being am has have had having do does did done will would shall
should can could may might must not no so if s
""".split())


def norm(word):
    return word.lower().replace("’", "'")


def is_acronym(word):
    """All-capital tokens such as US, WHO, AI, G7 are looked up case-sensitively first."""
    return len(word) >= 2 and word.isupper()


def candidates(w):
    """Lower-case forms to try, in order, when looking a token up (same order as index.html)."""
    c = [w]
    if w.endswith("'s"):
        c.append(w[:-2])
    elif w.endswith("s'"):
        c.append(w[:-1])
    for x in list(c):
        if x.endswith("ies"):
            c.append(x[:-3] + "y")
        if x.endswith("es"):
            c.append(x[:-2])
        if x.endswith("s"):
            c.append(x[:-1])
    out = []
    for x in c:
        if x and x not in out:
            out.append(x)
    return out


def tokens(text):
    for m in TOKEN.finditer(text or ""):
        t = m.group(0)
        if HAS_LETTER.search(t):
            yield t


def sentences(story):
    yield story.get("title", "")
    for s in story.get("summary", []):
        yield s
    for s in story.get("why", []):
        yield s


def needs_entry(word):
    if is_acronym(word):
        return True
    return norm(word) not in STOPWORDS


def lookup(glossary, word):
    forms = glossary.get("forms", {})
    entries = glossary.get("entries", {})
    if is_acronym(word):
        k = forms.get(word.replace("’", "'"))
        if k in entries:
            return k
    for c in candidates(norm(word)):
        k = forms.get(c) or (c if c in entries else None)
        if k and k in entries:
            return k
    return None
