"""The drow's Post Process Anim Blueprint, by script: ABP_Drow_Post_Process runs CR_Drow last, and is set as the Post
Process Anim Blueprint of the Drow mesh asset, so the correctives run after whatever plays her (drow handoff, step 5).

    UnrealEditor-Cmd.exe D:/UnrealWorld/UnrealWorld/UnrealWorld.uproject -run=pythonscript -script="D:/UnrealWorld/UnrealWorld/Tools/abp_drow.py"

Run after drow_control_rig.py (CR_Drow must exist). Python cannot place anim graph nodes, so this duplicates Fearing's
hand-made ABP_Fearing_Post_Process (Input Pose -> Control Rig -> Output Pose), points it at Drow_Skeleton and CR_Drow,
and compiles it. It refuses if Fearing's graph holds anything else, rather than copy her nodes onto the drow. If the
asset is already there it only re-points and recompiles it, so a hand edit survives a rerun.
"""
import unreal

SRC = "/Game/Chars/SpaceAmazon/ABP_Fearing_Post_Process"
DST = "/Game/Chars/Drow/ABP_Drow_Post_Process"
MESH = "/Game/Chars/Drow/Drow"
CR = "/Game/Chars/Drow/CR_Drow"
ALLOWED = ("AnimGraphNode_Root", "AnimGraphNode_LinkedInputPose", "AnimGraphNode_ControlRig")

assets = unreal.EditorAssetLibrary


def graph_nodes(bp):
    """The nodes of the editable graphs. The compiler keeps copies under ExecuteUbergraph_<ABP>, rebuilt at every
    compile: editing those changes nothing."""
    pkg = bp.get_outermost()
    return [n for n in unreal.ObjectIterator(unreal.AnimGraphNode_Base)
            if n.get_outermost() == pkg and not n.get_outer().get_name().startswith("ExecuteUbergraph")]


def main():
    mesh = assets.load_asset(MESH)
    cr_class = assets.load_blueprint_class(CR)
    if mesh is None or cr_class is None:
        raise RuntimeError("abp_drow: need %s and %s (import_drow.py, drow_control_rig.py)" % (MESH, CR))
    if not assets.does_asset_exist(DST):
        src = assets.load_asset(SRC)
        kinds = sorted({n.get_class().get_name() for n in graph_nodes(src)})
        other = [k for k in kinds if k not in ALLOWED]
        if other:
            raise RuntimeError("abp_drow: %s has more than the Control Rig node: %s. Make the ABP by hand "
                               "(SpaceAmazon_Unreal.md section 2)" % (SRC, other))
        if assets.duplicate_asset(SRC, DST) is None:
            raise RuntimeError("abp_drow: could not duplicate " + SRC)
        unreal.log("abp_drow: %s duplicated from %s (nodes %s)" % (DST, SRC, kinds))
    abp = assets.load_asset(DST)
    abp.set_editor_property("target_skeleton", mesh.skeleton)
    rigs = [n for n in graph_nodes(abp) if n.get_class().get_name() == "AnimGraphNode_ControlRig"]
    if len(rigs) != 1:
        raise RuntimeError("abp_drow: %d Control Rig nodes in %s, expected 1" % (len(rigs), DST))
    node = rigs[0].get_editor_property("node")
    node.set_editor_property("control_rig_class", cr_class)
    rigs[0].set_editor_property("node", node)
    unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    got = rigs[0].get_editor_property("node").get_editor_property("control_rig_class")
    if got != cr_class:
        raise RuntimeError("abp_drow: the node reads back %s, not %s" % (got, cr_class))
    assets.save_loaded_asset(abp)

    mesh.set_editor_property("post_process_anim_blueprint", unreal.BlueprintEditorLibrary.generated_class(abp))
    assets.save_loaded_asset(mesh)
    unreal.log("abp_drow: %s on %s runs %s; set as the Post Process Anim Blueprint of %s"
               % (DST, mesh.skeleton.get_name(), cr_class.get_name(), MESH))


main()
