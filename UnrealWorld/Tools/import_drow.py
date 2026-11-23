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

    -script="D:/UnrealWorld/UnrealWorld/Tools/import_drow.py texturas"
only reimports the manifest's textures over T_Drow_* and saves them. Meshes, materials, clips and the 465 batch clips
stay untouched, since a full run rewrites the whole /Game/Chars/Drow tree (drow handoff, recolour step 4,
2026-11-22: only the skin, eye and hair PNGs changed, and they keep their paths).

    -script="D:/UnrealWorld/UnrealWorld/Tools/import_drow.py pecas"
reimports only the pieces: their textures, their material instances and the 14 Pecas/*.fbx, and saves only those.
Then it deletes the T_Drow_* textures the manifest no longer names, if nothing references them. Written for step 7-8
(drow handoff, 2026-11-22): textura_peca.py gave each piece its own small texture and a new UV0, so the meshes and
the materials change but the leader, the clips and the props do not.

    -script="D:/UnrealWorld/UnrealWorld/Tools/import_drow.py mascaras"
the body masks (drow handoff, step 9, 2026-11-23): everything "pecas" does, plus the mask textures (mascaras/ of the
export: uncompressed, nearest, no mips), M_Drow_Masked (M_Drow_Base plus the WPO mask node) as the parent of the
skin's, the shirt's and the gym top's instances, and the leader reimported, because the body now carries the mask
address as UV 1. The leader must keep its skeleton, physics asset, post-process Anim Blueprint and morph targets
(checked); its sockets are set again. Clips and props are not touched. ADrow::UpdateBodyMasks sets Wear/Wear2 from the
pieces' Visible flags. A later "pecas" keeps the masked parent.
"""
import json
import os
import re
import sys

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
# Body masks (step 9). The objects whose material takes M_Drow_Masked, with their mask textures (BodyMasks,
# BodyMasks2). gurps generate_outfit_masks.py writes the body's into mascaras/, the shirt's and the gym top's (masked
# by the jacket) into mascaras/<Piece>/; exportar_pacote_unreal.py --mascaras copies that tree.
MASKED = {"Base_Body_Rigged": ("T_Drow_BodyMasks", "T_Drow_BodyMasks2"),
          "Shirt": ("T_Drow_ShirtMasks", None), "Gym_Top": ("T_Drow_GymTopMasks", None)}
MASK_FILES = {"T_Drow_BodyMasks": "masks_rgba.png", "T_Drow_BodyMasks2": "masks_rgba_2.png",
              "T_Drow_ShirtMasks": "Shirt/masks_rgba.png", "T_Drow_GymTopMasks": "Gym_Top/masks_rgba.png"}
MASK_NONE = "T_Drow_MasksNone"   # 4x4 white: a BodyMasks2 the mesh does not have hides nothing
MASKED_MAT = "M_Drow_Masked"
# The same NaN trick as Sophia's and Fearing's (UnrealWorld Art/sophia_jaqueta_chaos_cloth.md, "Body masks"). WPO runs
# per vertex; a triangle with a NaN vertex is not drawn, in the shadow pass too. Mask 0 = hidden, Wear 1 = worn.
MASK_HLSL = """float4 m = Tex.SampleLevel(TexSampler, UV, 0);
float4 m2 = Tex2.SampleLevel(Tex2Sampler, UV, 0);
float hidden = dot(step(m, 0.5), Wear) + dot(step(m2, 0.5), Wear2);
return hidden > 0.5 ? asfloat(0x7fc00000).xxx : float3(0, 0, 0);"""
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


def build_base(default_tex, name="M_Drow_Base", masked=False):
    """M_SpaceAmazon_Base's shape: texture * tint or tint alone, roughness. masked: plus the body mask node on World
    Position Offset (M_Drow_Masked), rebuilt in place on every run so that a change to the node reaches it."""
    path = MAT_DIR + "/" + name
    if assets.does_asset_exist(path) and not masked:
        return assets.load_asset(path)
    if assets.does_asset_exist(path):
        mat = assets.load_asset(path)
        mel.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset(name, MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
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
    if masked:
        add_mask_node(mat)
    mel.recompile_material(mat)
    assets.save_loaded_asset(mat)
    return mat


def add_mask_node(mat):
    # Max WPO Displacement stays 0, which means no clamp: a clamped NaN is no longer a NaN.
    mat.set_editor_property("max_world_position_offset_displacement", 0.0)
    none = assets.load_asset(TEX_DIR + "/" + MASK_NONE)
    t1 = expr(mat, unreal.MaterialExpressionTextureObjectParameter, -900, 350, parameter_name="BodyMasks", texture=none,
              sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    t2 = expr(mat, unreal.MaterialExpressionTextureObjectParameter, -900, 550, parameter_name="BodyMasks2", texture=none,
              sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    uv = expr(mat, unreal.MaterialExpressionTextureCoordinate, -900, 750, coordinate_index=1)
    custom = expr(mat, unreal.MaterialExpressionCustom, -300, 500, code=MASK_HLSL, description="BodyMasks",
                  output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    inputs = []
    for n in ("Tex", "Tex2", "UV", "Wear", "Wear2"):
        ci = unreal.CustomInput()
        ci.set_editor_property("input_name", n)
        inputs.append(ci)
    custom.set_editor_property("inputs", inputs)
    link(t1, "", custom, "Tex")
    link(t2, "", custom, "Tex2")
    link(uv, "", custom, "UV")
    for i, n in enumerate(("Wear", "Wear2")):
        # 0 = not worn: nothing hides until ADrow::UpdateBodyMasks says what she wears
        w = expr(mat, unreal.MaterialExpressionVectorParameter, -900, 950 + 250 * i, parameter_name=n,
                 default_value=unreal.LinearColor(0, 0, 0, 0))
        app = expr(mat, unreal.MaterialExpressionAppendVector, -600, 950 + 250 * i)
        link(w, "RGB", app, "A")
        link(w, "A", app, "B")
        link(app, "", custom, n)
    to_property(custom, "", MP.MP_WORLD_POSITION_OFFSET)


def import_masks():
    """The mask textures: one texel per vertex, so uncompressed, nearest, no mips, never streamed (BC compression
    bleeds into the neighbouring vertices' decisions). Plus the 4x4 white MASK_NONE."""
    import struct
    import zlib
    none_png = os.path.join(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir()),
                            "drow_masks_none.png")
    raw = b"".join(b"\0" + b"\xff" * 16 for _ in range(4))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    with open(none_png, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 6, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    files = {MASK_NONE: none_png}
    for name, rel in MASK_FILES.items():
        src = os.path.join(ART, "mascaras", rel)
        if not os.path.isfile(src):
            raise RuntimeError("missing mask %s (export with --mascaras)" % src)
        files[name] = src
    tasks = []
    for name, src in files.items():
        t = unreal.AssetImportTask()
        t.set_editor_properties({"filename": src, "destination_path": TEX_DIR, "destination_name": name,
                                 "automated": True, "replace_existing": True, "save": False})
        tasks.append(t)
    tools.import_asset_tasks(tasks)
    TC = unreal.TextureCompressionSettings
    MG = unreal.TextureMipGenSettings
    for name in files:
        tex = assets.load_asset(TEX_DIR + "/" + name)
        if tex is None:
            raise RuntimeError("mask texture did not import: " + name)
        tex.set_editor_properties({
            "srgb": False, "never_stream": True,
            "compression_settings": getattr(TC, "TC_VECTOR_DISPLACEMENTMAP", None) or TC.TC_VECTOR_DISPLACEMENT_MAP,
            "filter": unreal.TextureFilter.TF_NEAREST,
            "mip_gen_settings": getattr(MG, "TMGS_NO_MIPMAPS", None) or MG.TMGS_NOMIPMAPS})
        assets.save_loaded_asset(tex, only_if_is_dirty=False)
        log("mask texture %s %dx%d" % (name, tex.blueprint_get_size_x(), tex.blueprint_get_size_y()))


def build_instances(manifest, keys, tex, base, masked_base=None):
    factory = unreal.MaterialInstanceConstantFactoryNew()
    out = {}
    for m, key in keys.items():
        info = manifest["materiais"][m]
        name = "MI_Drow_" + key
        path = MAT_DIR + "/" + name
        mi = assets.load_asset(path) if assets.does_asset_exist(path) else \
            tools.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant, factory)
        masks = [MASKED[o] for o in info["objetos"] if o in MASKED] if masked_base else []
        mel.set_material_instance_parent(mi, masked_base if masks else base)
        for param, t in zip(("BodyMasks", "BodyMasks2"), masks[0] if masks else ()):
            mel.set_material_instance_texture_parameter_value(mi, param, assets.load_asset(TEX_DIR + "/" + (t or MASK_NONE)))
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
        assets.save_loaded_asset(mi, only_if_is_dirty=False)
        out[m] = mi
        log("material %s -> %s%s%s%s" % (m, name, " (%s)" % tex[m] if m in tex else " (tint)", ", two-sided" if two else "",
                                         ", masked by %s" % (masks[0],) if masks else ""))
    return out


def assign(mesh, entry, mis):
    # Reading a struct out of an unreal.Array gives a copy: edit it, then put it back.
    slots = mesh.get_editor_property("materials")
    missing = []
    for i in range(len(slots)):
        s = slots[i]
        slot = clean(str(s.get_editor_property("material_slot_name")))
        match = [m for m in entry["materiais"] if slot.startswith(clean(m))]
        if not match and len(entry["materiais"]) == 1:
            # textura_peca.py (2026-11-22) renamed the Tripo materials (tripo_mat_<hash>) to M_<Piece>. A reimport
            # keeps the old slot (reset_to_fbx_on_material_conflict does not apply to an automated import) and adds
            # the new one, which the sections use. Removing the old one would shift the section indices; the piece
            # has one material, so the old slot gets it too
            match = list(entry["materiais"])
            log("%s: slot %s, from an earlier import, gets %s too" % (mesh.get_name(), slot, match[0]))
        if not match:
            missing.append(slot)
            continue
        s.set_editor_property("material_interface", mis[max(match, key=len)])
        slots[i] = s
    if missing:
        raise RuntimeError("%s: slots with no Blender material: %s" % (mesh.get_name(), missing))
    mesh.set_editor_property("materials", slots)
    # read back: a slot left empty renders the default grey material and no import error says so
    empty = [str(x.get_editor_property("material_slot_name")) for x in mesh.get_editor_property("materials")
             if x.get_editor_property("material_interface") is None]
    if empty:
        raise RuntimeError("%s: slots still empty after assigning: %s" % (mesh.get_name(), empty))


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
    set_sockets(socket_mesh, sockets)


def set_sockets(socket_mesh, sockets):
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


def import_pieces(manifest, keys, tex):
    """The pieces alone: material instances over the existing master, the 14 meshes onto the existing skeleton.
    The leader is loaded, not reimported. Saves only what it touched."""
    for name in sorted(set(tex.values())):
        assets.save_asset(TEX_DIR + "/" + name, only_if_is_dirty=False)
    base = assets.load_asset(MAT_DIR + "/M_Drow_Base")
    leader = assets.load_asset("%s/%s" % (ROOT, NAME))
    if base is None or not isinstance(leader, unreal.SkeletalMesh):
        raise RuntimeError("pecas needs a full import first: no %s/M_Drow_Base or %s/%s" % (MAT_DIR, ROOT, NAME))
    skeleton = leader.skeleton
    # the shirt and the gym top keep M_Drow_Masked once "mascaras" has made it
    masked = assets.load_asset(MAT_DIR + "/" + MASKED_MAT) if assets.does_asset_exist(MAT_DIR + "/" + MASKED_MAT) else None
    mis = build_instances(manifest, keys, tex, base, masked)
    pieces = [f for f in manifest["fbx"] if not f["lider"]]
    tools.import_asset_tasks([task(os.path.join(ART, f["arquivo"]), PIECE_DIR, mesh_options(skeleton)) for f in pieces])
    for f in pieces:
        m = assets.load_asset("%s/%s" % (PIECE_DIR, f["nome"]))
        if not isinstance(m, unreal.SkeletalMesh):
            raise RuntimeError("piece did not import: %s/%s" % (PIECE_DIR, f["nome"]))
        if m.skeleton != skeleton:
            raise RuntimeError("%s is on %s, not %s" % (f["nome"], m.skeleton.get_path_name(), skeleton.get_path_name()))
        assign(m, f, mis)
        n, lost = check_morphs(m, f)
        # setting "materials" does not mark the package dirty, so a save "if dirty" kept the state the import task
        # saved, with the new slot empty: six pieces rendered grey (2026-11-22). The full run hid this, since it
        # saves the whole directory
        if not assets.save_loaded_asset(m, only_if_is_dirty=False):
            raise RuntimeError("could not save " + m.get_path_name())
        log("%s: %d morph targets, %d material slots%s" % (
            m.get_name(), n, len(m.get_editor_property("materials")), ", hidden in Blender" if f["escondida"] else ""))
    assets.save_loaded_asset(skeleton, only_if_is_dirty=True)
    # the old 4K atlases: named after their PNG (drow_tenis, drow_cabelo_coque, ...), which no material reads now
    # the mask textures are not in the manifest; the body's are not referenced yet when "mascaras" gets here
    wanted = {t.lower() for t in tex.values()} | {t.lower() for t in MASK_FILES} | {MASK_NONE.lower()}
    leader_tex = [manifest["materiais"][m]["imagem"] for m in next(f for f in manifest["fbx"] if f["lider"])["materiais"]]
    wanted |= {"t_drow_" + re.sub(r"^drow_", "", os.path.splitext(os.path.basename(x))[0], flags=re.I).lower()
               for x in leader_tex if x}
    for path in assets.list_assets(TEX_DIR, recursive=False, include_folder=False):
        name = path.split("/")[-1].split(".")[0]
        if not name.startswith("T_Drow_") or name.lower() in wanted:
            continue
        refs = assets.find_package_referencers_for_asset(path.split(".")[0], load_assets_to_confirm=True)
        if refs:
            log("kept %s: still referenced by %s" % (name, list(refs)))
        elif assets.delete_asset(path.split(".")[0]):
            log("deleted %s: no material reads it" % name)
        else:
            raise RuntimeError("could not delete " + path)
    log("pecas: %d pieces, %d textures, %d material instances reimported and saved; leader, clips and props untouched"
        % (len(pieces), len(set(tex.values())), len(mis)))



def import_masks_and_leader(manifest, keys, tex):
    """mascaras: the mask textures and M_Drow_Masked, the pieces as in "pecas" (the shirt's and the gym top's
    instances get the masked parent), then the leader reimported onto its own skeleton, its skin on M_Drow_Masked."""
    import_masks()
    leader_entry = next(f for f in manifest["fbx"] if f["lider"])
    build_base(tex[leader_entry["materiais"][0]], MASKED_MAT, masked=True)
    assets.save_asset(MAT_DIR + "/" + MASKED_MAT, only_if_is_dirty=False)
    import_pieces(manifest, {m: k for m, k in keys.items()
                             if any(m in f["materiais"] for f in manifest["fbx"] if not f["lider"])}, tex)
    leader = assets.load_asset("%s/%s" % (ROOT, NAME))
    skeleton = leader.skeleton

    def state(m):
        return {"physics": m.get_editor_property("physics_asset"),
                "post": m.get_editor_property("post_process_anim_blueprint"),
                "morphs": len(m.get_all_morph_target_names())}
    before = state(leader)
    tools.import_asset_tasks([task(os.path.join(ART, leader_entry["arquivo"]), ROOT, mesh_options(skeleton))])
    leader = assets.load_asset("%s/%s" % (ROOT, NAME))
    if leader.skeleton != skeleton:
        raise RuntimeError("leader reimported onto %s" % leader.skeleton.get_path_name())
    after = state(leader)
    if after != before:
        raise RuntimeError("leader changed on reimport: %s -> %s" % (before, after))
    base = assets.load_asset(MAT_DIR + "/M_Drow_Base")
    masked = assets.load_asset(MAT_DIR + "/" + MASKED_MAT)
    mis = build_instances(manifest, {m: keys[m] for m in leader_entry["materiais"]}, tex, base, masked)
    assign(leader, leader_entry, mis)
    check_morphs(leader, leader_entry)
    with open(os.path.join(ART, "Props", "soquetes_unreal.json"), encoding="utf-8") as fh:
        set_sockets(leader, json.load(fh)["soquetes"])
    if not assets.save_loaded_asset(leader, only_if_is_dirty=False):
        raise RuntimeError("could not save " + leader.get_path_name())
    assets.save_loaded_asset(skeleton, only_if_is_dirty=True)
    log("mascaras: leader reimported (%d morph targets; physics asset and post process kept); M_Drow_Masked on %s"
        % (after["morphs"], sorted(MASKED)))


def main():
    with open(os.path.join(ART, NAME + "_modular.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    run("Interchange.FeatureFlags.Import.FBX False")
    # Interchange's texture import asserts on the Slate application, which a commandlet does not have
    run("Interchange.FeatureFlags.Import.PNG False")
    try:
        keys = instance_names(manifest)
        if "mascaras" in sys.argv[1:]:
            import_masks_and_leader(manifest, keys, import_textures(manifest, keys))
            return
        if "pecas" in sys.argv[1:]:
            # only the pieces' materials: the leader's textures and instances stay as they are
            keys = {m: k for m, k in keys.items()
                    if any(m in f["materiais"] for f in manifest["fbx"] if not f["lider"])}
        tex = import_textures(manifest, keys)
        if "texturas" in sys.argv[1:] and "pecas" not in sys.argv[1:]:
            for name in sorted(set(tex.values())):
                assets.save_asset(TEX_DIR + "/" + name, only_if_is_dirty=False)
            log("texturas: %d textures reimported and saved; meshes, materials and clips untouched" % len(set(tex.values())))
            return
        leader_entry = next(f for f in manifest["fbx"] if f["lider"])
        if "pecas" in sys.argv[1:]:
            import_pieces(manifest, keys, tex)
            return
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
