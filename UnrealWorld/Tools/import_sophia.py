"""Imports Sophia's textures, builds her materials, and assigns them to her meshes (card 020).

Run inside the editor (Output Log, Cmd mode):

    py "D:/UnrealWorld/UnrealWorld/Tools/import_sophia.py"             textures, materials, assignment
    py "D:/UnrealWorld/UnrealWorld/Tools/import_sophia.py" --reimport  also re-import textures already there

Safe to run again. Existing textures are kept (their settings are re-checked), master materials
are built only if missing, and the instances' parameters and the mesh slots are always re-applied.
The meshes themselves are imported by hand (Sophia_Unreal.md §2): run this again after that, and
it assigns the instances to whichever meshes it finds.

Sources are Art/ (Sophia_Unreal.md §2, "The whole material map"). Checked 2026-10-27: the FBX's
embedded textures are byte-identical to these, and the FBX body matches the .blend that the masks
and wounds were generated from (vertex count, both UV channels, 52 shape keys, 118 bones).

Only M_Sophia_Base is built here, plus the lens. M_Sophia_Body and M_Sophia_Shirt (the WPO
clothing masks, 022) and the wounds (043) come later. Until then the body uses a base instance,
and the mask and wound textures are imported and waiting.
"""
import os
import sys

import unreal

ART = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Art"))
INTRO = os.path.join(ART, "grruzam_lote", "unreal", "Movements_Intro")

ROOT = "/Game/Chars/Sophia"
TEX_DIR = ROOT + "/Textures"
MAT_DIR = ROOT + "/Materials"

REIMPORT = "--reimport" in sys.argv

asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
mel = unreal.MaterialEditingLibrary


def enum(enum_type, *names):
    """The first of `names` that exists on enum_type, so a renamed member fails loudly."""
    for name in names:
        if hasattr(enum_type, name):
            return getattr(enum_type, name)
    raise RuntimeError("%s has none of %s. Members: %s" % (
        enum_type.__name__, names, [m for m in dir(enum_type) if m.isupper()]))


TC = unreal.TextureCompressionSettings
SETTINGS = {
    "color": {"srgb": True, "compression_settings": enum(TC, "TC_DEFAULT")},
    "orm": {"srgb": False, "compression_settings": enum(TC, "TC_MASKS")},
    # One texel per vertex, addressed by UV 1: no compression bleed, no filtering, no mips.
    "mask": {"srgb": False,
             "compression_settings": enum(TC, "TC_VECTOR_DISPLACEMENTMAP", "TC_VECTOR_DISPLACEMENT_MAP"),
             "filter": enum(unreal.TextureFilter, "TF_NEAREST"),
             "mip_gen_settings": enum(unreal.TextureMipGenSettings, "TMGS_NO_MIPMAPS", "TMGS_NOMIPMAPS"),
             "never_stream": True},
    "wound_tint": {"srgb": True, "compression_settings": enum(TC, "TC_BC7")},
    "wound_mask": {"srgb": False, "compression_settings": enum(TC, "TC_BC7")},
    # The file is OpenGL (green up), Unreal is DirectX.
    "normal_gl": {"srgb": False, "compression_settings": enum(TC, "TC_NORMALMAP"),
                  "flip_green_channel": True},
}

