"""Parity test: does the generated Control Rig give the same derived bones Blender's drivers gave?

    UnrealEditor-Cmd.exe UnrealWorld.uproject -run=pythonscript -script="Tools/paridade_control_rig.py RECIPES.json /Game/Path/Clip /Game/Path/CR_Name [tolerance_degrees]"

The clip must come from Blender with the drivers evaluated (exportar_unreal.py bakes them): its
derived-bone tracks are the reference. Per frame, the clip's local pose goes into the rig's hierarchy,
the rig runs Forwards Solve, and each derived bone the recipes name is compared with the clip's own
track. The rig overwrites those bones, so a match means the rig rebuilt Blender's value from the
source bones alone, which is what it will do after aim offsets and foot IK.

Also reports the error with the recipe switched off (the bone left at its reference pose), so a pass
is a pass on a clip that actually twists, not on one where every answer is zero.
Fails (exception, nonzero exit) above the tolerance, default 0.05 degrees.

Curves (optional 5th argument, CURVES_REF.json from gurps tools/blender/exportar_curvas_ref.py): the
value of every shape key Blender's drivers gave on every frame. Each curve the rig sets is compared
with it (tolerance 0.002); the peak value is printed beside it, so a pass is on a curve that moves.
Unreal frame i is Blender frame f0 + i.
"""
import json
import math
import sys

import unreal

assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)


def angle_deg(a, b):
    d = abs(a.x * b.x + a.y * b.y + a.z * b.z + a.w * b.w)
    return math.degrees(2.0 * math.acos(min(1.0, d)))


def bone_key(name):
    return unreal.RigElementKey(type=unreal.RigElementType.BONE, name=name)


def main(recipes_path, clip_path, cr_path, tol, curvas_ref=None):
    with open(recipes_path, encoding="utf-8") as f:
        rows = [r for r in json.load(f)["linhas"] if r.get("tipo") == "torcao"]
    clip = assets.load_asset(clip_path)
    bp = assets.load_asset(cr_path)
    if not isinstance(clip, unreal.AnimSequence) or bp is None:
        raise RuntimeError("missing clip or rig: %s, %s" % (clip_path, cr_path))
    rig = bp.create_control_rig()
    if rig is None:
        raise RuntimeError("could not instance " + cr_path)
    rig.request_init()
    rig.execute("Forwards Solve")
    h = rig.get_hierarchy()
    bones = [k for k in h.get_all_keys(True) if k.type == unreal.RigElementType.BONE]
    names = [str(k.name) for k in bones]
    derived = [r["osso"] for r in rows]
    missing = [n for n in derived + [r["fonte"] for r in rows] if n not in names]
    if missing:
        raise RuntimeError("bones not in the rig hierarchy: %s" % missing)

    ref = None
    if curvas_ref:
        with open(curvas_ref, encoding="utf-8") as f:
            todos = json.load(f)
        nome = clip_path.rsplit("/", 1)[-1]
        k = [c for c in todos if nome.endswith(c)]
        if not k:
            raise RuntimeError("clip %s not in %s (%s)" % (nome, curvas_ref, list(todos)))
        ref_c = todos[k[0]]["chaves"]
        cpior = {c: (0.0, 0) for c in ref_c}
        got_c = {c: [] for c in ref_c}
    opts = unreal.AnimPoseEvaluationOptions()
    frames = clip.get_editor_property("number_of_sampled_frames")
    worst = {n: (0.0, 0) for n in derived}
    off = {n: 0.0 for n in derived}
    for f in range(frames):
        pose = unreal.AnimPoseExtensions.get_anim_pose_at_frame(clip, f, opts)
        for k in bones:
            h.set_local_transform(k, unreal.AnimPoseExtensions.get_bone_pose(pose, k.name, unreal.AnimPoseSpaces.LOCAL),
                                  False, True, False, False)
        rig.execute("Forwards Solve")
        for n in derived:
            ref = unreal.AnimPoseExtensions.get_bone_pose(pose, n, unreal.AnimPoseSpaces.LOCAL).rotation
            got = h.get_local_transform(bone_key(n), False).rotation
            rest = h.get_local_transform(bone_key(n), True).rotation
            e = angle_deg(ref, got)
            if e > worst[n][0]:
                worst[n] = (e, f)
            off[n] = max(off[n], angle_deg(ref, rest))
        if curvas_ref:
            for c in ref_c:
                got_c[c].append(h.get_curve_value(unreal.RigElementKey(type=unreal.RigElementType.CURVE, name=c)))
    unreal.log("paridade: %s on %s, %d frames, tolerance %.3f deg" % (cr_path, clip_path, frames, tol))
    fail = []
    for n in derived:
        e, f = worst[n]
        unreal.log("paridade:   %-26s max %.4f deg (frame %d)   recipe off: %.2f deg" % (n, e, f, off[n]))
        if e > tol:
            fail.append(n)
    if curvas_ref:
        # Unreal frame i against Blender frame f0 + i + d: the shift is measured, not assumed
        def erros(d):
            out = {}
            for c, vals in ref_c.items():
                es = [(abs(g_ - vals[i + d]), i) for i, g_ in enumerate(got_c[c]) if 0 <= i + d < len(vals)]
                out[c] = max(es) if es else (0.0, 0)
            return out
        por = {d: erros(d) for d in (-1, 0, 1)}
        d = min(por, key=lambda k: max(e for e, _ in por[k].values()))
        unreal.log("paridade: curve frame shift %+d (worst per shift: %s)"
                   % (d, ", ".join("%+d: %.4f" % (k, max(e for e, _ in v.values())) for k, v in por.items())))
        cpior = por[d]
        cfail = [c for c, (e, _) in cpior.items() if e > 0.002]
        ativas = [c for c, v in ref_c.items() if max(v) > 0.05]
        pior = max(cpior.items(), key=lambda t: t[1][0])
        unreal.log("paridade: curves %d (%d peak above 0.05), worst %s %.5f at frame %d"
                   % (len(cpior), len(ativas), pior[0], pior[1][0], pior[1][1]))
        for c in cfail[:10]:
            unreal.log("paridade:   curve %-28s max %.4f (frame %d), peak %.3f" % (c, cpior[c][0], cpior[c][1], max(ref_c[c])))
        fail += cfail
    if fail:
        raise RuntimeError("paridade FAILED for %s" % fail[:12])
    unreal.log("paridade: PASS")


args = [a for a in sys.argv[1:] if not a.startswith("-")]
if len(args) < 3:
    raise RuntimeError("usage: paridade_control_rig.py RECIPES.json /Game/Path/Clip /Game/Path/CR_Name [tolerance_degrees] [CURVES_REF.json]")
main(args[0], args[1], args[2], float(args[3]) if len(args) > 3 else 0.05, args[4] if len(args) > 4 else None)
