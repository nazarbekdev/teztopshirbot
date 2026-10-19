#!/usr/bin/env python3
"""
Reel ssenariysi → ovoz (Edge TTS, uz-UZ-MadinaNeural) + so'z vaqtlari + voqealar jadvali (`timeline.json`).
Animatsiya (reel.html) va tovush effektlari (mix_audio.py) BIR XIL jadvaldan o'qiydi — rasm va tovush mos tushadi.

Ishlatish:  python build_timeline.py <ishchi_papka>
"""

import asyncio
import json
import pathlib
import subprocess
import sys

import edge_tts

WORK = pathlib.Path(sys.argv[1])
VOICE, RATE = "uz-UZ-MadinaNeural", "+6%"
LEAD, TAIL, MIN_DUR = 0.25, 0.55, 2.8

SCENES = [
    ("hook", "Ertaga topshirish kerak, lekin hali hech narsa tayyor emasmi?"),
    ("solution", "Telegramdagi Tez Topshir boti hammasini tez hal qiladi!"),
    ("services", "Kurs ishi, taqdimot, referat, mustaqil ish, test va krossvord. Narxlar atigi bir ming besh yuz so'mdan!"),
    ("demo", "Mavzuni yozasiz, va bir necha daqiqada tayyor fayl o'zingizga keladi."),
    ("promo", "Birinchi uch yuz foydalanuvchiga istalgan bitta xizmat bepul! Promokod: Tez start. Telegramda: Tez Topshir bot."),
]


async def speak(name: str, text: str):
    out = WORK / f"{name}.mp3"
    words = []
    comm = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
    with open(out, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({"text": chunk["text"], "t0": chunk["offset"] / 1e7,
                              "t1": (chunk["offset"] + chunk["duration"]) / 1e7})
    dur = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)]).decode())
    return words, dur


def find(words, *keys, after=0.0):
    """Birinchi mos so'zning boshlanish vaqti (sahna ichida)."""
    for w in words:
        t = w["text"].lower().strip(".,:!?")
        if w["t0"] >= after and any(t.startswith(k) for k in keys):
            return w["t0"]
    return after


async def main():
    timeline, cursor = [], 0.0
    for name, text in SCENES:
        words, voice_dur = await speak(name, text)
        dur = max(MIN_DUR, LEAD + voice_dur + TAIL)
        for w in words:                                     # so'z vaqtlari sahna boshiga nisbatan (LEAD bilan)
            w["t0"] += LEAD
            w["t1"] += LEAD
        scene = {"name": name, "text": text, "start": round(cursor, 3), "dur": round(dur, 3), "voice": f"{name}.mp3",
                 "voice_at": round(cursor + LEAD, 3), "words": words, "events": {}}
        ev = scene["events"]
        if name == "services":
            for i, key in enumerate(("kurs", "taqdimot", "referat", "mustaqil", "test", "krossvord")):
                ev[f"card{i}"] = find(words, key)
            ev["price"] = find(words, "bir", after=ev["card5"])
        if name == "demo":
            ev["type"] = find(words, "mavzuni")
            ev["progress"] = find(words, "bir", after=ev["type"] + 0.2)
            ev["file"] = find(words, "tayyor")
        if name == "promo":
            ev["coupon"] = find(words, "promokod")
            ev["cta"] = find(words, "telegramda")
            ev["gift"] = 0.2
            ev["free"] = find(words, "bepul")
        timeline.append(scene)
        cursor += dur
    (WORK / "timeline.json").write_text(json.dumps({"total": round(cursor, 3), "scenes": timeline}, ensure_ascii=False, indent=1))
    print("jami", round(cursor, 2), "soniya;", ", ".join(f"{s['name']}={s['dur']}" for s in timeline))


asyncio.run(main())