# (asset name, source file, kind)
TEXTURES = [
    ("T_Sophia_Body_Fishnet", os.path.join(ART, "Sophia_Body_Fishnet_rede_unhas.png"), "color"),
    ("T_Sophia_Body_BareLegs", os.path.join(ART, "Sophia_vag_unhas.png"), "color"),
    ("T_Sophia_Body_Redhead", os.path.join(ART, "Sophia_Body_Redhead.png"), "color"),
    ("T_Sophia_Shirt", os.path.join(ART, "Sophia_Shirt.png"), "color"),
    ("T_Sophia_Shirt_ORM", os.path.join(ART, "Sophia_Shirt_ORM.png"), "orm"),
    ("T_Sophia_Skirt", os.path.join(ART, "Sophia_Skirt.png"), "color"),
    ("T_Sophia_Skirt_ORM", os.path.join(ART, "Sophia_Skirt_ORM.png"), "orm"),
    ("T_Sophia_Jacket", os.path.join(ART, "Sophia_Jacket.png"), "color"),
    ("T_Sophia_Panty", os.path.join(ART, "Sophia_Panty.png"), "color"),
    ("T_Sophia_Panty_ORM", os.path.join(ART, "Sophia_Panty_ORM.png"), "orm"),
    ("T_Sophia_Choker", os.path.join(ART, "Sophia_Choker.png"), "color"),
    ("T_Sophia_Choker_ORM", os.path.join(ART, "Sophia_Choker_ORM.png"), "orm"),
    ("T_Sophia_Gear", os.path.join(INTRO, "Sophia_tripo_image_04970812_d53a_4a1b_86ef_6f4f97d768e1_0.png"), "color"),
    ("T_Sophia_Eyes", os.path.join(ART, "Sophia_olhos.png"), "color"),
    ("T_Sophia_Teeth", os.path.join(ART, "Sophia_dentes_dentes.png"), "color"),
    ("T_Sophia_UpperBikini", os.path.join(ART, "Sophia_Upper_Bikini.png"), "color"),
    ("T_Sophia_Katana", os.path.join(ART, "Sophia_Katana.png"), "color"),
    ("T_Sophia_Katana_ORM", os.path.join(ART, "Sophia_Katana_ORM.png"), "orm"),
    ("T_Sophia_Pistol", os.path.join(ART, "Sophia_Pistol.png"), "color"),
    ("T_Sophia_Pistol_ORM", os.path.join(ART, "Sophia_Pistol_ORM.png"), "orm"),
    ("T_Sophia_Headphone", os.path.join(ART, "Sophia_Kitty_Headphone.png"), "color"),
    # RGBA = arms (jacket), chest (shirt), hips (skirt), legs (boots); _2: R panty, G belt.
    ("T_Sophia_BodyMasks", os.path.join(ART, "sophia_masks", "masks_rgba.png"), "mask"),
    ("T_Sophia_BodyMasks2", os.path.join(ART, "sophia_masks", "masks_rgba_2.png"), "mask"),
    ("T_Sophia_ShirtMasks", os.path.join(ART, "sophia_shirt_masks", "masks_rgba.png"), "mask"),
    ("T_Sophia_Wounds_Tint", os.path.join(ART, "feridas", "Sophia_Feridas_Tint.png"), "wound_tint"),
    ("T_Sophia_Wounds_Mask", os.path.join(ART, "feridas", "Sophia_Feridas_Mask.png"), "wound_mask"),
    ("T_Sophia_Wounds_Normal", os.path.join(ART, "feridas", "Sophia_Feridas_Normal.png"), "normal_gl"),
]


def import_textures():
    tasks = []
    for name, src, _ in TEXTURES:
        if not os.path.isfile(src):
            raise RuntimeError("missing source texture: " + src)
        if assets.does_asset_exist(TEX_DIR + "/" + name) and not REIMPORT:
            continue
        task = unreal.AssetImportTask()
        task.set_editor_properties({
            "filename": src, "destination_path": TEX_DIR, "destination_name": name,
            "automated": True, "replace_existing": True, "save": False})
        tasks.append(task)
    if tasks:
        unreal.log("Sophia: importing %d textures" % len(tasks))
        asset_tools.import_asset_tasks(tasks)

    for name, _, kind in TEXTURES:
        tex = assets.load_asset(TEX_DIR + "/" + name)
        if tex is None:
            raise RuntimeError("texture did not import: " + name)
        wanted = SETTINGS[kind]
        diff = {k: v for k, v in wanted.items() if tex.get_editor_property(k) != v}
        if diff:
            tex.set_editor_properties(diff)  # one PostEditChange, so a 4K texture compresses once
            unreal.log("Sophia: %s <- %s" % (name, sorted(diff)))
        assets.save_loaded_asset(tex)


def tex(name):
    return assets.load_asset(TEX_DIR + "/" + name)


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


MP = unreal.MaterialProperty
SAMPLER = unreal.MaterialSamplerType


