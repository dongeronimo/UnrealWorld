# -*- coding: utf-8 -*-
"""Triangulos UV das unhas do Body_Rigged, para pintar (unhas_compor.py).

  blender -b ARQ.blend -P unhas_uv.py -- SAIDA.json

A textura nunca pintou as unhas da Sophia (a cor ali e a da pele desde
Sophia_uv_unica.png). Cada unha e uma placa com a sua propria ilha UV (~56 faces); 16 sao
partes soltas, mas a do anelar e a de um dedo do pe estao fundidas na malha principal, entao
o criterio e a ilha UV, nao a parte solta: ilha de ate 80 faces cujos vertices tem como osso
dominante a falange distal de um dedo ou o ToeBase. Pega tambem os fragmentos de 1-2 faces
que sobraram da ilha de uma unha do pe.
"""
import bpy, bmesh, sys, json, collections
saida = sys.argv[sys.argv.index('--') + 1]
o = bpy.data.objects['Body_Rigged']; me = o.data
bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
uv = bm.loops.layers.uv['Channel0']
nomes = {g.index: g.name for g in o.vertex_groups}
dom = [max([(g.weight, nomes[g.group]) for g in v.groups] or [(0, '')])[1].replace('CC_Base_', '') for v in me.vertices]
ch = lambda l: (round(l[uv].uv.x, 5), round(l[uv].uv.y, 5))
visto, ilhas = set(), []
for f in bm.faces:
    if f.index in visto: continue
    pilha, comp = [f], []; visto.add(f.index)
    while pilha:
        x = pilha.pop(); comp.append(x)
        for l in x.loops:
            for lg in l.edge.link_loops:
                g = lg.face
                if g.index in visto: continue
                # mesma ilha so se a aresta tem a mesma UV nas duas faces (sem costura)
                if {ch(l), ch(l.link_loop_next)} == {ch(lg), ch(lg.link_loop_next)}:
                    visto.add(g.index); pilha.append(g)
    ilhas.append(comp)
eh_unha = lambda n: n.endswith('3') and any(k in n for k in ('Thumb', 'Index', 'Mid', 'Ring', 'Pinky')) or n.endswith('ToeBase')
r = {}
for comp in ilhas:
    if len(comp) > 80: continue
    n = collections.Counter(dom[v.index] for f in comp for v in f.verts).most_common(1)[0][0]
    if eh_unha(n):
        r.setdefault(n, []).append([[list(l[uv].uv) for l in f.loops] for f in comp])
json.dump(r, open(saida, 'w'))
print('  ilhas de unha:', {k: [len(i) for i in v] for k, v in sorted(r.items())}, flush=True)
