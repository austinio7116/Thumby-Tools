#!/usr/bin/env python3
"""Trim what comes BEFORE a tournament piece's first word (Mark, 2026-10-12:
"and player... always has an X ending at the start of it"; the female closing
names "have a small ts before the words start"; "just cut out these unwanted
bits from the start of these words -- no need to regenerate").

What is there is the end of the word before, or a breath, ahead of the piece's
own first sound. The first word's own start is found from the sound itself:

  * a VOWEL-initial piece ("and player..."): where the sound first rises well
    above a breath's level (12% of the piece's peak), less 20 ms
  * a P-initial piece ("player n."): the lips close before the p -- the start
    is the end of that short silence, the latest quiet stretch (under 2% of
    the peak, 8 ms or more) in the 150 ms before the vowel; none found, the
    vowel less 40 ms

The original is kept as orig/<name>.wav beside it, once, and every trim is
made from that original, so running this again changes nothing more.

    python trim_tourn_starts.py <voice dir> <piece prefix> [<piece prefix>...]
    e.g.  python trim_tourn_starts.py tourn_narrator second_
          python trim_tourn_starts.py tourn_female second_ close_
"""
import array, glob, os, shutil, sys, wave

D = sys.argv[1]
PREFIXES = sys.argv[2:]
os.makedirs(os.path.join(D, "orig"), exist_ok=True)


def read(p):
    with wave.open(p) as w:
        a = array.array("h"); a.frombytes(w.readframes(w.getnframes()))
        return a, w.getframerate()


def env(a, sr, ms):
    k = max(1, int(sr * ms / 1000)); out = []; s = 0
    ab = [abs(x) for x in a]
    for i, v in enumerate(ab):
        s += v
        if i >= k:
            s -= ab[i - k]
        out.append(s / min(i + 1, k))
    # centre the window
    h = k // 2
    return out[h:] + [out[-1]] * h


def lowpass(a, sr, hz=800.0):
    """a first-order low-pass: voiced sound keeps its strength, hiss (s, ts, x) loses most of it"""
    import math
    k = 1.0 - math.exp(-2.0 * math.pi * hz / sr)
    y, out = 0.0, []
    for x in a:
        y += k * (x - y)
        out.append(y)
    return out


for pre in PREFIXES:
    for p in sorted(glob.glob(os.path.join(D, pre + "*_t*.wav"))):
        name = os.path.basename(p)
        o = os.path.join(D, "orig", name)
        if not os.path.exists(o):
            shutil.copy(p, o)
        a, sr = read(o)
        # A LEFTOVER FIRST? The clip opens with the end of the word before (60-80
        # ms of it), then the pause, then the piece's own word: skip to after
        # that pause -- a stretch under 5% of the peak for 100 ms or more that
        # begins in the first 250 ms
        e10 = env(a, sr, 10)
        ek = max(e10) or 1
        after = 0
        i, n = 0, min(len(e10), int(sr * 0.250))
        while i < n:
            if e10[i] < ek * 0.05:
                j = i
                while j < len(e10) and e10[j] < ek * 0.05:
                    j += 1
                if j - i >= int(sr * 0.100):
                    after = j
                    break
                i = j
            else:
                i += 1
        # WHERE THE VOICE BEGINS: the low band's first rise to 20% of its peak,
        # after any leftover and its pause
        lp = env(lowpass(a, sr), sr, 10)
        lpk = max(lp) or 1
        vo = next((i for i in range(after, len(lp)) if lp[i] >= lpk * 0.20), after)
        # ...and the cut at the QUIETEST moment in the 150 ms before it: the gap
        # between the stray sound and the word (for "player", the p's closure)
        e3 = env(a, sr, 3)
        lo, hi = max(0, vo - int(sr * 0.150)), max(0, vo - int(sr * 0.012))
        if after:
            lo = max(lo, after - int(sr * 0.050))     # never back into the leftover
        start = min(range(lo, hi), key=lambda i: e3[i]) if hi > lo else lo
        cut = a[start:]
        f = int(sr * 0.004)                           # a 4 ms fade in, no click
        for k in range(min(f, len(cut))):
            cut[k] = int(cut[k] * k / f)
        with wave.open(p, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(cut.tobytes())
        print(f"{name:22s} {'leftover skipped, ' if after else ''}voice at {vo / sr * 1000:4.0f} ms, cut at {start / sr * 1000:4.0f} ms")
