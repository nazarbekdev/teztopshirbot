#!/usr/bin/env python3
"""2-reel tovushi: timeline2.json. Har xabar uchun "pop", demo faylida "ding", promoda "chime". Musiqa reel 1 bilan bir xil uslubda."""
import json, pathlib, subprocess, sys, wave
import numpy as np

W = pathlib.Path(sys.argv[1]); SR = 44100
tl = json.loads((W / "timeline2.json").read_text())
N = int((tl["total"] + 0.6) * SR)
rng = np.random.default_rng(11)

def tone(freq, dur, kind="sine", decay=6.0, amp=1.0):
    t = np.arange(int(dur * SR)) / SR
    f = freq if np.isscalar(freq) else np.interp(t, np.linspace(0, dur, len(freq)), freq)
    ph = 2 * np.pi * np.cumsum(f if not np.isscalar(f) else np.full_like(t, f)) / SR
    w = np.sin(ph) if kind == "sine" else (2 * (ph / (2 * np.pi) % 1) - 1) * 0.5 if kind == "saw" else np.sign(np.sin(ph)) * 0.4
    return amp * w * np.exp(-decay * t) * np.minimum(1, t * 400)

def add(buf, sig, at, gain=1.0):
    i = int(at * SR)
    if i < 0 or i >= len(buf): return
    sig = sig[: len(buf) - i]
    buf[i:i + len(sig)] += sig * gain

def noise_sweep(dur, amp=1.0):
    t = np.arange(int(dur * SR)) / SR
    n = rng.standard_normal(len(t))
    env = np.sin(np.pi * np.linspace(0, 1, len(t))) ** 1.5
    return amp * n * env * 0.3

def pop(freq=760): return tone(np.linspace(freq*0.75, freq*1.25, int(0.08*SR)), 0.08, decay=24, amp=0.55)
def ding(): return tone(1318.5, 0.5, decay=7, amp=0.7) + tone(1975.5, 0.5, decay=9, amp=0.45)
def chime():
    out = np.zeros(int(1.0*SR))
    for k,f in enumerate((784,988,1175,1568)): add(out, tone(f,0.7,decay=5,amp=0.55), k*0.07)
    return out

# musiqa (reel1 bilan bir xil, biroz sokinroq — dialog uzunroq)
music = np.zeros(N); bpm=104; beat=60/bpm
chords=[(220.0,[440,523.25,659.25,523.25]),(174.61,[349.23,440,523.25,440]),(261.63,[523.25,659.25,783.99,659.25]),(196.0,[392,493.88,587.33,493.88])]
t=0.0; bar=0
while t < tl["total"]+0.5:
    root,arp=chords[bar%4]
    add(music, tone(root/2, beat*3.6, "sine", decay=1.4, amp=0.45), t)
    for i in range(8): add(music, tone(arp[i%4],0.32,"saw",decay=7,amp=0.12), t+i*beat/2)
    for i in range(4):
        add(music, tone(np.linspace(130,48,int(0.16*SR)),0.16,decay=15,amp=0.75), t+i*beat, 0.5)
    t+=beat*4; bar+=1
music *= 0.5

def load_wav(p):
    with wave.open(str(p)) as f: return np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32)/32768

voice = np.zeros(N); spans=[]
for s in tl["scenes"]:
    wav = W/(s["name"]+".wav")
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(W/s["voice"]),"-ar",str(SR),"-ac","1",str(wav)],check=True)
    v = load_wav(wav); v = v/(np.abs(v).max()+1e-9)*0.92
    add(voice, v, s["voice_at"]); spans.append((s["voice_at"], s["voice_at"]+len(v)/SR))

duck = np.ones(N)
for a,b in spans: duck[int(a*SR):int(b*SR)] = 0.35
k = np.ones(int(0.12*SR))/int(0.12*SR); duck = np.convolve(duck,k,mode="same")
music *= duck

sfx = np.zeros(N)
for s in tl["scenes"]:
    add(sfx, pop(680 if s["speaker"]=="T" else 820), s["start"]+0.08, 0.6)
    if s["kind"]=="demo":
        add(sfx, noise_sweep(1.6,0.7), s["start"]+0.5, 0.3)
        add(sfx, ding(), s["start"]+2.2, 0.55)
    if s["kind"]=="promo":
        e=s["events"]
        add(sfx, chime(), s["start"]+0.1, 0.5)
        add(sfx, pop(1000), s["start"]+e["coupon"], 0.6)
        add(sfx, ding(), s["start"]+e["coupon"]+0.5, 0.4)

mix = voice*1.0 + music*0.5 + sfx*0.5
fade = np.minimum(1, np.linspace(0,1,N)*(N/SR)/0.4)
tail = np.minimum(1, (N-np.arange(N))/(0.8*SR))
mix = mix*fade*tail
mix = mix/np.abs(mix).max()*0.89
stereo = np.stack([mix,mix],axis=1)
with wave.open(str(W/"mix2.wav"),"wb") as f:
    f.setnchannels(2); f.setsampwidth(2); f.setframerate(SR); f.writeframes((stereo*32767).astype(np.int16).tobytes())
print("mix2.wav", round(N/SR,2),"s")
