"""Turn a GitHub avatar into an animated halftone (dotted) SVG.

Usage:  python scripts/halftone.py [github_username]
Output: assets/avatar-dark.svg, assets/avatar-light.svg
"""
import io, math, sys, urllib.request
from PIL import Image, ImageOps, ImageEnhance

USER = sys.argv[1] if len(sys.argv) > 1 else "Satish-970"
GRID = 56          # dots per row/column (higher = more detail)
CELL = 8           # px between dot centres
MAX_R = CELL * 0.52

req = urllib.request.Request(f"https://github.com/{USER}.png?size=460",
                             headers={"User-Agent": "halftone-script"})
img = Image.open(io.BytesIO(urllib.request.urlopen(req).read())).convert("L")
img = ImageOps.autocontrast(img, cutoff=2)
img = ImageEnhance.Contrast(img).enhance(1.25)
img = img.resize((GRID, GRID), Image.LANCZOS)
px = img.load()

SIZE = GRID * CELL
c = (GRID - 1) / 2

def build(dark: bool) -> str:
    color = "#58A6FF" if dark else "#0969DA"
    dots = []
    for y in range(GRID):
        for x in range(GRID):
            dist = math.hypot(x - c, y - c)
            if dist > GRID / 2:            # circular crop
                continue
            v = px[x, y] / 255
            v = v if dark else 1 - v       # dark bg: bright = big dot
            r = MAX_R * (v ** 0.9)
            if r < 0.5:
                continue
            delay = dist * 0.035           # ripple from the centre
            dots.append(
                f'<circle cx="{x*CELL+CELL/2}" cy="{y*CELL+CELL/2}" r="{r:.2f}" '
                f'style="animation-delay:{delay:.2f}s"/>'
            )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" width="320" height="320">
<style>
  circle {{ fill:{color}; opacity:0; animation: pop .6s ease-out forwards, breathe 5s ease-in-out 3s infinite; transform-box:fill-box; transform-origin:center; }}
  @keyframes pop {{ from {{ opacity:0; transform:scale(0); }} to {{ opacity:1; transform:scale(1); }} }}
  @keyframes breathe {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:.55; }} }}
</style>
{''.join(dots)}
</svg>'''

for name, dark in (("dark", True), ("light", False)):
    open(f"assets/avatar-{name}.svg", "w").write(build(dark))
print("done")