def build_base():
    """M_Sophia_Base, Sophia_Unreal.md §2: BaseColor (alpha -> opacity mask), and UseORM
    picking the ORM texture or flat Roughness/Metallic. Tint and UseBaseColorTexture exist for
    pieces with no texture (the glasses frame)."""
    path = MAT_DIR + "/M_Sophia_Base"
    if assets.does_asset_exist(path):
        return assets.load_asset(path)
    mat = asset_tools.create_asset("M_Sophia_Base", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("used_with_skeletal_mesh", True)

    base = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -900, -300,
                parameter_name="BaseColor", sampler_type=enum(SAMPLER, "SAMPLERTYPE_COLOR"),
                texture=tex("T_Sophia_Jacket"))
    tint = expr(mat, unreal.MaterialExpressionVectorParameter, -900, -50,
                parameter_name="Tint", default_value=unreal.LinearColor(1, 1, 1, 1))
    mul = expr(mat, unreal.MaterialExpressionMultiply, -600, -250)
    link(base, "RGB", mul, "A")
    link(tint, "RGB", mul, "B")
    use_tex = expr(mat, unreal.MaterialExpressionStaticSwitchParameter, -400, -250,
                   parameter_name="UseBaseColorTexture", default_value=True)
    link(mul, "", use_tex, "True")
    link(tint, "RGB", use_tex, "False")
    to_property(use_tex, "", MP.MP_BASE_COLOR)
    to_property(base, "A", MP.MP_OPACITY_MASK)  # read only by Masked instances (the panty)

    orm = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, -900, 250,
               parameter_name="ORM", sampler_type=enum(SAMPLER, "SAMPLERTYPE_MASKS"),
               texture=tex("T_Sophia_Choker_ORM"))
    rough = expr(mat, unreal.MaterialExpressionScalarParameter, -900, 550,
                 parameter_name="Roughness", default_value=0.6)
    metal = expr(mat, unreal.MaterialExpressionScalarParameter, -900, 650,
                 parameter_name="Metallic", default_value=0.0)
    one = expr(mat, unreal.MaterialExpressionConstant, -900, 750, r=1.0)
    for orm_out, flat, prop, y in (("G", rough, MP.MP_ROUGHNESS, 300),
                                   ("B", metal, MP.MP_METALLIC, 450),
                                   ("R", one, MP.MP_AMBIENT_OCCLUSION, 600)):
        sw = expr(mat, unreal.MaterialExpressionStaticSwitchParameter, -400, y,
                  parameter_name="UseORM", default_value=False)
        link(orm, orm_out, sw, "True")
        link(flat, "", sw, "False")
        to_property(sw, "", prop)

    mel.recompile_material(mat)
    assets.save_loaded_asset(mat)
    return mat


