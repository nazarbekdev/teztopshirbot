#!/usr/bin/env python3
"""
2-reel ssenariysi (chat hikoya, kurs ishi): ikki ovoz (talaba=Sardor erkak, do'st=Madina ayol) → timeline2.json.
Ishlatish: python build_timeline2.py <ishchi_papka>
"""
import asyncio, json, pathlib, subprocess, sys
import edge_tts

WORK = pathlib.Path(sys.argv[1])
VOICES = {"T": "uz-UZ-SardorNeural", "D": "uz-UZ-MadinaNeural"}
LEAD, TAIL, MIN_DUR = 0.2, 0.45, 1.8

# (nomi, gapiruvchi T|D|None, matn, turi)
SCENES = [
    ("hook", "T", "Ertaga kurs ishini topshirishim kerak, hali boshlamadim! 😭", "bubble_T"),
    ("reply1", "D", "Nima?! Tez Topshir botini sinab ko'r.", "bubble_D"),
    ("ask", "T", "Bu nima o'zi?", "bubble_T"),
    ("explain", "D", "Telegramdagi bot. Mavzuni yozasan, fayl o'zi keladi. Kurs ishi atigi ellik besh ming so'mdan.", "bubble_D"),
    ("demo", "T", "Voy, bir necha daqiqada tayyor bo'libdi!", "demo"),
    ("advice", "D", "Faqat topshirishdan oldin o'zing bir o'qib chiq, xo'pmi?", "bubble_D"),
    ("promo", "D", "Promokod Tez start: birinchi uch yuz foydalanuvchiga bitta xizmat bepul! Kurs ishi bundan mustasno.", "promo"),
]


async def speak(name, voice, text):
    out = WORK / f"{name}.mp3"
    words = []
    comm = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    with open(out, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({"text": chunk["text"], "t0": chunk["offset"] / 1e7, "t1": (chunk["offset"] + chunk["duration"]) / 1e7})
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)]).decode())
    return words, dur


def find(words, *keys, after=0.0):
    for w in words:
        t = w["text"].lower().strip(".,:!?")
        if w["t0"] >= after and any(t.startswith(k) for k in keys):
            return w["t0"]
    return after


async def main():
    timeline, cursor = [], 0.0
    for name, speaker, text, kind in SCENES:
        voice = VOICES.get(speaker, VOICES["D"])
        words, voice_dur = await speak(name, voice, text)
        dur = max(MIN_DUR, LEAD + voice_dur + TAIL)
        for w in words:
            w["t0"] += LEAD; w["t1"] += LEAD
        scene = {"name": name, "speaker": speaker, "kind": kind, "text": text, "start": round(cursor, 3),
                 "dur": round(dur, 3), "voice": f"{name}.mp3", "voice_at": round(cursor + LEAD, 3), "words": words, "events": {}}
        ev = scene["events"]
        if name == "demo":
            ev["type"] = find(words, "voy") and 0.05  # demo boshida darhol
        if name == "promo":
            ev["coupon"] = find(words, "promokod")
            ev["note"] = find(words, "kurs", after=ev["coupon"] + 0.3)
        timeline.append(scene)
        cursor += dur
    (WORK / "timeline2.json").write_text(json.dumps({"total": round(cursor, 3), "scenes": timeline}, ensure_ascii=False, indent=1))
    print("jami", round(cursor, 2), "s;", ", ".join(f"{s['name']}={s['dur']}" for s in timeline))

asyncio.run(main())
