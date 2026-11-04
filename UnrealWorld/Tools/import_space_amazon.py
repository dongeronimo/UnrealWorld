"""Imports the Space Amazon (skeletal mesh + clips + textures + materials) from Art/space_amazon/unreal, headless or in the editor.

    UnrealEditor-Cmd.exe UnrealWorld.uproject -run=pythonscript -script="Tools/import_space_amazon.py"

or, in the editor's Output Log (Cmd mode):  py "D:/UnrealWorld/UnrealWorld/Tools/import_space_amazon.py"

Reimports over existing assets, so references to them survive. Uses the legacy FBX importer
(Interchange.FeatureFlags.Import.FBX False for this run only): its options can be set from script and
read back, and the parity test (paridade_control_rig.py) checks the result bone by bone anyway. The
Blender side is exportar_unreal.py (cm scene, UnitScaleFactor 1, A-pose as bind and reference pose).

Materials are built here, not taken from the FBX: the importer never made any for her (the slots came
in empty on 2026-10-29), and three of them need settings an FBX cannot carry. One master
(M_SpaceAmazon_Base, the shape of M_Sophia_Base without the ORM branch, which she has no textures for)
and one instance per Blender material, with Blender's roughness and flat colours. Safe to run again.

2026-11-03 (gurps export from expr/e32_katana.blend): the armour atlas, the two gloves and the
scabbard got their slots, and the eyes are the anime texture. Weapons are not in the character FBX
(exportar_pacote_unreal.py --soquetes): Props/Katana.fbx comes in as a static mesh in ROOT/Props with
the scabbard's material. Its two sockets are set by hand from Props/soquetes_unreal.json (the guide,
D:/UnrealWorld/SpaceAmazon_Unreal.md).
"""
import glob
import os

import unreal

ART = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Art", "space_amazon", "unreal"))
ROOT = "/Game/Chars/SpaceAmazon"
ANIM_DIR = ROOT + "/animclips"
TEX_DIR = ROOT + "/Textures"
MAT_DIR = ROOT + "/Materials"
NAME = "SpaceAmazon"
HAIR_BONES = ("CC_Extra_Ponytail08", "CC_Extra_L_FrontLock03", "CC_Extra_R_FrontLock03", "CC_Extra_L_Lock02", "CC_Extra_R_Lock02")

# (asset, source). exportar_unreal.py writes the packed images next to the FBX; the eye texture is not packed in the .blend.
TEXTURES = [
    ("T_SpaceAmazon_Body", os.path.join(ART, "SpaceAmazon_SpaceAmazon_Body_8k.png")),
    ("T_SpaceAmazon_Hair", os.path.join(ART, "SpaceAmazon_tripo_rgb_2aafc456_259a_4bc5_adf4_effd21ec6d91.png")),
    ("T_SpaceAmazon_Lashes", os.path.join(ART, "SpaceAmazon_Cilios.png")),
    ("T_SpaceAmazon_Teeth", os.path.join(ART, "SpaceAmazon_Dentes.png")),
    ("T_SpaceAmazon_Mouth", os.path.join(ART, "SpaceAmazon_Boca.png")),
    ("T_SpaceAmazon_Eyes", os.path.normpath(os.path.join(ART, "..", "expr", "e25_olho_anime.png"))),
    ("T_SpaceAmazon_Armour", os.path.join(ART, "SpaceAmazon_tripo_rgb_020e62f1_15a8_4e27_adde_c48f0143a961.png")),
    ("T_SpaceAmazon_Glove_L", os.path.join(ART, "SpaceAmazon_Left_Glove.png")),
    ("T_SpaceAmazon_Glove_R", os.path.join(ART, "SpaceAmazon_Right_Glove.png")),
    ("T_SpaceAmazon_Katana", os.path.join(ART, "SpaceAmazon_tripo_rgb_e45e460f_7eba_4f65_b196_4f7bd77e604a.png")),
]