def build_lens():
    path = MAT_DIR + "/M_Sophia_Lens"
    if assets.does_asset_exist(path):
        return assets.load_asset(path)
    mat = asset_tools.create_asset("M_Sophia_Lens", MAT_DIR, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", enum(unreal.BlendMode, "BLEND_TRANSLUCENT"))
    tint = expr(mat, unreal.MaterialExpressionVectorParameter, -500, -100,
                parameter_name="Tint", default_value=unreal.LinearColor(0.02, 0.02, 0.025, 1))
    opacity = expr(mat, unreal.MaterialExpressionScalarParameter, -500, 100,
                   parameter_name="Opacity", default_value=0.6)
    to_property(tint, "RGB", MP.MP_BASE_COLOR)
    to_property(opacity, "", MP.MP_OPACITY)
    mel.recompile_material(mat)
    assets.save_loaded_asset(mat)
    return mat


# (instance, base colour texture, ORM texture or None, extra)
INSTANCES = [
    ("MI_Sophia_Body", "T_Sophia_Body_Fishnet", None, {"Roughness": 0.5}),
    ("MI_Sophia_Shirt", "T_Sophia_Shirt", "T_Sophia_Shirt_ORM", {}),
    ("MI_Sophia_Skirt", "T_Sophia_Skirt", "T_Sophia_Skirt_ORM", {}),
    ("MI_Sophia_Jacket", "T_Sophia_Jacket", None, {}),
    ("MI_Sophia_Panty", "T_Sophia_Panty", "T_Sophia_Panty_ORM", {"masked": True}),
    ("MI_Sophia_Choker", "T_Sophia_Choker", "T_Sophia_Choker_ORM", {}),
    ("MI_Sophia_Gear", "T_Sophia_Gear", None, {}),
    ("MI_Sophia_Eyes", "T_Sophia_Eyes", None, {}),
    ("MI_Sophia_Teeth", "T_Sophia_Teeth", None, {}),
    ("MI_Sophia_UpperBikini", "T_Sophia_UpperBikini", None, {}),
    ("MI_Sophia_Katana", "T_Sophia_Katana", "T_Sophia_Katana_ORM", {}),
    ("MI_Sophia_Pistol", "T_Sophia_Pistol", "T_Sophia_Pistol_ORM", {}),
    ("MI_Sophia_Headphone", "T_Sophia_Headphone", None, {}),
    ("MI_Sophia_GlassFrame", None, None, {"Tint": unreal.LinearColor(0.03, 0.03, 0.03, 1)}),
]


def build_instances(base):
    # The factory's InitialParent is a bare UPROPERTY(), invisible to Python: the parent is set
    # below with set_material_instance_parent instead.
    factory = unreal.MaterialInstanceConstantFactoryNew()
    for name, color, orm, extra in INSTANCES:
        path = MAT_DIR + "/" + name
        mi = assets.load_asset(path) if assets.does_asset_exist(path) else \
            asset_tools.create_asset(name, MAT_DIR, unreal.MaterialInstanceConstant, factory)
        mel.set_material_instance_parent(mi, base)
        mel.set_material_instance_static_switch_parameter_value(mi, "UseBaseColorTexture", color is not None)
        if color:
            mel.set_material_instance_texture_parameter_value(mi, "BaseColor", tex(color))
        mel.set_material_instance_static_switch_parameter_value(mi, "UseORM", orm is not None)
        if orm:
            mel.set_material_instance_texture_parameter_value(mi, "ORM", tex(orm))
        if "Roughness" in extra:
            mel.set_material_instance_scalar_parameter_value(mi, "Roughness", extra["Roughness"])
        if "Tint" in extra:
            mel.set_material_instance_vector_parameter_value(mi, "Tint", extra["Tint"])
        overrides = mi.get_editor_property("base_property_overrides")
        overrides.set_editor_properties({
            "override_blend_mode": bool(extra.get("masked")),
            "blend_mode": enum(unreal.BlendMode, "BLEND_MASKED" if extra.get("masked") else "BLEND_OPAQUE")})
        mi.set_editor_property("base_property_overrides", overrides)
        mel.update_material_instance(mi)
        assets.save_loaded_asset(mi)


# FBX material slot name (prefix) -> material. The slot names were read from the FBX files.
SLOTS = [
    ("Sophia_Body_Fishnet", "MI_Sophia_Body"),
    ("Sophia_Shirt", "MI_Sophia_Shirt"),
    ("Sophia_Skirt", "MI_Sophia_Skirt"),
    ("Sophia_Jacket", "MI_Sophia_Jacket"),
    ("Sophia_Panty", "MI_Sophia_Panty"),
    ("Sophia_Choker", "MI_Sophia_Choker"),
    # Boots and belt: own slots (2026-10-27) so each can be hidden alone; same material as the rest.
    ("Sophia_Boots", "MI_Sophia_Gear"),
    ("Sophia_Belt", "MI_Sophia_Gear"),
    ("tripo_mat", "MI_Sophia_Gear"),
    ("Olhos", "MI_Sophia_Eyes"),
    ("Dentes", "MI_Sophia_Teeth"),
    ("Sophia_Upper_Bikini", "MI_Sophia_UpperBikini"),
    ("Sophia_Katana", "MI_Sophia_Katana"),
    ("Sophia_Pistol", "MI_Sophia_Pistol"),
    ("Sophia_Kitty_Headphone", "MI_Sophia_Headphone"),
    ("Sophia_Glass_Frame", "MI_Sophia_GlassFrame"),
    ("Sophia_Glass_Lens", "M_Sophia_Lens"),
]


def material_for(slot):
    for prefix, mat_name in SLOTS:
        if slot.lower().startswith(prefix.lower()):
            return assets.load_asset(MAT_DIR + "/" + mat_name)
    return None


def assign():
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    found = 0
    for data in registry.get_assets_by_path(ROOT, recursive=True):
        if str(data.package_path).startswith(MAT_DIR) or str(data.package_path).startswith(TEX_DIR):
            continue
        mesh = data.get_asset()
        if isinstance(mesh, unreal.SkeletalMesh):
            # Reading a struct out of an unreal.Array gives a copy: edit it, then put it back.
            slots = mesh.get_editor_property("materials")
            for i in range(len(slots)):
                slot = slots[i]
                name = str(slot.get_editor_property("material_slot_name"))
                mat = material_for(name)
                if mat:
                    slot.set_editor_property("material_interface", mat)
                    slots[i] = slot
                unreal.log("Sophia: %s [%s] -> %s" % (mesh.get_name(), name, mat.get_name() if mat else "UNMATCHED"))
            mesh.set_editor_property("materials", slots)
        elif isinstance(mesh, unreal.StaticMesh):
            for i, slot in enumerate(mesh.get_editor_property("static_materials")):
                name = str(slot.get_editor_property("material_slot_name"))
                mat = material_for(name)
                if mat:
                    mesh.set_material(i, mat)
                unreal.log("Sophia: %s [%s] -> %s" % (mesh.get_name(), name, mat.get_name() if mat else "UNMATCHED"))
        else:
            continue
        found += 1
        assets.save_loaded_asset(mesh)
    if not found:
        unreal.log_warning("Sophia: no meshes under %s yet. Import them, then run this again." % ROOT)


import_textures()
build_instances(build_base())
build_lens()
assign()
unreal.log("Sophia: done")
