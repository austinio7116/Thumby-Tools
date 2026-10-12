#!/usr/bin/env python3
"""The referee calls' listening page (CueVR 7.5): every piece's takes, and
calls put together from whichever takes are chosen -- the way the game will
join them -- so the calls are judged whole, by ear (plan doc, "Judged by ear").

  python make_tourn_page.py <out dir>

Copies tourn_<voice>/*.wav to <out>/<voice>/ and writes <out>/index.html.
"""
import glob, json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
VOICES = [("narrator", "Male"), ("female", "Female")]
have = {}
for v, _ in VOICES:
    src = os.path.join(HERE, f"tourn_{v}")
    os.makedirs(os.path.join(OUT, v), exist_ok=True)
    for f in sorted(glob.glob(os.path.join(src, "*_t*.wav"))):
        shutil.copy(f, os.path.join(OUT, v, os.path.basename(f)))
        m = re.match(r"(.+)_t(\d+)\.wav$", os.path.basename(f))
        have.setdefault(v, {}).setdefault(m.group(1), []).append(int(m.group(2)))

page = open(os.path.join(HERE, "tourn_page.html")).read()
page = page.replace("/*HAVE*/{}", json.dumps(have))
open(os.path.join(OUT, "index.html"), "w").write(page)
print(os.path.join(OUT, "index.html"), sum(len(t) for v in have.values() for t in v.values()), "takes")
