# -*- coding: utf-8 -*-
"""Puts an AccuRig character's .blend in centimetres, so Unreal imports it with no unit conversion.
  batch: blender -b IN.blend -P to_centimeters.py -- OUT.blend

Why: an FBX in metres (UnitScaleFactor 100) makes Unreal convert to cm on import, and the x100
lands on the root bone (RL_BoneRoot at scale 100). No Blender FBX export option writes a cm file
with every node at scale 1 from a metre scene (11 combinations tested, 2026-10-16), so the data
itself has to be in cm.

What it does:
  - armature rest bones, mesh data and shape keys x100;
  - every action's pose bone location curves x100 (Ctrl+A does not touch actions);
  - locations of root objects x100 (camera, light), so the scene still lines up;
  - scene Unit Scale 0.01, length in centimetres: 1 Blender unit = 1 cm, and the exporter
    writes UnitScaleFactor 1.

Proof: the deformed mesh in rest and at 3 frames of every action, before and after; refuses to
save if any vertex is more than 0.5 mm away from 100x its old position.
"""
import bpy, sys, os, re
from mathutils import Matrix

OUT = os.path.abspath(sys.argv[sys.argv.index('--') + 1])
K = 100.0
# 0.5 mm, in the new units. Ratoman measured 0.145 mm: float drift on the ear and whisker tips at the
# end of the dance (0.02 mm at its start), with every other bone under 0.03 mm. Cause not found.
TOL = 5e-4 * K
P = lambda *x: print(*x, flush=True)

if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
sc = bpy.context.scene
if abs(sc.unit_settings.scale_length - 1.0) > 1e-9:
    raise SystemExit("scene Unit Scale is %g, expected 1 (metres)" % sc.unit_settings.scale_length)
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
if len(arms) != 1:
    raise SystemExit("expected one armature, found %d" % len(arms))
arm = arms[0]
if max(abs(x - 1) for x in arm.scale) > 1e-6:
    raise SystemExit("armature scale %s: apply it first" % tuple(arm.scale))
malhas = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == arm]
acts = [a for a in bpy.data.actions if any(f.data_path.startswith('pose.bones') for f in a.fcurves)]
ad = arm.animation_data or arm.animation_data_create()
ligada = ad.action
slot = ad.action_slot if hasattr(ad, 'action_slot') else None


def amostras():
    """(action, frame) -> world coordinates of each deformed mesh."""
    out = {}
    casos = [(None, 0)] + [(a, int(f)) for a in acts
                           for f in sorted({a.frame_range[0], sum(a.frame_range) / 2, a.frame_range[1]})]
    for a, f in casos:
        arm.data.pose_position = 'POSE' if a else 'REST'
        ad.action = a
        if a and hasattr(ad, 'action_slot') and a.slots: ad.action_slot = a.slots[0]
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        cs = []
        for o in malhas:
            ev = o.evaluated_get(dg); me = ev.to_mesh()
            cs.append([ev.matrix_world @ v.co for v in me.vertices]); ev.to_mesh_clear()
        out[(a.name if a else 'rest', f)] = cs
    return out


antes = amostras()

S = Matrix.Scale(K, 4)
mundo = {o: o.matrix_world.copy() for o in malhas}
for o in bpy.data.objects:
    if o.parent is None: o.location *= K
bpy.context.view_layer.update()
# head/tail x K in edit mode: same direction, roll untouched. armature.transform(S) recomputes the
# rolls and the rounding twists the bones a little (0.15 mm at the end of the dance).
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')
# read everything first: a connected child's head is its parent's tail, it would be scaled twice
ossos = [(eb, eb.head * K, eb.tail * K, eb.roll) for eb in arm.data.edit_bones]
for eb, h, t, roll in ossos:
    eb.head = h; eb.tail = t; eb.roll = roll
bpy.ops.object.mode_set(mode='OBJECT')
for o in malhas:
    # mesh data (and shape keys) straight into the scaled world space; object at identity under the armature
    o.data.transform(S @ mundo[o], shape_keys=True)
    o.matrix_parent_inverse = arm.matrix_world.inverted()
    o.matrix_basis = Matrix.Identity(4)
for a in acts:
    n = 0
    for f in a.fcurves:
        if re.match(r'pose\.bones\[".*"\]\.location$', f.data_path):
            for kp in f.keyframe_points:
                # auto handles are recomputed from the curve's shape, which is not scale-invariant in y:
                # freeze them so the curve between keys is exactly the old one x K
                if kp.handle_left_type in {'AUTO', 'AUTO_CLAMPED'}: kp.handle_left_type = 'FREE'
                if kp.handle_right_type in {'AUTO', 'AUTO_CLAMPED'}: kp.handle_right_type = 'FREE'
                kp.co.y *= K; kp.handle_left.y *= K; kp.handle_right.y *= K
            n += 1
    P("  %s: %d location curves x %g" % (a.name, n, K))
sc.unit_settings.system = 'METRIC'
sc.unit_settings.scale_length = 1.0 / K
sc.unit_settings.length_unit = 'CENTIMETERS'
bpy.context.view_layer.update()

depois = amostras()
pior = 0.0
for chave, cs in antes.items():
    e = max((x * K - y).length for c0, c1 in zip(cs, depois[chave]) for x, y in zip(c0, c1))
    pior = max(pior, e)
    P("  %-50s max error %.4f mm" % ('%s @ %d' % chave, e * 10))
ad.action = ligada
if ligada and slot: ad.action_slot = slot
arm.data.pose_position = 'POSE'
if pior > TOL: raise SystemExit("REFUSED: a vertex moved %.3f mm" % (pior * 10))
h = max((o.matrix_world @ v.co).z for o in malhas for v in o.data.vertices)
P("  unit scale %g; rest height %.2f cm; max error %.4f mm" % (sc.unit_settings.scale_length, h, pior * 10))
bpy.ops.wm.save_as_mainfile(filepath=OUT, copy=True)
P("  saved %s" % OUT)
