import re, os, sys
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), 'assets', 'fonts')
OUT = os.path.join(HERE, 'build', 'fonts')
os.makedirs(OUT, exist_ok=True)
css = open(f'{SRC}/fonts.css', encoding='utf-8').read()
faces = re.findall(r"@font-face \{(.*?)\}", css, re.S)
out_css = []
for f in faces:
    fam = re.search(r"font-family: '([^']+)'", f).group(1)
    style = re.search(r"font-style: (\w+)", f).group(1)
    wt = re.search(r"font-weight: ([\d ]+);", f).group(1).split()
    src = re.search(r"url\('([^']+)'\)", f).group(1)
    rng = re.search(r"unicode-range: ([^;]+);", f).group(1)
    font = TTFont(f'{SRC}/{src}')
    weights = [400, 700] if len(wt) == 2 else [int(wt[0])]
    for w in weights:
        if len(wt) == 2:
            lo, hi = map(int, wt)
            if not lo <= w <= hi: continue
            inst = instancer.instantiateVariableFont(TTFont(f'{SRC}/{src}'), {'wght': w})
        else:
            inst = TTFont(f'{SRC}/{src}')
        inst.flavor = None
        name = f"{src[:-6]}-{w}.ttf"
        inst.save(f'{OUT}/{name}')
        out_css.append(f"@font-face {{ font-family: '{fam}'; font-style: {style}; font-weight: {w}; src: url('{name}') format('truetype'); unicode-range: {rng}; }}")
open(f'{OUT}/book-fonts.css', 'w').write('\n'.join(out_css) + '\n')
print(len(out_css), 'faces')
