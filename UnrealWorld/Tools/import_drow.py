"""Imports the drow as modular pieces (leader mesh + one skeletal mesh per piece, one skeleton), with textures,
materials, clips, props and sockets, headless or in the editor.

    UnrealEditor-Cmd.exe D:/UnrealWorld/UnrealWorld/UnrealWorld.uproject -run=pythonscript -script="D:/UnrealWorld/UnrealWorld/Tools/import_drow.py"
    Output Log, box on Cmd:  py "D:/UnrealWorld/UnrealWorld/Tools/import_drow.py"

The export is gurps tools/blender/exportar_pacote_unreal.py ... --modular (D:/drow/unreal):
  Drow.fbx                 body and face, the leader (Leader Pose); it makes Drow_Skeleton
  Pecas/Drow_<Piece>.fbx   each garment, hair, holster and scabbard; every one carries all 158 bones and is
                           imported onto Drow_Skeleton, so a piece that disagrees fails here, not at run time
  Drow_<clip>.fbx          clips (armature only)
  Props/*.fbx              Sophia's props refitted to her (static meshes on sockets), soquetes_unreal.json
  Drow_modular.json        which FBX holds which objects, shape keys and materials (PNG, roughness, colour)

Built from the manifest, not from a hand table like import_space_amazon.py: 15 meshes and 17 materials by hand
would drift from Blender. Same master material shape as Fearing's (base colour texture or tint, roughness).
The props reuse Sophia's material instances: they are her props (user, 2026-11-21).

Sockets go on the leader mesh (not the skeleton): props attach to the leader component, which is also the one
UAnimNotify_AttachToSocket gets. Python cannot name a socket (SocketName is VisibleAnywhere), so they go through
the C++ USocketTools::SetMeshSocket, which creates or updates them in place.

Fails loudly: a piece on another skeleton, a slot with no material, a mesh whose morph targets are not its
Blender shape keys, a missing texture. Safe to run again: it reimports over the same assets.
"""
import json
import os
import re

import unreal

ART = "D:/drow/unreal"
NAME = "Drow"
ROOT = "/Game/Chars/Drow"
PIECE_DIR = ROOT + "/Pieces"
ANIM_DIR = ROOT + "/animclips"
TEX_DIR = ROOT + "/Textures"
MAT_DIR = ROOT + "/Materials"
PROP_DIR = ROOT + "/Props"
SOPHIA_MAT = "/Game/Chars/Sophia/Materials"
# Two-sided by object: the braid's thin locks are single sheets seen from both sides (drow handoff, step 3);
# the mouth sac is seen from inside, as Fearing's. Everything else is one-sided: culling shows the right layer.
TWO_SIDED = {"Hair_Braid", "Boca"}
# Step 7 rebakes the pieces; the 8K skin keeps its texture and is capped here (drow handoff, step 7).
MAX_TEX = 4096
PROP_MATERIALS = [("Sophia_Katana", "MI_Sophia_Katana"), ("Sophia_Pistol", "MI_Sophia_Pistol"),
                  ("Sophia_Kitty_Headphone", "MI_Sophia_Headphone"), ("Sophia_Glass_Frame", "MI_Sophia_GlassFrame"),
                  ("Sophia_Glass_Lens", "M_Sophia_Lens")]

assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty


def log(msg):
    unreal.log("Drow: " + msg)


def run(cmd):
    unreal.SystemLibrary.execute_console_command(None, cmd)


def clean(s):
    return re.sub(r"\W", "_", s).lower()


def task(src, dest, options, name=None):
    t = unreal.AssetImportTask()
    props = {"filename": src, "destination_path": dest, "automated": True, "replace_existing": True, "save": True,
             "options": options}
    if name:
        props["destination_name"] = name
    t.set_editor_properties(props)
    return t


