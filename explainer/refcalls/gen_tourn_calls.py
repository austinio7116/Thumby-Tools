#!/usr/bin/env python3
"""The tournament referee's calls (CueVR 7.5): 34 pieces per voice, every one
CUT FROM A WHOLE SENTENCE in the place it is used (Mark, 2026-10-12: components,
not copies). Read the plan doc's "The referee's calls" section first.

  Opening name  "Player three"              x8   from match calls
  Second name   "and player six,"           x8   from match calls
  Table         "to table two."             x4   from match calls (a carrier after)
  Closing name  "player five."              x8   from champion lines (a carrier after)
  Lead-ins      "The final:"                     from the final's call
                "Your tournament champion is"    from champion lines
  Walkover      "has a walkover."                (a carrier after)
  Fixed         room open / five minutes / draw made, whole (a carrier after)

Every sentence is generated whole with the F5 clone, and Whisper's word times
place the cuts at the quietest point between two words. A piece that ends a
call comes from a sentence that runs on past it (F5 drops a final consonant):
70 ms kept past the last word, then 0.35 s of real silence.

  HF_HOME=/mnt/d/hf-cache REFCALL_VOICE=narrator|female python gen_tourn_calls.py [takes 3]

Writes tourn_<voice>/<piece>_t<take>.wav (22050 Hz, 16-bit) and a
tourn_<voice>/pieces.json of what was cut from what.
"""
import json, os, sys

import numpy as np
import torch
import torchaudio

from gen_refcalls import TAG, REF, REF_TEXT, NFE, HEADROOM, GAME_RATE, PEAK

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, f"tourn_{TAG}")
NUM = ["", "one", "two", "three", "four", "five", "six", "seven", "eight"]
TAIL_MS = 70
SILENCE = 0.35
CARRY = "Please make your way there."

# ---- the sentences, and the pieces each gives -----------------------------
# a match call for every opening number; the second numbers a permutation, so
# each appears once; the tables round twice
SECOND = [0, 6, 5, 8, 7, 2, 1, 4, 3]


def sentences():
    """EVERY PIECE IS FOLLOWED BY A REAL PAUSE in the sentence it is cut from --
    an ellipsis inside a call, a full stop and a carrier sentence at its end --
    and the cut goes inside that pause, so the piece's last sound is whole.
    (Commas made no pause: F5 runs straight through them.)"""
    S = []
    for n in range(1, 9):
        m, t = SECOND[n], (n - 1) % 4 + 1
        S.append({"key": f"match{n}", "text": f"Player {NUM[n]}... and player {NUM[m]}... to table {NUM[t]}. {CARRY}",
                  "cuts": [("open_%d" % n, None, "player", NUM[n]),
                           ("second_%d" % m, "and", None, NUM[m]),
                           ("table_%d" % t, "to", None, NUM[t], "end")]})
    for n in range(1, 9):
        S.append({"key": f"champ{n}", "text": f"Your tournament champion is... player {NUM[n]}. Congratulations to everyone who played.",
                  "cuts": [("lead_champion", None, "your", "is"),
                           ("close_%d" % n, "player", None, NUM[n], "end")]})
    S.append({"key": "final", "text": "The final... player two... and player seven... to table one. Good luck to both players.",
              "cuts": [("lead_final", None, "the", "final")]})
    S.append({"key": "walkover", "text": "Player four... has a walkover. Please wait for the next call.",
              "cuts": [("walkover", "has", None, "walkover", "end")]})
    S.append({"key": "open", "text": "The tournament room is open. Players, please come in.",
              "cuts": [("fixed_open", None, "the", "open", "end")]})
    S.append({"key": "five", "text": "The tournament begins in five minutes. Players, please be ready.",
              "cuts": [("fixed_five", None, "the", "minutes", "end")]})
    S.append({"key": "draw", "text": "The draw has been made. The first matches will be called now.",
              "cuts": [("fixed_draw", None, "the", "made", "end")]})
    return S


def norm(w):
    """a heard word, as letters: Whisper writes numbers as digits ("player 3")"""
    d = "".join(c for c in w if c.isdigit())
    if d and 1 <= int(d) <= 8:
        return NUM[int(d)]
    return "".join(c for c in w.lower() if c.isalpha())