# (FBX slot prefix, the Blender material name; instance; texture; roughness; extra)
#   two_sided: Blender draws both sides of everything; these are the ones seen from the inside or that are open sheets.
#   clip: Masked at this alpha, the GREATER_THAN node of M_Cilios.
#   tint: the Principled base colour of a material with no texture (linear, like Blender's).
# Hair and the two bikinis share the Tripo material, so they are one slot.
INSTANCES = [
    ("M_SpaceAmazon_Body", "MI_SpaceAmazon_Body", "T_SpaceAmazon_Body", 0.9, {}),
    ("M_Cilios", "MI_SpaceAmazon_Lashes", "T_SpaceAmazon_Lashes", 0.5, {"two_sided": True, "clip": 0.4}),
    ("tripo_mat_282d6479", "MI_SpaceAmazon_Hair", "T_SpaceAmazon_Hair", 0.9, {"two_sided": True}),
    ("Dentes", "MI_SpaceAmazon_Teeth", "T_SpaceAmazon_Teeth", 0.3, {}),
    ("M_Boca", "MI_SpaceAmazon_Mouth", "T_SpaceAmazon_Mouth", 0.7, {"two_sided": True}),
    ("Olhos", "MI_SpaceAmazon_Eyes", "T_SpaceAmazon_Eyes", 0.35, {}),
    ("M_Lingua", "MI_SpaceAmazon_Tongue", None, 0.45, {"tint": unreal.LinearColor(0.305, 0.048, 0.061, 1)}),
    ("M_Orbita", "MI_SpaceAmazon_Socket", None, 0.7, {"two_sided": True, "tint": unreal.LinearColor(0.275, 0.055, 0.078, 1)}),
    # the 14 armour pieces share one Tripo atlas; the skirt and the fins are open shells
    ("tripo_mat_8916083a", "MI_SpaceAmazon_Armour", "T_SpaceAmazon_Armour", 0.9, {"two_sided": True}),
    ("M_Left_Glove", "MI_SpaceAmazon_Glove_L", "T_SpaceAmazon_Glove_L", 0.9, {}),
    ("M_Right_Glove", "MI_SpaceAmazon_Glove_R", "T_SpaceAmazon_Glove_R", 0.9, {}),
    # the scabbard (skinned, in this FBX) and the katana (Props/Katana.fbx) share the Tripo atlas
    ("tripo_mat_b100a64c", "MI_SpaceAmazon_Katana", "T_SpaceAmazon_Katana", 0.9, {"two_sided": True}),
]
PROP_DIR = ROOT + "/Props"
PROPS = [("Katana", "MI_SpaceAmazon_Katana")]

assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
MP = unreal.MaterialProperty


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
                             "import_materials": False, "import_textures": False,
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


def import_textures():
    ts = []
    for name, src in TEXTURES:
        if not os.path.isfile(src):
            raise RuntimeError("missing source texture: " + src)
        t = unreal.AssetImportTask()
        t.set_editor_properties({"filename": src, "destination_path": TEX_DIR, "destination_name": name,
                                 "automated": True, "replace_existing": True, "save": False})
        ts.append(t)
    tools.import_asset_tasks(ts)
    for name, _ in TEXTURES:
        tex = assets.load_asset(TEX_DIR + "/" + name)
        if tex is None:
            raise RuntimeError("texture did not import: " + name)
        unreal.log("SpaceAmazon: texture %s %dx%d" % (name, tex.blueprint_get_size_x(), tex.blueprint_get_size_y()))


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


def build_base():
    path = MAT_DIR + "/M_SpaceAmazon_Base"
    if assets.does_asset_exist(path):
        return assets.load_asset(path)
    mat = tools.create_asset("M_SpaceAmazon_Base", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("used_with_skeletal_mesh", True)
    mat.set_editor_property("used_with_morph_targets", True)
    base = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -900, -300, parameter_name="BaseColor",
                sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_COLOR,
                texture=assets.load_asset(TEX_DIR + "/T_SpaceAmazon_Body"))
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
    to_property(base, "A", MP.MP_OPACITY_MASK)  # read only by the Masked instance (the lashes)
    rough = expr(mat, unreal.MaterialExpressionScalarParameter, -400, 100, parameter_name="Roughness", default_value=0.6)
    to_property(rough, "", MP.MP_ROUGHNESS)
    mel.recompile_material(mat)
    assets.save_loaded_asset(mat)
    return mat


def build_instances(base):
    factory = unreal.MaterialInstanceConstantFactoryNew()
    for _, name, tex, rough, extra in INSTANCES:
        path = MAT_DIR + "/" + name
        mi = assets.load_asset(path) if assets.does_asset_exist(path) else \
            tools.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant, factory)
        mel.set_material_instance_parent(mi, base)
        mel.set_material_instance_static_switch_parameter_value(mi, "UseBaseColorTexture", tex is not None)
        if tex:
            mel.set_material_instance_texture_parameter_value(mi, "BaseColor", assets.load_asset(TEX_DIR + "/" + tex))
        mel.set_material_instance_scalar_parameter_value(mi, "Roughness", rough)
        if "tint" in extra:
            mel.set_material_instance_vector_parameter_value(mi, "Tint", extra["tint"])
        o = mi.get_editor_property("base_property_overrides")
        masked = "clip" in extra
        o.set_editor_properties({
            "override_two_sided": True, "two_sided": bool(extra.get("two_sided")),
            "override_blend_mode": masked,
            "blend_mode": unreal.BlendMode.BLEND_MASKED if masked else unreal.BlendMode.BLEND_OPAQUE,
            "override_opacity_mask_clip_value": masked, "opacity_mask_clip_value": extra.get("clip", 0.3333)})
        mi.set_editor_property("base_property_overrides", o)
        mel.update_material_instance(mi)
        assets.save_loaded_asset(mi)


