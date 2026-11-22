"""Fearing's Grruzam clips: imports the batch's armature-only FBX, one Unreal folder per batch folder.

    UnrealEditor-Cmd.exe D:/UnrealWorld/UnrealWorld/UnrealWorld.uproject -run=pythonscript
        -script="D:/UnrealWorld/UnrealWorld/Tools/clipes_space_amazon.py Movements_Intro Movements_Idle"
    Output Log, box on Cmd:  py D:/UnrealWorld/UnrealWorld/Tools/clipes_space_amazon.py Movements_Walk_A

The script path must be absolute: a relative one resolves under Engine/Binaries/Win64. With no folder
names it imports every folder the batch exported. The editor must be closed for the headless run.

Source: D:/UnrealWorld/Art/space_amazon/grruzam_lote/unreal/<folder>/SpaceAmazon_*.fbx, written by
gurps tools/blender/lote_grruzam.py --quem fearing exportar <folder>. Destination:
/Game/Chars/SpaceAmazon/animclips/<folder>/. One folder each because Grruzam ships 10 clip names in two
folders (Jump_Block; the Idle_*_To_Jogging_*_Turn_* clips), and a flat folder would overwrite one of each pair.

The clips go onto SpaceAmazon_Skeleton, which import_space_amazon.py made from SpaceAmazon.fbx. The clip FBXs
carry only the armature, so the character never needs reimporting for them, unless the skeleton changes.
Clips named _Root, and every clip of a RootMotion folder, get Enable Root Motion: retarget_biped.py put
their travel on RL_BoneRoot.

Each clip is checked against the batch's katana_notifies.json (frame count). The katana notifies are
notifies_space_amazon.py's job, run after this.
"""
import glob
import json
import os
import sys

import unreal

LOTE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Art", "space_amazon",
                                     "grruzam_lote", "unreal"))
ROOT = "/Game/Chars/SpaceAmazon"
ANIM_DIR = ROOT + "/animclips"
SKELETON = ROOT + "/SpaceAmazon_Skeleton"
NAME = "SpaceAmazon"

tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.EditorAssetLibrary


def run(cmd):
    unreal.SystemLibrary.execute_console_command(None, cmd)


def options(skeleton):
    o = unreal.FbxImportUI()
    # armature-only FBXs import fine either way; off, so a clip FBX that ever carries a mesh (shape-key
    # curves) still comes in as an animation instead of a new skeletal mesh
    o.set_editor_properties({"automated_import_should_detect_type": False,
                             "import_mesh": False, "import_as_skeletal": True, "import_animations": True,
                             "import_materials": False, "import_textures": False, "skeleton": skeleton,
                             "mesh_type_to_import": unreal.FBXImportType.FBXIT_ANIMATION})
    o.anim_sequence_import_data.set_editor_properties({
        "animation_length": unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,
        "import_bone_tracks": True, "import_custom_attribute": True,
        "convert_scene": True, "force_front_x_axis": False})
    return o


def root_motion(folder, clip):
    return "_Root" in clip or "RootMotion" in folder


def main(folders):
    skeleton = assets.load_asset(SKELETON)
    if not isinstance(skeleton, unreal.Skeleton):
        raise RuntimeError("no skeleton at " + SKELETON)
    frames = {}
    nf = os.path.join(LOTE, "katana_notifies.json")
    if os.path.isfile(nf):
        with open(nf, encoding="utf-8") as fh:
            frames = {(c["pasta"], os.path.splitext(c["fbx"])[0]): c["frames"] for c in json.load(fh)["clips"]}
    if not folders:
        folders = sorted(d for d in os.listdir(LOTE) if glob.glob(os.path.join(LOTE, d, NAME + "_*.fbx")))
    bad = []
    run("Interchange.FeatureFlags.Import.FBX False")
    try:
        for folder in folders:
            fbxs = sorted(glob.glob(os.path.join(LOTE, folder, NAME + "_*.fbx")))
            if not fbxs:
                raise RuntimeError("no %s_*.fbx in %s" % (NAME, os.path.join(LOTE, folder)))
            dest = "%s/%s" % (ANIM_DIR, folder)
            tasks = []
            for f in fbxs:
                t = unreal.AssetImportTask()
                t.set_editor_properties({"filename": f, "destination_path": dest, "automated": True,
                                         "replace_existing": True, "save": True, "options": options(skeleton)})
                tasks.append(t)
            tools.import_asset_tasks(tasks)
            n_root = 0
            for f in fbxs:
                clip = os.path.splitext(os.path.basename(f))[0]
                seq = assets.load_asset("%s/%s" % (dest, clip))
                if not isinstance(seq, unreal.AnimSequence):
                    bad.append("%s/%s: did not import" % (folder, clip))
                    continue
                keys = seq.get_editor_property("number_of_sampled_keys")
                want = frames.get((folder, clip))
                if want is not None and keys != want:
                    bad.append("%s/%s: %d keys, the batch baked %d frames" % (folder, clip, keys, want))
                rm = root_motion(folder, clip)
                if seq.get_editor_property("enable_root_motion") != rm:
                    seq.set_editor_property("enable_root_motion", rm)
                    assets.save_loaded_asset(seq)
                n_root += rm
            unreal.log("clipes_space_amazon: %s: %d clips in %s, %d with root motion"
                       % (folder, len(fbxs), dest, n_root))
    finally:
        run("Interchange.FeatureFlags.Import.FBX True")
    if bad:
        raise RuntimeError("clipes_space_amazon: %d problems:\n  %s" % (len(bad), "\n  ".join(bad)))
    unreal.log("clipes_space_amazon: ok, folders %s" % ", ".join(folders))


main(sys.argv[1:])
