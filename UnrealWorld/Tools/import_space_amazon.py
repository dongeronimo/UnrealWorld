"""Imports the Space Amazon (skeletal mesh + clips) from Art/space_amazon/unreal, headless or in the editor.

    UnrealEditor-Cmd.exe UnrealWorld.uproject -run=pythonscript -script="Tools/import_space_amazon.py"

or, in the editor's Output Log (Cmd mode):  py "D:/UnrealWorld/UnrealWorld/Tools/import_space_amazon.py"

Reimports over existing assets, so references to them survive. Uses the legacy FBX importer
(Interchange.FeatureFlags.Import.FBX False for this run only): its options can be set from script and
read back, and the parity test (paridade_control_rig.py) checks the result bone by bone anyway. The
Blender side is exportar_unreal.py (cm scene, UnitScaleFactor 1, A-pose as bind and reference pose).
"""
import glob
import os

import unreal

ART = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Art", "space_amazon", "unreal"))
ROOT = "/Game/Chars/SpaceAmazon"
ANIM_DIR = ROOT + "/animclips"
NAME = "SpaceAmazon"

assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)


def run(cmd):
    unreal.SystemLibrary.execute_console_command(None, cmd)


def task(src, dest, options):
    t = unreal.AssetImportTask()
    t.set_editor_properties({"filename": src, "destination_path": dest, "automated": True,
                             "replace_existing": True, "save": True, "options": options})
    return t


def mesh_options():
    o = unreal.FbxImportUI()
    o.set_editor_properties({"import_mesh": True, "import_as_skeletal": True, "import_animations": False,
                             "import_materials": True, "import_textures": True,
                             "mesh_type_to_import": unreal.FBXImportType.FBXIT_SKELETAL_MESH})
    o.skeletal_mesh_import_data.set_editor_properties({
        "import_morph_targets": True,
        "use_t0_as_ref_pose": False,  # the bind pose is the A-pose; the clip's T-pose stays out
        "convert_scene": True, "force_front_x_axis": False})
    return o


def anim_options(skeleton):
    o = unreal.FbxImportUI()
    o.set_editor_properties({"import_mesh": False, "import_as_skeletal": True, "import_animations": True,
                             "import_materials": False, "import_textures": False, "skeleton": skeleton,
                             "mesh_type_to_import": unreal.FBXImportType.FBXIT_ANIMATION})
    o.anim_sequence_import_data.set_editor_properties({
        "animation_length": unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME,
        "import_bone_tracks": True, "import_custom_attribute": True,
        "convert_scene": True, "force_front_x_axis": False})
    return o


def main():
    run("Interchange.FeatureFlags.Import.FBX False")
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    try:
        mesh_fbx = os.path.join(ART, NAME + ".fbx")
        if not os.path.isfile(mesh_fbx):
            raise RuntimeError("missing " + mesh_fbx)
        tools.import_asset_tasks([task(mesh_fbx, ROOT, mesh_options())])
        mesh = assets.load_asset("%s/%s" % (ROOT, NAME))
        if not isinstance(mesh, unreal.SkeletalMesh):
            raise RuntimeError("skeletal mesh did not import: %s/%s" % (ROOT, NAME))
        skeleton = mesh.skeleton
        unreal.log("SpaceAmazon: mesh %s, skeleton %s" % (mesh.get_path_name(), skeleton.get_path_name()))

        clips = sorted(f for f in glob.glob(os.path.join(ART, NAME + "_*.fbx")))
        tools.import_asset_tasks([task(f, ANIM_DIR, anim_options(skeleton)) for f in clips])
        for f in clips:
            path = "%s/%s" % (ANIM_DIR, os.path.splitext(os.path.basename(f))[0])
            a = assets.load_asset(path)
            if not isinstance(a, unreal.AnimSequence):
                raise RuntimeError("clip did not import: " + path)
            unreal.log("SpaceAmazon: clip %s, %d keys" % (path, a.get_editor_property("number_of_sampled_keys")))
        # the task's save flag writes only the primary asset; the skeleton, physics asset, materials
        # and textures it created stay dirty, and the mesh on disk then points at nothing
        saved = assets.save_directory(ROOT, only_if_is_dirty=False, recursive=True)
        unreal.log("SpaceAmazon: saved %s: %s" % (ROOT, saved))
    finally:
        run("Interchange.FeatureFlags.Import.FBX True")


main()