def assign(mesh):
    # Reading a struct out of an unreal.Array gives a copy: edit it, then put it back.
    slots = mesh.get_editor_property("materials")
    sem = []
    for i in range(len(slots)):
        s = slots[i]
        nome = str(s.get_editor_property("material_slot_name"))
        mi = next((m for p, m, _, _, _ in INSTANCES if nome.lower().startswith(p.lower())), None)
        if mi is None:
            sem.append(nome)
            continue
        s.set_editor_property("material_interface", assets.load_asset(MAT_DIR + "/" + mi))
        slots[i] = s
        unreal.log("SpaceAmazon: slot %s -> %s" % (nome, mi))
    if sem:
        raise RuntimeError("slots with no material in INSTANCES: %s" % sem)
    mesh.set_editor_property("materials", slots)


def import_props():
    """Each weapon as a static mesh with its material. A failure here is logged, not raised: the
    character import has already succeeded, and the sockets are set by hand anyway."""
    for name, mi in PROPS:
        src = os.path.join(ART, "Props", name + ".fbx")
        if not os.path.isfile(src):
            unreal.log_warning("SpaceAmazon: no prop %s (export with --soquetes)" % src)
            continue
        try:
            o = unreal.FbxImportUI()
            o.set_editor_properties({"import_mesh": True, "import_as_skeletal": False, "import_animations": False,
                                     "import_materials": False, "import_textures": False,
                                     "mesh_type_to_import": unreal.FBXImportType.FBXIT_STATIC_MESH})
            o.static_mesh_import_data.set_editor_properties({"convert_scene": True, "force_front_x_axis": False,
                                                             "combine_meshes": True, "auto_generate_collision": False})
            tools.import_asset_tasks([task(src, PROP_DIR, o)])
            sm = assets.load_asset(PROP_DIR + "/" + name)
            sm.set_material(0, assets.load_asset(MAT_DIR + "/" + mi))
            unreal.log("SpaceAmazon: prop %s/%s -> %s" % (PROP_DIR, name, mi))
        except Exception as e:
            unreal.log_warning("SpaceAmazon: prop %s did not import (%s); import it by hand (guide, step 4)" % (name, e))


def main():
    run("Interchange.FeatureFlags.Import.FBX False")
    # Interchange's texture import asserts on the Slate application, which a commandlet does not have
    run("Interchange.FeatureFlags.Import.PNG False")
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

        import_textures()
        build_instances(build_base())
        assign(mesh)

        clips = sorted(f for f in glob.glob(os.path.join(ART, NAME + "_*.fbx")))
        tools.import_asset_tasks([task(f, ANIM_DIR, anim_options(skeleton)) for f in clips])
        for f in clips:
            path = "%s/%s" % (ANIM_DIR, os.path.splitext(os.path.basename(f))[0])
            a = assets.load_asset(path)
            if not isinstance(a, unreal.AnimSequence):
                raise RuntimeError("clip did not import: " + path)
            unreal.log("SpaceAmazon: clip %s, %d keys" % (path, a.get_editor_property("number_of_sampled_keys")))
        import_props()
        # the task's save flag writes only the primary asset; the skeleton, physics asset, materials
        # and textures it created stay dirty, and the mesh on disk then points at nothing
        saved = assets.save_directory(ROOT, only_if_is_dirty=False, recursive=True)
        unreal.log("SpaceAmazon: saved %s: %s" % (ROOT, saved))

        ossos = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(unreal.AnimPoseExtensions.get_reference_pose(skeleton))]
        falta = [b for b in HAIR_BONES if b not in ossos]
        unreal.log("SpaceAmazon: %d bones, %d morph targets, %d material slots; hair bones missing: %s"
                   % (len(ossos), len(mesh.get_all_morph_target_names()), len(mesh.get_editor_property("materials")), falta or "none"))
        if falta:
            raise RuntimeError("hair bones did not reach the skeleton: %s" % falta)
    finally:
        run("Interchange.FeatureFlags.Import.FBX True")
        run("Interchange.FeatureFlags.Import.PNG True")


main()
