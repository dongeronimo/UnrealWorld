"""BP_Drow, the drow's Blueprint over the C++ ADrow (Source/UnrealWorld/Drow.*), and a check of what it carries: every
piece with its mesh on Drow_Skeleton, every prop on a socket the Drow mesh has (drow handoff, step 5).

    UnrealEditor-Cmd.exe D:/UnrealWorld/UnrealWorld/UnrealWorld.uproject -run=pythonscript -script="D:/UnrealWorld/UnrealWorld/Tools/bp_drow.py"

Run after import_drow.py and abp_drow.py, with the C++ built. Creates the Blueprint only if it is not there, so hand
edits to it survive. The check reads the class defaults: an asset path wrong in Drow.cpp shows here as a component
with no mesh, not as an invisible piece in the level.
"""
import unreal

ROOT = "/Game/Chars/Drow"
BP = ROOT + "/BP_Drow"

assets = unreal.EditorAssetLibrary


def main():
    if not assets.does_asset_exist(BP):
        f = unreal.BlueprintFactory()
        f.set_editor_property("parent_class", unreal.Drow)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset("BP_Drow", ROOT, unreal.Blueprint, f)
        if bp is None:
            raise RuntimeError("bp_drow: could not create " + BP)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        assets.save_loaded_asset(bp)
        unreal.log("bp_drow: created %s (parent ADrow)" % BP)
    bp = assets.load_asset(BP)
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    body = assets.load_asset(ROOT + "/Drow")
    skeleton = body.skeleton
    post = body.get_editor_property("post_process_anim_blueprint")
    unreal.log("bp_drow: Drow mesh post process ABP: %s" % (post.get_name() if post else "NONE"))
    bad = []
    for c in cdo.get_editor_property("pieces"):
        m = c.get_skeletal_mesh_asset()
        ok = m is not None and m.skeleton == skeleton
        unreal.log("bp_drow: piece %-14s %-24s visible=%s" % (c.get_name(), m.get_name() if m else "NO MESH", c.is_visible()))
        if not ok:
            bad.append(c.get_name())
    for name in ("katana", "pistol", "glasses", "headphone"):
        c = cdo.get_editor_property(name)
        sm = c.get_editor_property("static_mesh")
        sock = str(c.get_attach_socket_name())
        has = body.find_socket(sock) is not None
        unreal.log("bp_drow: prop %-10s %-16s on socket %-16s socket on Drow: %s; tags %s"
                   % (name, sm.get_name() if sm else "NO MESH", sock, has, [str(t) for t in c.component_tags]))
        if sm is None or not has:
            bad.append(name)
    if post is None:
        bad.append("post process ABP")
    if bad:
        raise RuntimeError("bp_drow: wrong: %s" % bad)
    unreal.log("bp_drow: OK")


main()
