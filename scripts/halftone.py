"""Generate an animated halftone hero card (living dotted portrait + profile info).

Usage:  python scripts/halftone.py [github_username]
Output: assets/hero-<style>-<colour>-dark.svg and ...-light.svg
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
COLOR = "photo"                     # "photo" = colours copied from your profile picture   |   "gradient" = flowing rainbow
STYLE = "code"                      # "code" = 0/1, letters & symbols   |   "dots" = round halftone dots
LOOP = 14.0                         # seconds for one full cycle: clear picture -> scatter -> clear picture
HOLD = 1.0                         # share of the cycle where the dots sit perfectly in place (0.35 = 35%)
DRIFT = 1.0                         # how far each dot swirls while scattered (2.0 = double)
WAVE = 6.0                          # height of the rolling wave while scattered, in pixels (0 = none)
# ────────────────────────────────────────────────────

GRID, CELL = (64, 6.75) if STYLE == "code" else (80, 5.4)   # cells per side, spacing (bigger GRID = sharper)
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

raw = load_avatar().convert("RGB")
side = min(raw.size)
raw = raw.crop(((raw.width - side)//2, (raw.height - side)//2,
                (raw.width + side)//2, (raw.height + side)//2))
avatar = raw.convert("L")
avatar = ImageOps.autocontrast(avatar, cutoff=1)
avatar = Image.blend(avatar, ImageOps.equalize(avatar), 0.5)
avatar = ImageEnhance.Contrast(avatar).enhance(1.15)
avatar = avatar.resize((GRID, GRID), Image.LANCZOS)
px = avatar.load()

# ── colours copied from the photo ──
import colorsys
cimg = raw.resize((GRID, GRID), Image.LANCZOS)
cpx = cimg.load()

def _hex(r, g, b):
    return "#%02x%02x%02x" % (round(r * 255), round(g * 255), round(b * 255))

def photo_color(x, y, dark):
    """The photo's own colour for this cell, lifted/dimmed so it stays visible on the page background."""
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in cpx[x, y]))
    s = min(1.0, s * 1.25)
    v = (0.50 + 0.50 * v) if dark else (0.12 + 0.55 * v)
    return _hex(*colorsys.hsv_to_rgb(h, s, v))

def dominant_hues(n=5):
    q = cimg.resize((64, 64)).quantize(colors=12)
    pal, found = q.getpalette(), sorted(q.getcolors(), reverse=True)
    out = []
    for _, i in found:
        h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in pal[i*3:i*3+3]))
        if s < 0.25 or v < 0.2:
            continue                                   # skip greys / near-black
        if any(min(abs(h - o), 1 - abs(h - o)) < 0.07 for o in out):
            continue                                   # skip near-duplicate hues
        out.append(h)
        if len(out) == n:
            break
    return out

if COLOR == "photo":
    hues = dominant_hues()
    if len(hues) >= 2:
        hues = (hues * 5)[:5]
        PALETTES["dark"]["colors"] = [_hex(*colorsys.hsv_to_rgb(h, 0.55, 1.0)) for h in hues]
        PALETTES["light"]["colors"] = [_hex(*colorsys.hsv_to_rgb(h, 0.85, 0.62)) for h in hues]
        print("palette from photo:", PALETTES["dark"]["colors"])
    else:
        print("photo has no strong colours - keeping default palette for text")

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

RAMP_A = [".", ":", "1", "0", "+", "7", "X", "A", "M", "#", "@"]   # dark -> bright
RAMP_B = [",", ";", "0", "1", "x", "2", "K", "V", "W", "%", "&"]   # flicker twins of the above

