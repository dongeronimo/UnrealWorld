"""Blender: dump Sophia's body (rest pose) for sophia_feridas.py. Like sophia_textura_dump.py, plus vertex normals.
blender -b sophia_ruiva_preview.blend --python sophia_feridas_dump.py -- OUT.npz"""
import bpy, numpy as np, sys
o=bpy.data.objects['Body_Rigged']; me=o.data; arm=o.parent
me.calc_loop_triangles()
mw=np.array(o.matrix_world)
co=np.array([v.co for v in me.vertices]); co=co@mw[:3,:3].T+mw[:3,3]
nr=np.array([v.normal for v in me.vertices])@np.linalg.inv(mw[:3,:3])
nr/=np.linalg.norm(nr,axis=1,keepdims=True)+1e-12
names={g.index:g.name for g in o.vertex_groups}
nv=len(me.vertices); hair=np.zeros(nv); head=np.zeros(nv); jaw=np.zeros(nv)
for v in me.vertices:
    for g in v.groups:
        n=names[g.group]
        if n.startswith('CC_Extra_Hair'): hair[v.index]+=g.weight
        elif n=='CC_Base_Head': head[v.index]+=g.weight
        elif n.startswith('CC_Base_Jaw') or 'Teeth' in n or 'Tongue' in n: jaw[v.index]+=g.weight
uv=me.uv_layers['Channel0'].data
tri=np.array([t.vertices[:] for t in me.loop_triangles])
tuv=np.array([[uv[l].uv[:] for l in t.loops] for t in me.loop_triangles])
am=np.array(arm.matrix_world)
B={}
for b in arm.data.bones:
    B[b.name+'|h']=(am@np.append(np.array(b.head_local),1))[:3]
    B[b.name+'|t']=(am@np.append(np.array(b.tail_local),1))[:3]
np.savez(sys.argv[-1], co=co, nr=nr, hair=hair, head=head, jaw=jaw, tri=tri, tuv=tuv, bnames=np.array(list(B.keys())), bpos=np.array(list(B.values())))
print("DUMPED", co.min(0), co.max(0), len(tri))
for k in sorted(B):
    if k.endswith('|h') and ('Twist' not in k) and ('Extra' not in k): print("B", k, np.round(B[k],3))
