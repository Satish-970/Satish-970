import random, urllib.request

name = "Satish Pakalapati"
desc = "Data Scientist | Full Stack Developer | AI Enthusiast"

# ONLY professional palettes (carefully selected)
palettes = [
    "12,24,30",   # royal purple blue
    "6,17,38",    # indigo electric
    "20,14,30",   # navy violet
    "2,20,27",    # deep blue modern
    "5,12,18",    # subtle tech gradient
]

palette = random.choice(palettes)

url = f"https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList={palette}&height=220&section=header&text={name.replace(' ','%20')}&fontSize=48&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc={desc.replace(' ','%20').replace('|','%7C')}&descSize=18&descAlignY=55"

urllib.request.urlretrieve(url, "banner.svg")
