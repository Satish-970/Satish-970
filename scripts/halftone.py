"""Generate an animated halftone hero card (living dotted portrait + profile info).

Usage:  python scripts/halftone.py [github_username]
Output: assets/hero-dark.svg, assets/hero-light.svg
"""
import io, json, math, os, random, sys, urllib.request
from xml.sax.saxutils import escape
from PIL import Image, ImageOps, ImageEnhance

USER = sys.argv[1] if len(sys.argv) > 1 else "Satish-970"

# ───────────── edit the card text here ─────────────
HOST = "github"
INFO = [
    ("role",     "Data Scientist · Full Stack Developer"),
    ("base",     "Vijayawada, Andhra Pradesh, India"),
    ("langs",    "Python · Java · JavaScript · C · R"),
    ("ml",       "scikit-learn · TensorFlow · Pandas"),
    ("big data", "Hadoop · Spark · Tableau"),
    ("web",      "Spring Boot · React · Node.js"),
    ("learning", "Deep Learning · Cloud · DevOps"),
    ("fuel",     "Coffee"),
]
CYCLE = 40                          # seconds for one full colour flow (bigger = slower)
OFFSET = random.uniform(0, CYCLE)   # new starting colours every time the script runs
LOOP = 14.0                         # seconds for one full cycle: clear picture -> scatter -> clear picture
HOLD = 0.35                         # share of the cycle where the dots sit perfectly in place (0.35 = 35%)
DRIFT = 1.0                         # how far each dot swirls while scattered (2.0 = double)
WAVE = 6.0                          # height of the rolling wave while scattered, in pixels (0 = none)
# ────────────────────────────────────────────────────

GRID, CELL = 80, 5.4            # dots per side, spacing  (bigger GRID = sharper)
MIN_R, MAX_R = 0.75, CELL * 0.52
VARIANTS = 6                    # different swirl patterns inside every wave band
BANDS = 24                      # the wave travels across the portrait in this many strips
PAD = 14
PORT = GRID * CELL
W, H = 980, int(PORT + 2 * PAD)

PALETTES = {
    "dark":  dict(colors=["#58A6FF", "#A371F7", "#F778BA", "#FFA657", "#3FB950"],
                  text="#C9D1D9", card="#161B22", border="#30363D"),
    "light": dict(colors=["#0969DA", "#8250DF", "#BF3989", "#BC4C00", "#1A7F37"],
                  text="#24292F", card="#F6F8FA", border="#D0D7DE"),
}

# ── data ──
def load_avatar():
    path = os.environ.get("AVATAR_FILE")
    if path:
        return Image.open(path)
    req = urllib.request.Request(f"https://github.com/{USER}.png?size=600",
                                 headers={"User-Agent": "halftone-script"})
    return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=20).read()))