def mesh_options(skeleton=None):
    o = unreal.FbxImportUI()
    o.set_editor_properties({"import_mesh": True, "import_as_skeletal": True, "import_animations": False,
                             "import_materials": False, "import_textures": False,
                             # one physics asset, the leader's; a piece follows the leader's pose
                             "create_physics_asset": skeleton is None,
                             "mesh_type_to_import": unreal.FBXImportType.FBXIT_SKELETAL_MESH})
    if skeleton:
        o.set_editor_property("skeleton", skeleton)
    o.skeletal_mesh_import_data.set_editor_properties({
        "import_morph_targets": True,
        "use_t0_as_ref_pose": False,  # the bind pose is the A-pose
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


def instance_names(manifest):
    """Blender material -> instance key. Tripo's materials are named by hash: those take the name of the first
    object that uses one (Choker's is shared with Hair_High_Bum and Holster). The rest keep their name."""
    keys = {}
    for f in manifest["fbx"]:
        for m in f["materiais"]:
            if m not in keys:
                keys[m] = f["objetos"][0] if m.startswith("tripo_mat") else re.sub(r"^M_", "", m)
    return keys


def import_textures(manifest, keys):
    tex_of, tasks = {}, []
    for m, key in keys.items():
        src = manifest["materiais"][m]["imagem"]
        if not src:
            continue
        if not os.path.isfile(src):
            raise RuntimeError("missing texture %s (material %s)" % (src, m))
        norm = os.path.normcase(os.path.abspath(src))
        if norm not in tex_of:
            # named after the file (drow_jacket.png serves the jacket and the bikini bottom); the PNGs the export
            # wrote out of packed Tripo images are named by hash, and take the material's key
            stem = re.sub(r"^drow_", "", os.path.splitext(os.path.basename(src))[0], flags=re.I)
            tex_of[norm] = "T_Drow_" + (key if stem.lower().startswith("tripo") else stem)
            t = unreal.AssetImportTask()
            t.set_editor_properties({"filename": src, "destination_path": TEX_DIR, "destination_name": tex_of[norm],
                                     "automated": True, "replace_existing": True, "save": False})
            tasks.append(t)
    tools.import_asset_tasks(tasks)
    for name in sorted(set(tex_of.values())):
        tex = assets.load_asset(TEX_DIR + "/" + name)
        if tex is None:
            raise RuntimeError("texture did not import: " + name)
        w, h = tex.blueprint_get_size_x(), tex.blueprint_get_size_y()
        if max(w, h) > MAX_TEX:
            tex.set_editor_property("max_texture_size", MAX_TEX)
            assets.save_loaded_asset(tex)
        log("texture %s %dx%d%s" % (name, w, h, " (capped at %d)" % MAX_TEX if max(w, h) > MAX_TEX else ""))
    return {m: tex_of[os.path.normcase(os.path.abspath(manifest["materiais"][m]["imagem"]))]
            for m in keys if manifest["materiais"][m]["imagem"]}


def expr(mat, cls, x, y, **props):
    e = mel.create_material_expression(mat, cls, x, y)
    if props:
        e.set_editor_properties(props)
    return e


def link(a, a_out, b, b_in):
    if not mel.connect_material_expressions(a, a_out, b, b_in):
        raise RuntimeError("could not connect %s.%s -> %s.%s" % (a.get_name(), a_out, b.get_name(), b_in))


def to_property(a, a_out, prop):
    if not mel.connect_material_property(a, a_out, prop):
        raise RuntimeError("could not connect %s.%s -> %s" % (a.get_name(), a_out, prop))


def build_base(default_tex):
    """M_SpaceAmazon_Base's shape: texture * tint or tint alone, roughness."""
    path = MAT_DIR + "/M_Drow_Base"
    if assets.does_asset_exist(path):
        return assets.load_asset(path)
    mat = tools.create_asset("M_Drow_Base", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("used_with_skeletal_mesh", True)
    mat.set_editor_property("used_with_morph_targets", True)
    base = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -900, -300, parameter_name="BaseColor",
                sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
                texture=assets.load_asset(TEX_DIR + "/" + default_tex))
    tint = expr(mat, unreal.MaterialExpressionVectorParameter, -900, -50, parameter_name="Tint",
                default_value=unreal.LinearColor(1, 1, 1, 1))
    mul = expr(mat, unreal.MaterialExpressionMultiply, -600, -250)
    link(base, "RGB", mul, "A")
    link(tint, "RGB", mul, "B")
    use_tex = expr(mat, unreal.MaterialExpressionStaticSwitchParameter, -400, -250,
                   parameter_name="UseBaseColorTexture", default_value=True)
    link(mul, "", use_tex, "True")
    link(tint, "RGB", use_tex, "False")
    to_property(use_tex, "", MP.MP_BASE_COLOR)
    rough = expr(mat, unreal.MaterialExpressionScalarParameter, -400, 100, parameter_name="Roughness", default_value=0.6)
    to_property(rough, "", MP.MP_ROUGHNESS)
    mel.recompile_material(mat)
    assets.save_loaded_asset(mat)
    return mat


def build_instances(manifest, keys, tex, base):
    factory = unreal.MaterialInstanceConstantFactoryNew()
    out = {}
    for m, key in keys.items():
        info = manifest["materiais"][m]
        name = "MI_Drow_" + key
        path = MAT_DIR + "/" + name
        mi = assets.load_asset(path) if assets.does_asset_exist(path) else \
            tools.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant, factory)
        mel.set_material_instance_parent(mi, base)
        mel.set_material_instance_static_switch_parameter_value(mi, "UseBaseColorTexture", m in tex)
        if m in tex:
            mel.set_material_instance_texture_parameter_value(mi, "BaseColor", assets.load_asset(TEX_DIR + "/" + tex[m]))
        else:
            c = info["cor"] or [1, 1, 1]
            mel.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(c[0], c[1], c[2], 1))
        mel.set_material_instance_scalar_parameter_value(mi, "Roughness",
                                                         info["rugosidade"] if info["rugosidade"] is not None else 0.6)
        two = bool(set(info["objetos"]) & TWO_SIDED)
        o = mi.get_editor_property("base_property_overrides")
        o.set_editor_properties({"override_two_sided": True, "two_sided": two})
        mi.set_editor_property("base_property_overrides", o)
        mel.update_material_instance(mi)
        assets.save_loaded_asset(mi)
        out[m] = mi
        log("material %s -> %s%s%s" % (m, name, " (%s)" % tex[m] if m in tex else " (tint)", ", two-sided" if two else ""))
    return out


