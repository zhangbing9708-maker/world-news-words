"""Make Farsi audio for World News Words.

usage:
  python3 tools/make_audio.py           make audio for every Farsi word and example that has none yet
  python3 tools/make_audio.py --prune   also delete audio files nothing refers to any more

Most phones and computers have no Persian voice, so the site plays recorded files for Farsi instead of
the device's text-to-speech. This script creates data/audio/fa/<id>.mp3 for:
  - every glossary entry (fa.v, the spelling with vowel marks, or else fa.w)   -> stored as fa.a
  - every key-word example sentence (ex.faV, or else ex.fa)                  -> stored as ex.faA
  - every example word in data/alphabets.json for Farsi (ex.v, or else ex.w)  -> stored as ex.a
The voice is the open-source Piper "gyro" Persian voice, run with sherpa-onnx. Both are downloaded from
GitHub into ~/.cache/wnw-tts the first time. ffmpeg turns the speech into small MP3 files.
An id is a hash of the spoken text, so files are reused and only new words are synthesised.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOSSARY = os.path.join(ROOT, "data", "glossary.json")
ALPHABETS = os.path.join(ROOT, "data", "alphabets.json")
AUDIO_DIR = os.path.join(ROOT, "data", "audio", "fa")
CACHE = os.path.expanduser("~/.cache/wnw-tts")
RELEASES = "https://github.com/k2-fsa/sherpa-onnx/releases/download"
ENGINE = "sherpa-onnx-v1.13.7-linux-x64-static"
ENGINE_URL = f"{RELEASES}/v1.13.7/{ENGINE}.tar.bz2"
VOICE = "vits-piper-fa_IR-gyro-medium"
VOICE_URL = f"{RELEASES}/tts-models/{VOICE}.tar.bz2"
TATWEEL = "ـ"


def ensure(name, url):
    path = os.path.join(CACHE, name)
    if os.path.isdir(path):
        return path
    os.makedirs(CACHE, exist_ok=True)
    print(f"Downloading {name} ...", flush=True)
    with tempfile.TemporaryDirectory(dir=CACHE) as td:
        tmp = os.path.join(td, "x.tar.bz2")
        subprocess.run(["curl", "-sSL", "--fail", "--retry", "2", "-o", tmp, url], check=True)
        with tarfile.open(tmp, "r:bz2") as tf:
            tf.extractall(CACHE, filter="data")
    if not os.path.isdir(path):
        sys.exit(f"Download of {name} did not produce {path}")
    return path


def audio_id(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def spoken(text):
    return re.sub(r"\s+", " ", str(text or "").replace(TATWEEL, "")).strip()


def main():
    prune = "--prune" in sys.argv
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is needed to make MP3 files.")
    glossary = json.load(open(GLOSSARY, encoding="utf-8"))
    alphabets = json.load(open(ALPHABETS, encoding="utf-8")) if os.path.exists(ALPHABETS) else None

    jobs = {}  # id -> text
    def want(text):
        t = spoken(text)
        if not t:
            return None
        i = audio_id(t)
        jobs[i] = t
        return i

    for e in glossary["entries"].values():
        fa = e.get("fa") or {}
        i = want(fa.get("v") or fa.get("w"))
        if i:
            fa["a"] = i
        ex = e.get("ex")
        if isinstance(ex, dict) and ex.get("fa"):
            i = want(ex.get("faV") or ex.get("fa"))
            if i:
                ex["faA"] = i
    if alphabets and isinstance(alphabets.get("fa"), dict):
        for sec in alphabets["fa"].get("sections", []):
            for c in sec.get("cells", []):
                ex = (c or {}).get("ex")
                if isinstance(ex, dict):
                    i = want(ex.get("v") or ex.get("w"))
                    if i:
                        ex["a"] = i

    os.makedirs(AUDIO_DIR, exist_ok=True)
    todo = {i: t for i, t in jobs.items() if not os.path.exists(os.path.join(AUDIO_DIR, i + ".mp3"))}
    if todo:
        engine = ensure(ENGINE, ENGINE_URL)
        voice = ensure(VOICE, VOICE_URL)
        binary = os.path.join(engine, "bin", "sherpa-onnx-offline-tts")
        model = os.path.join(voice, "fa_IR-gyro-medium.onnx")

        def synth(item):
            i, text = item
            with tempfile.TemporaryDirectory() as td:
                wav = os.path.join(td, "a.wav")
                subprocess.run([binary, f"--vits-model={model}", f"--vits-tokens={os.path.join(voice, 'tokens.txt')}",
                                f"--vits-data-dir={os.path.join(voice, 'espeak-ng-data')}", "--num-threads=1",
                                f"--output-filename={wav}", text], check=True, capture_output=True)
                out = os.path.join(AUDIO_DIR, i + ".mp3")
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-af", "adelay=60:all=1",
                                "-ac", "1", "-ar", "22050", "-c:a", "libmp3lame", "-b:a", "32k", out + ".tmp.mp3"], check=True)
                os.replace(out + ".tmp.mp3", out)
            return i

        workers = max(1, min(6, (os.cpu_count() or 2)))
        print(f"Making {len(todo)} audio files with {workers} workers ...", flush=True)
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for _ in pool.map(synth, sorted(todo.items())):
                done += 1
                if done % 50 == 0:
                    print(f"  {done}/{len(todo)}", flush=True)

    json.dump(glossary, open(GLOSSARY, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    if alphabets is not None:
        json.dump(alphabets, open(ALPHABETS, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

    removed = 0
    if prune:
        for f in os.listdir(AUDIO_DIR):
            if f.endswith(".mp3") and f[:-4] not in jobs:
                os.remove(os.path.join(AUDIO_DIR, f))
                removed += 1
    size = sum(os.path.getsize(os.path.join(AUDIO_DIR, f)) for f in os.listdir(AUDIO_DIR))
    print(f"Farsi audio: {len(todo)} new, {len(jobs) - len(todo)} reused, {removed} removed; "
          f"{len(os.listdir(AUDIO_DIR))} files, {size / 1e6:.1f} MB.")


if __name__ == "__main__":
    main()
