# -*- coding: utf-8 -*-
"""Pinta as unhas na textura do corpo.  python unhas_compor.py UNHAS.json ENTRADA.png SAIDA.png [R,G,B]

Cor bordo por padrao. Mantem o sombreado da textura (a luminancia original, suavizada,
modula a cor) e dilata 3 px alem da borda da ilha UV para nao sobrar costura de pele.
"""
import sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
Image.MAX_IMAGE_PIXELS = None
unhas, ent, sai = sys.argv[1:4]
cor = np.array([float(x) for x in (sys.argv[4] if len(sys.argv) > 4 else '96,10,28').split(',')])
im = Image.open(ent).convert('RGBA'); W, H = im.size
mask = Image.new('L', (W, H), 0); d = ImageDraw.Draw(mask)
for ilhas in json.load(open(unhas)).values():
    for tris in ilhas:
        for f in tris:
            d.polygon([(u * W, (1 - v) * H) for u, v in f], fill=255)
mask = mask.filter(ImageFilter.MaxFilter(7))
m = np.asarray(mask) > 0
a = np.asarray(im).astype(float)
lum = a[..., :3].mean(2); ref = np.median(lum[m])
fator = np.clip((lum / ref) ** .6, .6, 1.4)
a[m, :3] = np.clip(cor[None, :] * fator[m][:, None], 0, 255)
Image.fromarray(a.astype(np.uint8)).save(sai)
print('  %d texels pintados em %s' % (m.sum(), sai))