def load_stats():
    try:
        h = {"User-Agent": "halftone-script"}
        if os.environ.get("GH_TOKEN"):
            h["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
        r = urllib.request.Request(f"https://api.github.com/users/{USER}", headers=h)
        d = json.load(urllib.request.urlopen(r, timeout=15))
        return [("repos", f"{d['public_repos']} public"), ("followers", str(d["followers"]))]
    except Exception as e:
        print("stats skipped:", e)
        return []

avatar = load_avatar().convert("L")
side = min(avatar.size)
avatar = avatar.crop(((avatar.width - side)//2, (avatar.height - side)//2,
                      (avatar.width + side)//2, (avatar.height + side)//2))
avatar = ImageOps.autocontrast(avatar, cutoff=1)
avatar = Image.blend(avatar, ImageOps.equalize(avatar), 0.5)
avatar = ImageEnhance.Contrast(avatar).enhance(1.15)
avatar = avatar.resize((GRID, GRID), Image.LANCZOS)
px = avatar.load()

info = INFO + load_stats()

# motion: every group rests at (0,0) for the HOLD part of the cycle, then wanders and returns to (0,0)
STEPS = 24

def path(ax, ay, loops, phase, d):
    pts = ["0%{transform:translate(0px,0px)}"]
    for j in range(STEPS + 1):
        t = j / STEPS
        env = math.sin(math.pi * t)                 # 0 at both ends, so dots always return home
        ang = d * 2 * math.pi * loops * t + phase
        pct = (HOLD + (1 - HOLD) * t) * 100
        pts.append(f"{pct:.2f}%{{transform:translate({ax*env*math.cos(ang):.2f}px,{ay*env*math.sin(ang):.2f}px)}}")
    return "".join(pts)

_rng = random.Random(42)
variants = [dict(ax=_rng.uniform(2.5, 6.0) * DRIFT, ay=_rng.uniform(2.5, 6.0) * DRIFT,
                 loops=_rng.choice((1, 2)), phase=_rng.uniform(0, 2 * math.pi),
                 d=_rng.choice((1, -1))) for _ in range(VARIANTS)]

def motion_css():
    out = []
    for i, v in enumerate(variants):
        out.append(f"@keyframes o{i}{{{path(v['ax'], v['ay'], v['loops'], v['phase'], v['d'])}}}"
                   f".m{i}{{animation:o{i} {LOOP}s linear infinite}}")
    for b in range(BANDS):                          # rolling wave: each strip is a little behind the last
        out.append(f"@keyframes w{b}{{{path(WAVE, WAVE, 2, b * 2 * math.pi * 1.5 / BANDS, 1)}}}"
                   f".w{b}{{animation:w{b} {LOOP}s linear infinite}}")
    return "".join(out)

def build(theme: str) -> str:
    p = PALETTES[theme]
    dark = theme == "dark"
    c = (GRID - 1) / 2
    rng = random.Random(1)

    groups = [[[] for _ in range(VARIANTS)] for _ in range(BANDS)]
    for y in range(GRID):
        for x in range(GRID):
            if math.hypot(x - c, y - c) > GRID / 2:
                continue
            v = px[x, y] / 255
            v = v if dark else 1 - v
            r = MIN_R + (MAX_R - MIN_R) * (v ** 0.8)
            band = min(BANDS - 1, int((x + y) / (2 * (GRID - 1)) * BANDS))
            groups[band][rng.randrange(VARIANTS)].append(
                f'<circle cx="{PAD + x*CELL + CELL/2:.1f}" cy="{PAD + y*CELL + CELL/2:.1f}" r="{r:.2f}"/>')

    cols = p["colors"] + [p["colors"][0]]
    stops = "".join(f'<stop offset="{i/(len(cols)-1):.3f}" stop-color="{col}"/>' for i, col in enumerate(cols))
    kf = "".join(f"{round(i*100/(len(cols)-1))}%{{fill:{col}}}" for i, col in enumerate(cols))

    # text card geometry
    n = len(info)
    row = min(38, (PORT - 88) / n)
    card_h = 40 + 24 + n * row + 24
    top = PAD + (PORT - card_h) / 2
    cx0 = PAD + PORT + 30
    card_w = W - cx0 - PAD
    kx, vx = cx0 + 30, cx0 + 30 + 112
    y0 = top + 46
    lines = []
    for i, (k, v) in enumerate(info):
        y = y0 + 40 + i * row
        lines.append(
            f'<g class="ln" style="animation-delay:{0.6 + i*0.18:.2f}s">'
            f'<text x="{kx}" y="{y:.0f}" class="t k" style="animation-delay:-{i*CYCLE/12 + OFFSET:.1f}s">{escape(k)}</text>'
            f'<text x="{vx}" y="{y:.0f}" class="t v">{escape(v)}</text></g>')
    last_y = y0 + 40 + (n - 1) * row
    cursor_y = last_y + row - 13

    dots = ""
    for b, band in enumerate(groups):
        inner = "".join(f'<g class="m{i}">' + "".join(g) + '</g>' for i, g in enumerate(band) if g)
        dots += f'<g class="w{b}">{inner}</g>'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Living dotted portrait and profile card">
<defs>
<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="{PAD}" y1="{PAD}" x2="{PAD + PORT:.0f}" y2="{PAD + PORT:.0f}" spreadMethod="repeat">
{stops}
<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="{PORT:.0f} {PORT:.0f}" dur="{CYCLE}s" begin="-{OFFSET:.1f}s" repeatCount="indefinite"/>
</linearGradient>
</defs>
<style>
.t{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-size:15px}}
.v{{fill:{p["text"]}}}
.k{{font-weight:700;animation:wave {CYCLE}s linear infinite}}
.all{{animation:reveal 1.6s ease-out both}}
.ln{{opacity:0;animation:slide .6s ease-out forwards}}
.cur{{animation:blink 1s steps(2,start) infinite}}
{motion_css()}
@keyframes wave{{{kf}}}
@keyframes reveal{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes slide{{from{{opacity:0;transform:translateX(16px)}}to{{opacity:1;transform:translateX(0)}}}}
@keyframes blink{{to{{visibility:hidden}}}}
</style>
<g class="all" fill="url(#g)">{dots}</g>
<rect x="{cx0}" y="{top:.0f}" width="{card_w}" height="{card_h:.0f}" rx="14" fill="{p["card"]}" stroke="{p["border"]}"/>
<text x="{kx}" y="{y0:.0f}" class="t" style="font-size:18px;font-weight:700"><tspan class="k" style="animation-delay:-{OFFSET:.1f}s">{escape(USER.lower())}</tspan><tspan class="v">@</tspan><tspan class="k" style="animation-delay:-{3 + OFFSET:.1f}s">{HOST}</tspan></text>
<line x1="{kx}" y1="{y0+14:.0f}" x2="{cx0+card_w-30}" y2="{y0+14:.0f}" stroke="{p["border"]}" stroke-width="1.5"/>
{"".join(lines)}
<rect class="cur k" x="{kx}" y="{cursor_y:.0f}" width="9" height="17" style="animation-delay:-{5 + OFFSET:.1f}s"/>
</svg>'''

os.makedirs("assets", exist_ok=True)
for theme in ("dark", "light"):
    with open(f"assets/hero-{theme}.svg", "w", encoding="utf-8") as f:
        f.write(build(theme))
print("done")