def code_layers(dark: bool):
    """Characters grouped by column. Columns slide like falling code, flicker, then lock back into place."""
    rng = random.Random(7)
    fs = CELL * 1.1
    c = (GRID - 1) / 2
    css, out = [], []
    for x in range(GRID):
        xs, ys, ca, cb, cc = [], [], [], [], []
        for y in range(GRID):
            if math.hypot(x - c, y - c) > GRID / 2:
                continue
            v = px[x, y] / 255
            v = (v if dark else 1 - v) ** 0.9
            k = min(len(RAMP_A) - 1, int(v * len(RAMP_A)))
            xs.append(f"{PAD + x*CELL + CELL/2:.1f}")
            ys.append(f"{PAD + y*CELL + CELL/2 + fs*0.35:.1f}")
            ca.append(RAMP_A[k]); cb.append(RAMP_B[k])
            cc.append(f' fill="{photo_color(x, y, dark)}"' if COLOR == "photo" else "")
        if not xs:
            continue
        # slide: mostly vertical, back home during HOLD and at the end of the loop
        css.append(f"@keyframes c{x}{{{path(rng.uniform(1.5, 4) * DRIFT, rng.uniform(14, 42) * DRIFT, rng.choice((1, 2)), rng.uniform(0, 6.28), rng.choice((1, -1)))}}}"
                   f".c{x}{{animation:c{x} {LOOP}s linear infinite}}")
        # flicker: swap between the two glyph layers a few times, always ends on layer A
        times = sorted(rng.uniform(HOLD + 0.04, 0.96) * 100 for _ in range(6))
        ka = f"0%{{opacity:1}}{HOLD*100:.1f}%{{opacity:1}}" + "".join(
            f"{t:.1f}%{{opacity:{1 if (i + 1) % 2 == 0 else 0}}}" for i, t in enumerate(times)) + "100%{opacity:1}"
        kb = f"0%{{opacity:0}}{HOLD*100:.1f}%{{opacity:0}}" + "".join(
            f"{t:.1f}%{{opacity:{0 if (i + 1) % 2 == 0 else 1}}}" for i, t in enumerate(times)) + "100%{opacity:0}"
        css.append(f"@keyframes a{x}{{{ka}}}.a{x}{{animation:a{x} {LOOP}s step-end infinite}}"
                   f"@keyframes b{x}{{{kb}}}.b{x}{{animation:b{x} {LOOP}s step-end infinite}}")
        def layer(chars):   # one explicit position per character: renders identically everywhere
            return "".join(f'<tspan x="{a}" y="{b}"{f}>{escape(ch)}</tspan>' for a, b, ch, f in zip(xs, ys, chars, cc))
        out.append(f'<g class="c{x}"><text class="cd a{x}">{layer(ca)}</text>'
                   f'<text class="cd b{x}">{layer(cb)}</text></g>')
    css.append(f'.cd{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;'
               f'font-size:{fs:.1f}px;font-weight:700;text-anchor:middle}}')
    return "".join(out), "".join(css)

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
                f'<circle cx="{PAD + x*CELL + CELL/2:.1f}" cy="{PAD + y*CELL + CELL/2:.1f}" r="{r:.2f}"'
                + (f' fill="{photo_color(x, y, dark)}"' if COLOR == "photo" else "") + '/>')

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

    if STYLE == "code":
        dots, style_css = code_layers(dark)
    else:
        dots = ""
        for b, band in enumerate(groups):
            inner = "".join(f'<g class="m{i}">' + "".join(g) + '</g>' for i, g in enumerate(band) if g)
            dots += f'<g class="w{b}">{inner}</g>'
        style_css = motion_css()

    if COLOR == "photo":
        defs, gfill = "", ""
    else:
        defs = (f'<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="{PAD}" y1="{PAD}" x2="{PAD + PORT:.0f}" y2="{PAD + PORT:.0f}" spreadMethod="repeat">'
                f'{stops}<animateTransform attributeName="gradientTransform" type="translate" from="0 0" to="{PORT:.0f} {PORT:.0f}" '
                f'dur="{CYCLE}s" begin="-{OFFSET:.1f}s" repeatCount="indefinite"/></linearGradient></defs>')
        gfill = ' fill="url(#g)"'

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Animated portrait and profile card">
{defs}
<style>
.t{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-size:15px}}
.v{{fill:{p["text"]}}}
.k{{font-weight:700;animation:wave {CYCLE}s linear infinite}}
.all{{animation:reveal 1.6s ease-out both}}
.ln{{opacity:0;animation:slide .6s ease-out forwards}}
.cur{{animation:blink 1s steps(2,start) infinite}}
{style_css}
@keyframes wave{{{kf}}}
@keyframes reveal{{from{{opacity:0}}to{{opacity:1}}}}
@keyframes slide{{from{{opacity:0;transform:translateX(16px)}}to{{opacity:1;transform:translateX(0)}}}}
@keyframes blink{{to{{visibility:hidden}}}}
</style>
<g class="all"{gfill}>{dots}</g>
<rect x="{cx0}" y="{top:.0f}" width="{card_w}" height="{card_h:.0f}" rx="14" fill="{p["card"]}" stroke="{p["border"]}"/>
<text x="{kx}" y="{y0:.0f}" class="t" style="font-size:18px;font-weight:700"><tspan class="k" style="animation-delay:-{OFFSET:.1f}s">{escape(USER.lower())}</tspan><tspan class="v">@</tspan><tspan class="k" style="animation-delay:-{3 + OFFSET:.1f}s">{HOST}</tspan></text>
<line x1="{kx}" y1="{y0+14:.0f}" x2="{cx0+card_w-30}" y2="{y0+14:.0f}" stroke="{p["border"]}" stroke-width="1.5"/>
{"".join(lines)}
<rect class="cur k" x="{kx}" y="{cursor_y:.0f}" width="9" height="17" style="animation-delay:-{5 + OFFSET:.1f}s"/>
</svg>'''

import glob
os.makedirs("assets", exist_ok=True)
keep = {f"assets/hero-{STYLE}-{COLOR}-{t}.svg" for t in ("dark", "light")}
for old in glob.glob("assets/hero-*.svg") + glob.glob("assets/avatar-*.svg"):
    if old not in keep:                      # remove files from older versions
        os.remove(old)
for theme in ("dark", "light"):
    with open(f"assets/hero-{STYLE}-{COLOR}-{theme}.svg", "w", encoding="utf-8") as f:
        f.write(build(theme))
print(f"done: style={STYLE}, color={COLOR}, files={sorted(keep)}")
