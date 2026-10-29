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


def main(recipes_path, clip_path, cr_path, tol):
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
    unreal.log("paridade: %s on %s, %d frames, tolerance %.3f deg" % (cr_path, clip_path, frames, tol))
    fail = []
    for n in derived:
        e, f = worst[n]
        unreal.log("paridade:   %-26s max %.4f deg (frame %d)   recipe off: %.2f deg" % (n, e, f, off[n]))
        if e > tol:
            fail.append(n)
    if fail:
        raise RuntimeError("paridade FAILED for %s" % fail)
    unreal.log("paridade: PASS")


args = [a for a in sys.argv[1:] if not a.startswith("-")]
if len(args) < 3:
    raise RuntimeError("usage: paridade_control_rig.py RECIPES.json /Game/Path/Clip /Game/Path/CR_Name [tolerance_degrees]")
main(args[0], args[1], args[2], float(args[3]) if len(args) > 3 else 0.05)