def assign(mesh, entry, mis):
    # Reading a struct out of an unreal.Array gives a copy: edit it, then put it back.
    slots = mesh.get_editor_property("materials")
    missing = []
    for i in range(len(slots)):
        s = slots[i]
        slot = clean(str(s.get_editor_property("material_slot_name")))
        match = [m for m in entry["materiais"] if slot.startswith(clean(m))]
        if not match:
            missing.append(slot)
            continue
        s.set_editor_property("material_interface", mis[max(match, key=len)])
        slots[i] = s
    if missing:
        raise RuntimeError("%s: slots with no Blender material: %s" % (mesh.get_name(), missing))
    mesh.set_editor_property("materials", slots)


def check_morphs(mesh, entry):
    got = {str(n) for n in mesh.get_all_morph_target_names()}
    want = set(entry["chaves"])
    lost = sorted(want - got)
    # an expression key may be identical to the basis on the eyes or teeth and so not exported; report, but the
    # correctives (CORR_*) must all be there, or the leader's curve drives nothing on this piece
    lost_corr = [k for k in lost if k.startswith("CORR_")]
    if lost_corr:
        raise RuntimeError("%s: corrective morph targets missing: %s" % (mesh.get_name(), lost_corr))
    return len(got), lost


def import_props(socket_mesh):
    props_dir = os.path.join(ART, "Props")
    sock_file = os.path.join(props_dir, "soquetes_unreal.json")
    if not os.path.isfile(sock_file):
        unreal.log_warning("Drow: no %s (export with --soquetes)" % sock_file)
        return
    with open(sock_file, encoding="utf-8") as fh:
        sockets = json.load(fh)["soquetes"]
    meshes = sorted({s["static_mesh"] for s in sockets.values() if s})
    for name in meshes:
        src = os.path.join(props_dir, name + ".fbx")
        o = unreal.FbxImportUI()
        o.set_editor_properties({"import_mesh": True, "import_as_skeletal": False, "import_animations": False,
                                 "import_materials": False, "import_textures": False,
                                 "mesh_type_to_import": unreal.FBXImportType.FBXIT_STATIC_MESH})
        o.static_mesh_import_data.set_editor_properties({"convert_scene": True, "force_front_x_axis": False,
                                                         "combine_meshes": True, "auto_generate_collision": False})
        tools.import_asset_tasks([task(src, PROP_DIR, o)])
        sm = assets.load_asset(PROP_DIR + "/" + name)
        if not isinstance(sm, unreal.StaticMesh):
            raise RuntimeError("prop did not import: " + src)
        for i, sl in enumerate(sm.get_editor_property("static_materials")):
            slot = clean(str(sl.get_editor_property("material_slot_name")))
            mi = next((m for p, m in PROP_MATERIALS if slot.startswith(clean(p))), None)
            if mi is None:
                raise RuntimeError("prop %s: slot %s has no Sophia material" % (name, slot))
            sm.set_material(i, assets.load_asset(SOPHIA_MAT + "/" + mi))
        assets.save_loaded_asset(sm)
        log("prop %s/%s" % (PROP_DIR, name))
    # sockets on the leader mesh, created or updated in place (USocketTools: Python cannot name a socket)
    for sname, s in sorted(sockets.items()):
        if not s:
            log("socket %s: none yet" % sname)
            continue
        r = s["rotator"]
        loc = unreal.Vector(*s["loc_cm"])
        rot = unreal.Rotator(roll=r["roll"], pitch=r["pitch"], yaw=r["yaw"])
        if not unreal.SocketTools.set_mesh_socket(socket_mesh, sname, s["osso"], loc, rot):
            raise RuntimeError("socket %s: bone %s not in %s" % (sname, s["osso"], socket_mesh.get_name()))
        sock = socket_mesh.find_socket(sname)
        got_l, got_r = sock.get_editor_property("relative_location"), sock.get_editor_property("relative_rotation")
        d_rot = max(abs(got_r.roll - rot.roll), abs(got_r.pitch - rot.pitch), abs(got_r.yaw - rot.yaw))
        if str(sock.get_editor_property("bone_name")) != s["osso"] or (got_l - loc).length() > 1e-3 or d_rot > 1e-3:
            raise RuntimeError("socket %s read back as %s %s %s" % (sname, sock.get_editor_property("bone_name"), got_l, got_r))
        log("socket %s on %s: %s, (roll %.3f, pitch %.3f, yaw %.3f)" % (sname, s["osso"], s["loc_cm"], r["roll"], r["pitch"], r["yaw"]))
    assets.save_loaded_asset(socket_mesh)


