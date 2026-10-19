import json, pathlib, sys
from playwright.sync_api import sync_playwright
work = pathlib.Path(sys.argv[1]); fps=int(sys.argv[2]) if len(sys.argv)>2 else 30
tl = json.loads((work/"timeline2.json").read_text())
html = (pathlib.Path(pathlib.Path(__file__).parent / "reel2.html")).read_text().replace("/*TIMELINE*/null", json.dumps(tl, ensure_ascii=False))
(work/"reel2_built.html").write_text(html)
t0=float(sys.argv[3]) if len(sys.argv)>3 else 0.0
t1=float(sys.argv[4]) if len(sys.argv)>4 else tl["total"]
with sync_playwright() as p:
    b=p.chromium.launch(channel="chrome"); pg=b.new_page(viewport={"width":1080,"height":1920})
    pg.goto((work/"reel2_built.html").as_uri()); pg.wait_for_timeout(400)
    frames=work/"frames2"; frames.mkdir(exist_ok=True)
    n0,n1=int(t0*fps),int(t1*fps)
    for i in range(n0,n1):
        pg.evaluate(f"render({i/fps})"); pg.screenshot(path=str(frames/f"f{i:05d}.jpg"),type="jpeg",quality=92)
        if i%90==0: print("kadr",i,flush=True)
    b.close()