def quietest(w, sr, a, b):
    """the quietest 10 ms between a and b (seconds), as a sample index"""
    ia, ib = int(a * sr), int(b * sr)
    if ib - ia < int(0.012 * sr):
        return (ia + ib) // 2
    k = int(0.010 * sr)
    seg = w[ia:ib].abs()
    e = torch.nn.functional.avg_pool1d(seg.view(1, 1, -1), k, stride=1).view(-1)
    return ia + int(torch.argmin(e)) + k // 2


# ---- CUT IN THE SILENCE BEFORE THE NEXT WORD, NEVER ON A WORD'S TIME (Mark,
# 2026-10-12: "ALL of the voices STOP BEFORE THE END OF THE LAST WORD"). Whisper's
# word ends land early: a cut at end + 70 ms fell inside the last sound. The
# next word starts with p, t or k (or a new sentence), so just before it there
# is a stretch of real silence -- the cut is at the END of that stretch, so
# everything the piece's last sound did, release and all, is in the clip. A
# piece with no such silence is not cut.
QUIET_MIN = 0.14    # seconds of quiet that make the pause (a stop's closure inside a word is shorter)
KEEP = 0.37         # at most this much silence kept after the last sound


def quiet_runs(w, sr):
    """(start, end) seconds of every stretch quieter than 3% of the peak for QUIET_MIN or more"""
    k = int(0.005 * sr)
    e = torch.nn.functional.avg_pool1d(w.abs().view(1, 1, -1), k, stride=1, padding=k // 2).view(-1)
    q = (e < e.max() * 0.03).numpy()
    runs, i, n = [], 0, len(q)
    while i < n:
        if q[i]:
            j = i
            while j < n and q[j]:
                j += 1
            if (j - i) / sr >= QUIET_MIN:
                runs.append((i / sr, j / sr))
            i = j
        else:
            i += 1
    return runs


def main():
    takes = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    from f5_tts.api import F5TTS
    from f5_tts.infer.utils_infer import preprocess_ref_audio_text
    import whisper

    ref_file, ref_text = preprocess_ref_audio_text(REF, REF_TEXT)
    ri = torchaudio.info(ref_file)
    ref_sec = ri.num_frames / ri.sample_rate
    cps = len(ref_text.encode()) / ref_sec
    model = F5TTS()
    asr = whisper.load_model("small.en", download_root="/mnt/d/hf-cache/whisper")
    os.makedirs(OUT, exist_ok=True)
    log = {}
    for take in range(1, takes + 1):
        for s in sentences():
          # A SENTENCE IS TRIED AGAIN, with a new seed, until every piece of it
          # cuts inside a real pause (up to 8 tries); its pieces are kept together
          for attempt in range(8):
            seed = 1000 * take + sum(map(ord, s["key"])) % 997 + 7919 * attempt
            pending, fails = [], 0
            line = s["text"]
            dur = ref_sec + len(line.encode()) / cps + HEADROOM
            wav, sr, _ = model.infer(ref_file=REF, ref_text=REF_TEXT, gen_text=line, speed=1.0, nfe_step=NFE,
                                     seed=seed, fix_duration=dur, remove_silence=False, show_info=lambda *a, **k: None)
            w = torch.from_numpy(np.asarray(wav, dtype=np.float32))
            probe = torchaudio.functional.resample(w.unsqueeze(0), sr, 16000).view(-1)
            r = asr.transcribe(probe.numpy(), fp16=False, language="en", word_timestamps=True)
            words = [x for seg in r["segments"] for x in seg["words"]]
            heard = " ".join(norm(x["word"]) for x in words)
            print(f"[{TAG} t{take}] {s['key']}: {heard}", flush=True)
            for c in s["cuts"]:
                name, from_w, from_first, to_w = c[0], c[1], c[2], c[3]
                ends = len(c) > 4
                # where the piece starts: the first word, or the named word (from the left)
                if from_first:
                    i0 = 0
                else:
                    i0 = next((i for i, x in enumerate(words) if norm(x["word"]) == from_w), None)
                # where it ends: the named word, the first one after the start
                i1 = next((i for i, x in enumerate(words) if i0 is not None and i >= i0 and norm(x["word"]) == to_w), None)
                if i0 is None or i1 is None:
                    print(f"   {name}: NOT FOUND ({from_w or from_first!r}..{to_w!r}) -- skipped")
                    fails += 1
                    continue
                runs = quiet_runs(w, sr)
                # THE START: where the VOICE begins, not where the silence ends --
                # F5 breathes in after a pause, and a cut at the silence's end kept
                # the breath (Mark: "and player... always has an X ending at the
                # start of it"). The first moment the sound is well above a
                # breath's level, then back 20 ms for a vowel ("and") or 80 ms for
                # a consonant, so a t or p keeps its puff of air.
                k10 = int(0.010 * sr)
                env10 = torch.nn.functional.avg_pool1d(w.abs().view(1, 1, -1), k10, stride=1, padding=k10 // 2).view(-1)
                strong = float(env10.max()) * 0.12
                first = norm(words[i0]["word"])
                back = 0.02 if first[:1] in "aeiou" else 0.08
                if i0 == 0:
                    lo = 0
                else:
                    ws = words[i0]["start"]
                    before = [r for r in runs if ws - 0.30 <= r[1] <= ws + 0.15]
                    lo = int(before[-1][0] * sr) if before else quietest(w, sr, words[i0 - 1]["end"], ws)
                hi = min(len(env10), int((words[i0]["start"] + 0.45) * sr))
                on = (env10[lo:hi] >= strong).nonzero()
                if not on.numel():
                    print(f"   {name}: NO VOICE at {first!r} -- not cut"); fails += 1; continue
                a = max(lo, lo + int(on[0]) - int(back * sr))
                # THE END: the silence that ends where the NEXT word begins --
                # the one whose end is nearest the next word's start
                if i1 + 1 >= len(words):
                    print(f"   {name}: nothing after {to_w!r} -- not cut"); continue
                # THE PAUSE AFTER THE WORD: the first one that begins once the word
                # is under way (Whisper's times only place it roughly)
                ws, we = words[i1]["start"], words[i1]["end"]
                cand = [r for r in runs if r[0] >= ws + 0.08 and r[0] <= we + 0.60]
                if not cand:
                    print(f"   {name}: NO PAUSE after {to_w!r} -- not cut"); fails += 1; continue
                g0, g1 = cand[0]
                b = int(min(g1 - 0.004, g0 + KEEP) * sr)
                print(f"   {name}: cut in a {g1 - g0:.2f}s pause, kept {min(g1 - 0.004, g0 + KEEP) - g0:.2f}s of it")
                clip = w[a:b].clone()
                f = int(sr * 0.006)
                if clip.shape[-1] > 2 * f:
                    clip[:f] *= torch.linspace(0, 1, f)
                    clip[-f:] *= torch.linspace(1, 0, f)
                if ends and (b / sr - g0) < 0.30:
                    clip = torch.cat([clip, torch.zeros(int(sr * (0.30 - (b / sr - g0))))])
                g = torchaudio.functional.resample(clip.unsqueeze(0), sr, GAME_RATE)
                g = g / max(float(g.abs().max()), 1e-6) * PEAK
                dst = os.path.join(OUT, f"{name}_t{take}.wav")
                pending.append((dst, g, f"{name}_t{take}", {"from": s["key"], "seed": seed, "heard": heard,
                                                            "sec": round(g.shape[-1] / GAME_RATE, 3)}))
            if fails == 0 or attempt == 7:
                os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)
                torchaudio.save(os.path.join(OUT, "raw", f"{s['key']}_t{take}.wav"), w.unsqueeze(0), sr, encoding="PCM_S", bits_per_sample=16)
                for dst, g, key, ent in pending:
                    torchaudio.save(dst, g, GAME_RATE, encoding="PCM_S", bits_per_sample=16)
                    log[key] = ent
                break
            print(f"   ...{fails} not cut: trying {s['key']} again", flush=True)
    with open(os.path.join(OUT, "pieces.json"), "w") as f:
        json.dump(log, f, indent=1)
    print(f"{len(log)} pieces in {OUT}")


main()
