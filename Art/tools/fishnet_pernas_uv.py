# -*- coding: utf-8 -*-
"""Fishnet so nas pernas (Sophia, 2026-10-16), passo 1 de 2, no Blender:
  blender -b ARQ.blend -P fishnet_pernas_uv.py -- SAIDA.npz
Rasteriza no UV Channel0 do corpo (4096) dois campos por vertice, interpolados no triangulo:
  perna = fracao do peso em ossos de perna (Thigh/Calf/Knee/Foot/Toe), sem o cabelo
  t     = distancia ao longo do eixo da coxa abaixo da junta do quadril (do lado do vertice)
  x     = distancia a linha do meio do corpo; y = para tras da junta (+ e costas)
  braco = fracao do peso em ossos de braco (as maos pendem ao lado da coxa); z = altura (m)
O fishnet antigo foi pintado em volta do eixo de cada perna em 3D e pegou as maos (no A-pose
elas pendem na altura da coxa), a barriga e a vulva. Peso de perna >= 0,5 para no vinco da
virilha; a vulva e o perineo tem peso de pelvis e ficam fora. Passo 2: fishnet_pernas_compor.py.
"""
import bpy, sys, numpy as np
out = sys.argv[sys.argv.index('--') + 1]
S = 4096
arm = bpy.data.objects['Armature']; arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
b = bpy.data.objects['Body_Rigged']; me = b.data
nm = {g.index: g.name for g in b.vertex_groups if g.name in arm.data.bones}
H = lambda n: arm.matrix_world @ arm.data.bones[n].head_local
ax = {s: (H('CC_Base_%s_Thigh' % s), (H('CC_Base_%s_Calf' % s) - H('CC_Base_%s_Thigh' % s)).normalized()) for s in 'LR'}
leg = np.zeros(len(me.vertices)); tt = np.zeros(len(me.vertices)); xx_ = np.zeros(len(me.vertices)); yy_ = np.zeros(len(me.vertices)); aa_ = np.zeros(len(me.vertices)); zz_ = np.zeros(len(me.vertices))
for v in me.vertices:
    w = {nm[g.group]: g.weight for g in v.groups if g.group in nm and g.weight > 0}
    tot = sum(w.values()) or 1
    if not any('Hair' in n for n in w):
        leg[v.index] = sum(x for n, x in w.items() if any(k in n for k in ('Thigh', 'Calf', 'Knee', 'Foot', 'Toe'))) / tot
    s = 'L' if sum(x for n, x in w.items() if '_L_' in n) >= sum(x for n, x in w.items() if '_R_' in n) else 'R'
    tt[v.index] = (b.matrix_world @ v.co - ax[s][0]).dot(ax[s][1]); xx_[v.index] = abs((b.matrix_world @ v.co).x)
    yy_[v.index] = (b.matrix_world @ v.co).y - ax['L'][0].y; zz_[v.index] = (b.matrix_world @ v.co).z
    aa_[v.index] = sum(x for n, x in w.items() if any(k in n for k in ('Upperarm', 'Forearm', 'Hand', 'Thumb', 'Index', 'Mid', 'Ring', 'Pinky'))) / tot
uv = me.uv_layers['Channel0']
me.calc_loop_triangles()
L = np.full((S, S), -1.0, np.float32); T = np.zeros((S, S), np.float32); X = np.zeros((S, S), np.float32); Y = np.zeros((S, S), np.float32); Am = np.zeros((S, S), np.float32); Z = np.zeros((S, S), np.float32)
for tri in me.loop_triangles:
    vs = list(tri.vertices)
    p = np.array([tuple(uv.data[l].uv) for l in tri.loops]) * S
    x0, x1 = max(0, int(p[:, 0].min())), min(S, int(np.ceil(p[:, 0].max())) + 1)
    y0, y1 = max(0, int(p[:, 1].min())), min(S, int(np.ceil(p[:, 1].max())) + 1)
    if x0 >= x1 or y0 >= y1: continue
    a, bb, c = p; den = (bb[1] - c[1]) * (a[0] - c[0]) + (c[0] - bb[0]) * (a[1] - c[1])
    if abs(den) < 1e-12: continue
    yy, xx = np.mgrid[y0:y1, x0:x1] + .5
    wa = ((bb[1] - c[1]) * (xx - c[0]) + (c[0] - bb[0]) * (yy - c[1])) / den
    wb = ((c[1] - a[1]) * (xx - c[0]) + (a[0] - c[0]) * (yy - c[1])) / den
    wc = 1 - wa - wb
    inside = (wa >= -1e-4) & (wb >= -1e-4) & (wc >= -1e-4)
    L[y0:y1, x0:x1][inside] = (wa * leg[vs[0]] + wb * leg[vs[1]] + wc * leg[vs[2]])[inside]
    T[y0:y1, x0:x1][inside] = (wa * tt[vs[0]] + wb * tt[vs[1]] + wc * tt[vs[2]])[inside]
    X[y0:y1, x0:x1][inside] = (wa * xx_[vs[0]] + wb * xx_[vs[1]] + wc * xx_[vs[2]])[inside]
    Y[y0:y1, x0:x1][inside] = (wa * yy_[vs[0]] + wb * yy_[vs[1]] + wc * yy_[vs[2]])[inside]
    Am[y0:y1, x0:x1][inside] = (wa * aa_[vs[0]] + wb * aa_[vs[1]] + wc * aa_[vs[2]])[inside]
    Z[y0:y1, x0:x1][inside] = (wa * zz_[vs[0]] + wb * zz_[vs[1]] + wc * zz_[vs[2]])[inside]
# UV de baixo para cima; a imagem e de cima para baixo
np.savez_compressed(out, leg=L[::-1], t=T[::-1], x=X[::-1], y=Y[::-1], braco=Am[::-1], z=Z[::-1])
print('FISHNET_UV', out, 'pixels cobertos', int((L >= 0).sum()))
