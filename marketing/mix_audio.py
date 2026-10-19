#!/usr/bin/env python3
"""
Reel tovushi: ovoz (sahna fayllari) + fon musiqasi (sintez, ovoz ostida pasayadi) + effektlar (timeline.json
voqealariga mos). Natija: <ishchi_papka>/mix.wav  (44.1 kHz stereo). Tashqi musiqa fayli YO'Q — mualliflik huquqi muammosi bo'lmaydi.
"""
import json, pathlib, subprocess, sys, wave
import numpy as np

W = pathlib.Path(sys.argv[1])
SR = 44100
tl = json.loads((W / "timeline.json").read_text())
N = int((tl["total"] + 0.6) * SR)
rng = np.random.default_rng(7)


def tone(freq, dur, kind="sine", decay=6.0, amp=1.0):
    t = np.arange(int(dur * SR)) / SR
    f = freq if np.isscalar(freq) else np.interp(t, np.linspace(0, dur, len(freq)), freq)
    ph = 2 * np.pi * np.cumsum(f if not np.isscalar(f) else np.full_like(t, f)) / SR
    w = np.sin(ph) if kind == "sine" else (2 * (ph / (2 * np.pi) % 1) - 1) * 0.5 if kind == "saw" else np.sign(np.sin(ph)) * 0.4
    return amp * w * np.exp(-decay * t) * np.minimum(1, t * 400)


def add(buf, sig, at, gain=1.0):
    i = int(at * SR)
    if i < 0 or i >= len(buf):
        return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += sig * gain


def noise_sweep(dur, f0, f1, amp=1.0):
    t = np.arange(int(dur * SR)) / SR
    n = rng.standard_normal(len(t))
    fc = np.linspace(f0, f1, len(t))
    # oddiy "tovush supurgisi": bandpass o'rniga modulyatsiyalangan shovqin
    env = np.sin(np.pi * np.linspace(0, 1, len(t))) ** 1.5
    return amp * n * env * 0.35 * (0.6 + 0.4 * np.sin(2 * np.pi * fc * t / SR * 0.02))


def pop(freq=880):
    return tone(np.linspace(freq * 0.75, freq * 1.25, int(0.09 * SR)), 0.09, decay=22, amp=0.8)


def ding():
    return tone(1318.5, 0.5, decay=7, amp=0.7) + tone(1975.5, 0.5, decay=9, amp=0.45)


def chime():
    out = np.zeros(int(1.0 * SR))
    for k, f in enumerate((784, 988, 1175, 1568)):
        add(out, tone(f, 0.7, decay=5, amp=0.55), k * 0.07)
    return out


# ── musiqa: 112 bpm, A minor, arpegiy + bas + yengil zarba ──
music = np.zeros(N)
bpm = 112
beat = 60 / bpm
chords = [(220.0, [440, 523.25, 659.25, 523.25]), (174.61, [349.23, 440, 523.25, 440]),
          (261.63, [523.25, 659.25, 783.99, 659.25]), (196.0, [392, 493.88, 587.33, 493.88])]
t = 0.0
bar = 0
while t < tl["total"] + 0.5:
    root, arp = chords[bar % 4]
    add(music, tone(root / 2, beat * 3.6, "sine", decay=1.4, amp=0.55), t)
    for i in range(8):
        add(music, tone(arp[i % 4], 0.35, "saw", decay=7, amp=0.16), t + i * beat / 2)
    for i in range(4):
        k = tone(np.linspace(130, 48, int(0.18 * SR)), 0.18, decay=14, amp=0.9)
        add(music, k, t + i * beat, 0.55)
        add(music, noise_sweep(0.05, 8000, 8000, 0.5), t + i * beat + beat / 2, 0.22)
    t += beat * 4
    bar += 1
music *= 0.55


# ── ovoz ──
def load_wav(path):
    with wave.open(str(path)) as f:
        return np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32) / 32768


voice = np.zeros(N)
spans = []
for s in tl["scenes"]:
    wav = W / (s["name"] + ".wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(W / s["voice"]), "-ar", str(SR), "-ac", "1", str(wav)], check=True)
    v = load_wav(wav)
    v = v / (np.abs(v).max() + 1e-9) * 0.92
    add(voice, v, s["voice_at"])
    spans.append((s["voice_at"], s["voice_at"] + len(v) / SR))

# ovoz ostida musiqa pasayadi (ducking), silliq
duck = np.ones(N)
for a, b in spans:
    duck[int(a * SR):int(b * SR)] = 0.38
k = np.ones(int(0.12 * SR)) / int(0.12 * SR)
duck = np.convolve(duck, k, mode="same")
music *= duck

# ── effektlar ──
sfx = np.zeros(N)
for s in tl["scenes"]:
    add(sfx, noise_sweep(0.55, 400, 3000, 1.0), s["start"] - 0.05, 0.5)       # sahna o'tishi
    ev = s["events"]
    st = s["start"]
    if s["name"] == "hook":
        for i in range(10):
            add(sfx, tone(1800 if i % 2 else 1400, 0.05, decay=60, amp=0.5), st + 0.3 + i * 0.25, 0.5)
        add(sfx, tone(np.linspace(60, 220, int(1.6 * SR)), 1.6, "saw", decay=0.6, amp=0.28), st + 0.1)  # past "riser"
        add(sfx, tone(70, 0.6, decay=6, amp=1.0), st + 0.15, 0.7)                   # "ERTAGA" zarbasi
    if s["name"] == "solution":
        add(sfx, chime(), st + 0.1, 0.45)
    if s["name"] == "services":
        for i in range(6):
            add(sfx, pop(700 + i * 90), st + ev[f"card{i}"], 0.55)
        add(sfx, chime(), st + ev["price"], 0.5)
    if s["name"] == "demo":
        for i in range(14):
            add(sfx, tone(2400 + (i % 3) * 200, 0.03, decay=90, amp=0.6), st + ev["type"] + i * 0.06, 0.35)
        add(sfx, noise_sweep(0.6, 800, 2500, 0.8), st + ev["progress"], 0.35)
        add(sfx, ding(), st + ev["file"], 0.6)
    if s["name"] == "promo":
        add(sfx, chime(), st + 0.2, 0.5)
        add(sfx, pop(1000), st + ev["coupon"], 0.6)
        add(sfx, ding(), st + ev["coupon"] + 0.5, 0.45)
        add(sfx, pop(1200), st + ev["cta"], 0.6)

mix = voice * 1.0 + music * 0.5 + sfx * 0.55
fade = np.minimum(1, np.linspace(0, 1, N) * (N / SR) / 0.4)               # boshida yumshoq kirish
tail = np.minimum(1, (N - np.arange(N)) / (0.8 * SR))                      # oxirida so'nish
mix = mix * fade * tail
peak = np.abs(mix).max()
mix = mix / peak * 0.89                                                   # ~ -1 dBFS
stereo = np.stack([mix, mix], axis=1)
with wave.open(str(W / "mix.wav"), "wb") as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR)
    f.writeframes((stereo * 32767).astype(np.int16).tobytes())
print("mix.wav", round(N / SR, 2), "s")
