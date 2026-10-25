# -*- coding: utf-8 -*-
"""Rede do fishnet, passo A (no Blender): exporta a geometria das pernas para fishnet_rede_campos.py.
  blender -b ARQ.blend -P fishnet_rede.py -- GEOM.npz

Por que uma rede nova: o fishnet antigo foi pintado em volta do eixo reto de cada perna; no pe,
que corre na horizontal, o angulo em volta desse eixo degenera e a rede vira riscos compridos.
Um eixo curvo (quadril-joelho-tornozelo-dedos) resolveu o peito do pe mas espremeu as celulas no
peito do pe (lado de dentro da curva) e inchou no calcanhar (2026-10-16). O passo B mede na pele:
distancia geodesica ao longo da perna e o angulo em volta do eixo curvo. Daqui ele precisa da
malha (so a parte principal: as unhas soltas ficariam sem fonte), do UV, dos pesos, do lado, de
t (abaixo da junta do quadril) e de theta, o angulo em volta do eixo curvo, num referencial
transportado sem giro (a frente da canela continua no peito do pe depois do tornozelo).
"""
import bpy, bmesh, sys, math, numpy as np

out = sys.argv[sys.argv.index('--') + 1]
arm = bpy.data.objects['Armature']; arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
b = bpy.data.objects['Body_Rigged']; me = b.data
nm = {g.index: g.name for g in b.vertex_groups if g.name in arm.data.bones}
H = lambda n: np.array(arm.matrix_world @ arm.data.bones[n].head_local)
T_ = lambda n: np.array(arm.matrix_world @ arm.data.bones[n].tail_local)
co = np.array([b.matrix_world @ v.co for v in me.vertices])


def curva(s):
    p = np.array([H('CC_Base_%s_Thigh' % s) * 1.3 - H('CC_Base_%s_Calf' % s) * .3, H('CC_Base_%s_Thigh' % s),
                  H('CC_Base_%s_Calf' % s), H('CC_Base_%s_Foot' % s), H('CC_Base_%s_ToeBase' % s), T_('CC_Base_%s_ToeBase' % s)])
    for _ in range(4):  # Chaikin, mantendo as pontas
        q = [p[0]]
        for i in range(len(p) - 1): q += [.75 * p[i] + .25 * p[i + 1], .25 * p[i] + .75 * p[i + 1]]
        p = np.array(q + [p[-1]])
    d = np.linalg.norm(np.diff(p, axis=0), axis=1); s_ = np.concatenate([[0], np.cumsum(d)])
    ss = np.arange(0, s_[-1], .002)
    p = np.stack([np.interp(ss, s_, p[:, k]) for k in range(3)], 1)
    tg = np.gradient(p, axis=0); tg /= np.linalg.norm(tg, axis=1, keepdims=True)
    n = np.zeros_like(p); r = np.array([0., -1., 0.]); r -= tg[0] * r.dot(tg[0]); n[0] = r / np.linalg.norm(r)
    for i in range(1, len(p)):  # transporte paralelo: gira o minimo a cada passo
        v = n[i - 1] - tg[i] * n[i - 1].dot(tg[i]); n[i] = v / np.linalg.norm(v)
    return p, tg, n, np.cross(tg, n)


lado = np.zeros(len(co), np.int8); legw = np.zeros(len(co)); armw = np.zeros(len(co)); tt = np.zeros(len(co))
eixo = {s: (H('CC_Base_%s_Thigh' % s), (H('CC_Base_%s_Calf' % s) - H('CC_Base_%s_Thigh' % s)) / np.linalg.norm(H('CC_Base_%s_Calf' % s) - H('CC_Base_%s_Thigh' % s))) for s in 'LR'}
for v in me.vertices:
    w = {nm[g.group]: g.weight for g in v.groups if g.group in nm and g.weight > 0}
    lado[v.index] = 1 if sum(x for k, x in w.items() if '_L_' in k) >= sum(x for k, x in w.items() if '_R_' in k) else 0
    tot = sum(w.values()) or 1
    legw[v.index] = sum(x for k, x in w.items() if any(q in k for q in ('Thigh', 'Calf', 'Knee', 'Foot', 'Toe'))) / tot
    armw[v.index] = sum(x for k, x in w.items() if any(q in k for q in ('Upperarm', 'Forearm', 'Hand', 'Thumb', 'Index', 'Mid', 'Ring', 'Pinky'))) / tot
    o_, e_ = eixo['L' if lado[v.index] else 'R']; tt[v.index] = (co[v.index] - o_) @ e_  # abaixo da junta do quadril (m), como fishnet_pernas_uv.py
TH = np.zeros(len(co))
for k, s in ((1, 'L'), (0, 'R')):
    p, tg, n, bn = curva(s)
    idx = np.where(lado == k)[0]; c = co[idx]
    j = np.concatenate([np.argmin(((c[i:i + 4000, None, :] - p[None]) ** 2).sum(-1), 1) for i in range(0, len(c), 4000)])
    d = c - p[j]; d -= tg[j] * (d * tg[j]).sum(1, keepdims=True)
    TH[idx] = np.arctan2((d * bn[j]).sum(1), (d * n[j]).sum(1))

# parte principal (as unhas e o cabelo solto ficam fora)
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
visto = np.zeros(len(co), bool); maior = []
for v in bm.verts:
    if visto[v.index]: continue
    pilha, comp = [v], []; visto[v.index] = True
    while pilha:
        x = pilha.pop(); comp.append(x.index)
        for e in x.link_edges:
            y = e.other_vert(x)
            if not visto[y.index]: visto[y.index] = True; pilha.append(y)
    if len(comp) > len(maior): maior = comp
principal = np.zeros(len(co), bool); principal[maior] = True

uvl = me.uv_layers['Channel0']; me.calc_loop_triangles()
tv = np.array([tuple(t.vertices) for t in me.loop_triangles], np.int32)
tuv = np.array([[tuple(uvl.data[l].uv) for l in t.loops] for t in me.loop_triangles], np.float32)
np.savez_compressed(out, co=co, tv=tv, tuv=tuv, legw=legw, armw=armw, lado=lado, theta=TH, t=tt, principal=principal)
print('FISHNET_GEOM', out, '%d vertices (%d na parte principal), %d triangulos' % (len(co), principal.sum(), len(tv)))
