#!/usr/bin/env python3
"""reel.html ni kadrma-kadr suratga oladi (Chrome, 1080×1920, 30 fps). Ishlatish: render_frames.py <ishchi_papka> [fps] [t0 t1]"""
import json, pathlib, sys
from playwright.sync_api import sync_playwright

work = pathlib.Path(sys.argv[1])
fps = int(sys.argv[2]) if len(sys.argv) > 2 else 30
tl = json.loads((work / "timeline.json").read_text())
here = pathlib.Path(__file__).parent
html = (here / "reel.html").read_text().replace("/*TIMELINE*/null", json.dumps(tl, ensure_ascii=False))
(work / "reel_built.html").write_text(html)
for name in ("logo.png",):
    if (here / name).exists():
        (work / name).write_bytes((here / name).read_bytes())
frames = work / "frames"
frames.mkdir(exist_ok=True)
t0 = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
t1 = float(sys.argv[4]) if len(sys.argv) > 4 else tl["total"]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=1)
    page.goto((work / "reel_built.html").as_uri())
    page.wait_for_timeout(500)
    n0, n1 = int(t0 * fps), int(t1 * fps)
    for i in range(n0, n1):
        page.evaluate(f"render({i / fps})")
        page.screenshot(path=str(frames / f"f{i:05d}.jpg"), type="jpeg", quality=92)
        if i % 90 == 0:
            print("kadr", i, "/", int(tl["total"] * fps), flush=True)
    browser.close()