def main():
    with open(os.path.join(ART, NAME + "_modular.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    run("Interchange.FeatureFlags.Import.FBX False")
    # Interchange's texture import asserts on the Slate application, which a commandlet does not have
    run("Interchange.FeatureFlags.Import.PNG False")
    try:
        keys = instance_names(manifest)
        tex = import_textures(manifest, keys)
        leader_entry = next(f for f in manifest["fbx"] if f["lider"])
        mis = build_instances(manifest, keys, tex, build_base(tex[leader_entry["materiais"][0]]))

        tools.import_asset_tasks([task(os.path.join(ART, leader_entry["arquivo"]), ROOT, mesh_options())])
        leader = assets.load_asset("%s/%s" % (ROOT, NAME))
        if not isinstance(leader, unreal.SkeletalMesh):
            raise RuntimeError("leader did not import: %s/%s" % (ROOT, NAME))
        skeleton = leader.skeleton
        bones = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(unreal.AnimPoseExtensions.get_reference_pose(skeleton))]
        if len(bones) != manifest["ossos"]:
            raise RuntimeError("skeleton has %d bones, Blender %d" % (len(bones), manifest["ossos"]))

        meshes = [(leader_entry, leader)]
        pieces = [f for f in manifest["fbx"] if not f["lider"]]
        tools.import_asset_tasks([task(os.path.join(ART, f["arquivo"]), PIECE_DIR, mesh_options(skeleton)) for f in pieces])
        for f in pieces:
            m = assets.load_asset("%s/%s" % (PIECE_DIR, f["nome"]))
            if not isinstance(m, unreal.SkeletalMesh):
                raise RuntimeError("piece did not import: %s/%s" % (PIECE_DIR, f["nome"]))
            if m.skeleton != skeleton:
                raise RuntimeError("%s is on %s, not %s" % (f["nome"], m.skeleton.get_path_name(), skeleton.get_path_name()))
            meshes.append((f, m))
        for f, m in meshes:
            assign(m, f, mis)
            n, lost = check_morphs(m, f)
            assets.save_loaded_asset(m)
            log("%s: %d morph targets, %d material slots%s%s" % (
                m.get_name(), n, len(m.get_editor_property("materials")), ", hidden in Blender" if f["escondida"] else "",
                "; not exported (equal to the basis): %s" % lost if lost else ""))

        clips = sorted(os.path.join(ART, x) for x in os.listdir(ART)
                       if x.startswith(NAME + "_") and x.lower().endswith(".fbx"))
        tools.import_asset_tasks([task(c, ANIM_DIR, anim_options(skeleton)) for c in clips])
        for c in clips:
            path = "%s/%s" % (ANIM_DIR, os.path.splitext(os.path.basename(c))[0])
            a = assets.load_asset(path)
            if not isinstance(a, unreal.AnimSequence):
                raise RuntimeError("clip did not import: " + path)
            log("clip %s, %d keys" % (path, a.get_editor_property("number_of_sampled_keys")))

        import_props(leader)
        # the task's save flag writes only the primary asset; the skeleton and physics asset stay dirty
        saved = assets.save_directory(ROOT, only_if_is_dirty=False, recursive=True)
        log("saved %s: %s" % (ROOT, saved))
        log("%d bones; leader + %d pieces on %s; %d clips" % (len(bones), len(pieces), skeleton.get_name(), len(clips)))
    finally:
        run("Interchange.FeatureFlags.Import.FBX True")
        run("Interchange.FeatureFlags.Import.PNG True")


main()
