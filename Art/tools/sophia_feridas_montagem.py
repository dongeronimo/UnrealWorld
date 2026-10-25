"""Montage of the preview renders: one row per view, one column per HP."""
import sys, os, glob
from PIL import Image, ImageDraw
D = sys.argv[1]; views = sys.argv[2].split(',')
hps = sorted({f[-7:-4] for f in os.listdir(D) if '_hp' in f}, reverse=True)
for v in views:
    ims = [Image.open(os.path.join(D, '%s_hp%s.png' % (v, h))).convert('RGB') for h in hps]
    w, h = ims[0].size; M = Image.new('RGB', (w * len(ims), h + 22), (20, 20, 20)); dr = ImageDraw.Draw(M)
    for i, (im, hp) in enumerate(zip(ims, hps)):
        M.paste(im, (i * w, 22)); dr.text((i * w + 8, 5), '%s  HP %d%%' % (v, int(hp)), fill=(230, 230, 230))
    M.save(os.path.join(D, 'montagem_%s.png' % v))
