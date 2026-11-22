"""Fearing's expressions as a Pose Asset: imports SpaceAmazon_Expressoes_poses.fbx and builds
PA_SpaceAmazon_Expressoes from it, headless or in the editor.

    UnrealEditor-Cmd.exe UnrealWorld.uproject -run=pythonscript -script="D:/UnrealWorld/UnrealWorld/Tools/poses_space_amazon.py"
    Output Log, box on Cmd:  py D:/UnrealWorld/UnrealWorld/Tools/poses_space_amazon.py

The clip comes from gurps tools/blender/poses_expressoes.py, then exportar_unreal.py: frame 0 neutral, then
one preset per frame, baked from her Blender drivers (24 face keys, the jaw, the six ear bones). The pose
names are the curves the Pose Blender node listens to, so `EvilLaugh = 0.5` in the AnimGraph is half an
evil laugh. This is Ratoman's setup (Ratoman_Brute_Unreal.md section 8), scripted.

First run creates the Pose Asset with the poses named. Making it additive on Neutral is one click in the
Pose Asset editor: Python cannot reach UPoseAsset::ConvertSpace, only the Details panel's button can. Later
runs update the poses from the clip and keep the names and the additive setting (UpdatePoseFromAnimation).

import_space_amazon.py also imports this clip (it takes every SpaceAmazon_*.fbx), but does not touch the
Pose Asset: run this after it whenever the expressions change.
"""
import os

import unreal

ART = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Art", "space_amazon", "unreal"))
ROOT = "/Game/Chars/SpaceAmazon"
ANIM_DIR = ROOT + "/animclips"
CLIP = "SpaceAmazon_Expressoes_poses"
PA = "PA_SpaceAmazon_Expressoes"
SKELETON = ROOT + "/SpaceAmazon_Skeleton"
# frame order poses_expressoes.py prints: neutral, then the presets in the order of space_amazon.json
POSES = ["Neutral", "EvilLaugh", "Laugh", "Happy", "Frown", "Loathing", "Pain", "Scream", "Cry"]
FACE_SPOT_CHECK = ["mouthSmile_L", "mouthSmile_R", "eyeBlink_L", "browInnerUp", "mouthLowerDown_L"]

tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary


def run(cmd):
    unreal.SystemLibrary.execute_console_command(None, cmd)


def import_clip(skeleton):
    o = unreal.FbxImportUI()
    # the FBX carries the meshes too (their morph curves are the face), and an automated import that
    # detects the type makes it a skeletal mesh and leaves the animation unsaved
    o.set_editor_properties({"automated_import_should_detect_type": False,
                             "import_mesh": False, "import_as_skeletal": True, "import_animations": True,
                             "import_materials": False, "import_textures": False, "skeleton": skeleton,
                             "mesh_type_to_import": unreal.FBXImportType.FBXIT_ANIMATION})
    o.anim_sequence_import_data.set_editor_properties({
        "animation_length": unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,
        "import_bone_tracks": True, "import_custom_attribute": True,
        # the body correctives sit at 0 through the clip; the Control Rig owns them anyway
        "do_not_import_curve_with_zero": True,
        "convert_scene": True, "force_front_x_axis": False})
    t = unreal.AssetImportTask()
    t.set_editor_properties({"filename": os.path.join(ART, CLIP + ".fbx"), "destination_path": ANIM_DIR,
                             "automated": True, "replace_existing": True, "save": True, "options": o})
    run("Interchange.FeatureFlags.Import.FBX False")
    try:
        tools.import_asset_tasks([t])
    finally:
        run("Interchange.FeatureFlags.Import.FBX True")
    seq = assets.load_asset("%s/%s" % (ANIM_DIR, CLIP))
    if not isinstance(seq, unreal.AnimSequence):
        raise RuntimeError("clip did not import: %s/%s" % (ANIM_DIR, CLIP))
    keys = seq.get_editor_property("number_of_sampled_keys")
    curves = [str(c) for c in unreal.AnimationLibrary.get_animation_curve_names(seq, unreal.RawCurveTrackTypes.RCT_FLOAT)]
    missing = [c for c in FACE_SPOT_CHECK if c not in curves]
    unreal.log("poses_space_amazon: clip %s, %d keys, %d curves (%d CORR_)"
               % (seq.get_path_name(), keys, len(curves), sum(1 for c in curves if c.startswith("CORR_"))))
    if keys != len(POSES):
        raise RuntimeError("clip has %d keys, expected one per pose (%d)" % (keys, len(POSES)))
    if missing:
        raise RuntimeError("face curves missing from the clip: %s" % missing)
    return seq


def main():
    skeleton = assets.load_asset(SKELETON)
    if not isinstance(skeleton, unreal.Skeleton):
        raise RuntimeError("no skeleton at " + SKELETON)
    seq = import_clip(skeleton)

    path = "%s/%s" % (ROOT, PA)
    pa = assets.load_asset(path) if assets.does_asset_exist(path) else None
    if pa is None:
        f = unreal.PoseAssetFactory()
        f.set_editor_property("source_animation", seq)
        f.set_editor_property("pose_names", POSES)
        pa = tools.create_asset(PA, ROOT, unreal.PoseAsset, f)
        if pa is None:
            raise RuntimeError("could not create " + path)
        unreal.log("poses_space_amazon: created %s" % path)
    else:
        pa.update_pose_from_animation(seq)
        unreal.log("poses_space_amazon: updated %s from the clip" % path)
    names = [str(n) for n in pa.get_pose_names()]
    if names != POSES:
        raise RuntimeError("pose names %s, expected %s" % (names, POSES))
    assets.save_loaded_asset(pa)
    base = str(pa.get_base_pose_name())
    unreal.log("poses_space_amazon: %d poses %s; base pose %s" % (len(names), ", ".join(names),
               base if base != "None" else "none yet (make it additive on Neutral in the Pose Asset editor)"))


main()
