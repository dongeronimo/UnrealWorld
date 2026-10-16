# Sophia in Unreal

A step-by-step plan for taking Sophia from Blender to a playable character in Unreal: what to
export, how to import it, what to rebuild by hand (the masks, correctives, cloth and physics),
and where every file is.

Written 2026-10-16 for **UE 5.7**. It assumes the [Ratoman guide](Ratoman_Brute_Unreal.md) and
does not repeat it: import through Interchange, the IK Rig, the twist Control Rig and the Pose
Asset all work the same way for her. Her skeleton is the same AccuRig `CC_Base_*` rig. Where I am
not sure of an exact 5.7 menu name, the text says what the thing *does*. **None of these steps
has been run in an editor.**

Her animation is the subject of a separate plan, [`Sophia_Animation_Plan.md`](Sophia_Animation_Plan.md).

---

## 0. Where everything is

All paths are in `D:\UnrealWorld\Art\` unless noted.

| what | where |
|---|---|
| **The file to export** | **`sophia_idle.blend`** (2026-10-16: `sophia_camisa_masks.blend` + weapons holstered + idle clips). Every other `sophia_*.blend` is an intermediate step |
| Body mask textures | `sophia_masks\masks_rgba.png`: R arms (jacket), G chest (shirt), B hips (skirt), A legs (boots). 128×128 |
| Shirt mask texture | `sophia_shirt_masks\masks_rgba.png`: R = the jacket hides the shirt. 64×64 |
| Notes on cloth, masks, materials and props | `sophia_jaqueta_chaos_cloth.md`. It records every decision, with the measurements behind it |
| Correctives and thigh twist | `Sophia_corretivos_UNREAL.md` plus `Sophia_corretivos_referencia.csv` (the reference values to check against) |
| Her art tools | `tools\` here (fishnet), and `D:\gurps\tools\blender\` (everything else, including `exportar_unreal.py` and `aplicar_escala.py`) |
| Textures | `Sophia_*.png` and `Sophia_*_ORM.png` here. The Tripo atlas (belt, boots, holster, scabbard) is packed inside the blend; the exporter writes it out as a PNG |

### What is in the file

- **Armature** `Armature`: 117 bones.
  - The `CC_Base_*` body bones.
  - `CC_Extra_Holster` and `CC_Extra_Scabbard`, children of the Pelvis.
  - Three hair chains, children of the Head: `CC_Extra_HairBack` (root + 5), `HairL` (root + 3),
    `HairR` (root + 3).
- **The object scale is 0.01.** AccuRig works in centimetres. See step 1.
- **Skinned meshes:**

| mesh | material | notes |
|---|---|---|
| `Body_Rigged` | `Sophia_Body_Fishnet` (texture `Sophia_Body_Fishnet_pernas.png`; swap in `Sophia_vag.png` for bare legs) | 52 shape keys: 26 `CORR_*`, 22 ARKit-named expressions, `V_None`, plus the Basis |
| `Shirt` | `Sophia_Shirt` | own UV and textures, plus the mask UV on channel 1 |
| `Skirt` | `Sophia_Skirt` | 26 `CORR_*` keys, the same names as the body's; optional cloth (`Cloth_Mask`) |
| `Jacket` | `Sophia_Jacket` | cloth mask: colour attribute `Cloth_Mask` and group `Cloth_MaxDistance` |
| `Lower_Bikini` | `Sophia_Panty` | 26 `CORR_*` keys; Masked material |
| `Upper_Bikini` | `Sophia_Upper_Bikini` | an alternative top. Keep it hidden in game |
| `Choker` | `Sophia_Choker` | |
| `Boots`, `Belt`, `Holster`, `Katana_Sheat` | the Tripo atlas | |
| `Olhos`, `Dentes` | `Olhos`, `Dentes` | eyes and teeth |

- **Rigid props parented to bones:**

| prop | bone |
|---|---|
| `Glass_Rayban` | `CC_Base_Head` |
| `Kitty_Headphone` | `CC_Base_Head` |
| `Pistol` | `CC_Extra_Holster` (in the holster; preview only, see §1 Weapons) |
| `Katana` | `CC_Extra_Scabbard` (in the scabbard; preview only) |
- **Clips:**
  - `aerobic-dance`, `c08_low_hold_gun_turn180_l`, `dance-graceful`
  - `dual_gun_muzdn_end_pose` and `hold_gun_fastrun_forward` start, loop and end
  - Idles from `pose_idle.py` (in `sophia_idle.blend` only), one run builds all four:
    - `idle_hand_on_hip` and `idle_look_nails`: 240-frame loops (8 s) plus a closing key equal to
      the first.
    - `idle_hand_on_hip_to_look_nails` and `idle_look_nails_to_hand_on_hip`: 40 frames (1.3 s).
      Each starts exactly on frame 1 of its source idle and ends exactly on frame 1 of its
      target, so a state machine that enters the target at its start gets no pop. Play the
      transition from the source's start, or give it a short blend.
    - Rebuild:
      `blender -b sophia_armas.blend -P D:\gurps\tools\blender\pose_idle.py -- sophia_idle.blend poses/sophia_idle.json poses/sophia_idle2.json poses/sophia_idle1_2.json poses/sophia_idle2_1.json`
      (json paths under `D:\gurps\tools\blender\`).
  - The exporter skips `0_T-Pose`. `dance-graceful` still has AccuRig's T-pose on frame 1;
    trim it in Unreal or ignore it.

---

## 1. Export from Blender

```
blender -b sophia_idle.blend -P D:\gurps\tools\blender\aplicar_escala.py -- sophia_export.blend
blender -b sophia_export.blend -P D:\gurps\tools\blender\exportar_unreal.py -- D:\UnrealWorld\Art\sophia_unreal Sophia
```

- **`aplicar_escala.py` first.** It removes the armature's 0.01 scale and scales every action's
  location curves along with it (Ctrl+A does not do that). It refuses to save if any vertex moves
  more than 0.1 mm. **It has not been run on Sophia yet**: check its proof output. The masks
  survive it, because scaling does not reorder vertices.
- **`exportar_unreal.py`** writes:
  - one FBX of the character with no animation;
  - one FBX per clip, armature only;
  - the packed Tripo atlas as a PNG.

  Its settings each fix a known stumble: no leaf bones, metres with scale-1 nodes, face smoothing,
  modifiers **off**. With modifiers on, the MASK PREVIEW modifiers would delete faces and the
  shape keys would be lost. It re-reads every FBX and checks the bones.
- **Props:** I recommend taking the pistol, glasses, headphones and katana **out** of the character
  FBX. Make each one a static mesh on a socket. In game the pistol and katana change hands, get
  holstered and sheathed, and the glasses come off. If you keep the glasses and headphones in the
  FBX, enable the import option that keeps meshes in the bone hierarchy; they then arrive rigidly
  bound to their bone.
- **Weapons (user decision, 2026-10-16): never children of the hand.** They are static meshes
  attached by code, and the draw/holster notifies swap the socket. `armas_guardadas.py` puts the
  pistol in the holster and the katana in the scabbard. The fit is measured from the geometry:
  the katana's centreline matches the scabbard's to 4.2 mm on average, with the tip 4.9 cm short
  of the bottom. The pistol goes muzzle down along the holster axis, with the grip to the rear.
  It writes `sophia_soquetes.json`: each weapon's transform in its bone's space (metres,
  quaternion wxyz, Blender bone axes).
  - Sockets: `CC_Extra_Holster` (pistol) and `CC_Extra_Scabbard` (katana). The holster and the
    scabbard are skinned 100% to those bones, so the socket follows them exactly.
  - Hand sockets: none yet. The `Pistol` in the old file floated 0.5 m above the hand in the rest
    pose, so it was not a grip. The hand socket comes from the first clip with the pistol in
    hand, or set it by eye in the socket preview.
  - Unreal's bone axes can differ from Blender's after the FBX conversion. Treat the JSON as the
    starting value, and check it with the weapon as the socket's preview mesh.

---

## 2. Import

As in Ratoman §1, with these additions:

- **Morph targets on.** She has the 26 correctives and 22 expressions; the skirt and panty carry
  the same `CORR_*` names.
- **Vertex colour: Replace.** Without it the jacket's and skirt's `Cloth_Mask` colours are dropped.
- **Normals: import them.** Her meshes have custom normals.
- **Bone influences: 8.** 1,613 body vertices use more than 4 (`Sophia_corretivos_UNREAL.md`).
  - Check the per-platform skinning limit for mobile. If the phone caps at 4, run
    `limitar_influencias.py` in Blender rather than letting Unreal cut silently. On Illitran it
    measured 2.05 mm of displacement at worst.
  - The correctives were solved against these exact weights, so cutting influences slightly
    changes how they land.
- **UV channels:** the body and the shirt each have their mask address on **UV 1**. Don't let
  anything generate lightmap UVs into channel 1; skeletal meshes normally don't.

### Textures

| texture | sRGB | compression |
|---|---|---|
| `*_ORM.png` (R occlusion, G roughness, B metallic) | **off** | Masks |
| `masks_rgba.png` (body and shirt) | **off** | **VectorDisplacementmap (RGBA8)**: uncompressed. Filter **Nearest**, **NoMipmaps**, **Never Stream** |
| everything else | on | default |

### Materials (one section each)

- **Body.**
  - Opaque, *Used with Skeletal Mesh* checked.
  - The mask Custom node on WPO (step 4).
- **Shirt.** The same mask node, with its own texture.
- **Panty.** Masked, with the texture's alpha → Opacity Mask.
- **Glass lens.** Translucent.
- **Everything with an ORM texture.** G → Roughness, B → Metallic.

---

## 3. Check it before anything else

As in Ratoman §2: bone count, scale, rest pose. Then three checks of her own:

- **Each morph target alone at 1.0.** `CORR_L_Quadril_f090_a00` should change only the left hip;
  `eyeBlink_L` should close only the left eye.
- **Vertex colours.** In the skeletal mesh editor's vertex colour view, the jacket's front panels
  should be bright and its sleeves black.
- **UV 1.** It should show a regular grid of single points: one texel per vertex. If it looks like
  a normal unwrap, the import swapped UV channels.

---

## 4. Body and shirt masks

The full recipe, with the HLSL, is in `sophia_jaqueta_chaos_cloth.md`, under "Body masks" and
"Shirt mask".

In short:
- A **Custom** node on **World Position Offset** reads the mask texture with
  `SampleLevel(…, UV1, 0)`. It returns a NaN offset for a hidden vertex whose slot is worn, which
  drops every triangle touching it, in every pass including the shadows. It is the same trick as
  Unity's.
- **`Wear`** is a float4 vector parameter: arms, chest, hips, legs. Set it on **both** the body
  and the shirt material instances whenever a piece goes on or off.
- Keep **WPO Disable Distance** at 0, and **Max WPO Displacement** at 0, or the masks switch off
  quietly.
- Mobile has no TSR, virtual shadow maps or Lumen. If a desktop build turns them on, run the NaN
  test again; the Masked fallback is described in the notes.

---

## 5. Correctives and thigh twist

Follow `Sophia_corretivos_UNREAL.md`. Drivers don't survive FBX: the 26 corrective weights and the
4 thigh-twist fractions must be rebuilt in Unreal, as an AnimBP or Control Rig evaluating the same
rule table. Check the result against `Sophia_corretivos_referencia.csv`.

**Without this step her hips collapse in every crouch.** It matters more than anything else here.

---

## 6. Expressions

Use the Pose Asset, as in Ratoman §8. The 22 keys use ARKit names (`eyeBlink_L`,
`mouthSmile_R`, …), so Live Link Face could drive them directly later.

---

## 7. Physics asset

| body | shape | why |
|---|---|---|
| Pelvis, Spine01, Spine02 | capsules | cloth and hair collisions |
| Both clavicles | capsules | |
| **Both upper arms** | capsules **as thick as the jacket sleeve**, not the arm | the jacket's front panel stays outside the sleeve. A capsule that fits the skin lets it into the sleeve |
| Forearms | capsules at sleeve thickness, if a panel reaches them | |
| **Two spheres on Spine02** | one per breast, enclosing the **shirt**, not the skin | the jacket's front panels rest on them |
| Thighs (ThighTwist01) | capsules | skirt hem, holster, scabbard |
| `CC_Extra_Holster` | capsule; constraint to the Pelvis; swing about 25°, twist locked | |
| `CC_Extra_Scabbard` | capsule; same constraint, swing about 20° | |
| Hair chains | simulate the chain bones, not the roots | AnimDynamics or a physics chain, colliding with Spine02, the clavicles and the breast spheres |

---

## 8. Cloth

- **Jacket.** Chaos Cloth on its front panels and hem only, using the `Cloth_MaxDistance` mask.
  The full recipe and starting values are in the notes.
  - **Self-collision off.** The sleeves aren't cloth, and self-collision is the most expensive
    part of Chaos.
  - The panel-against-sleeve problem is solved by the thick arm capsules (§7).
- **Skirt hem.** Optional, with the same recipe and `Cloth_Mask`.
- **If Chaos is too heavy on the phone:** use **Kawaii Physics** instead. It needs bone chains in
  the panels; `rig_saias.py` has a chain mode. Use the same thick capsules as limits.

---

## 9. Animation

- **The IK Rig for her skeleton** is built as in Ratoman §3.
- **Retargeting from the UE5 Manny/Quinn skeleton** lets her use Epic's free animation sets:
  - The **Game Animation Sample** (locomotion: starts, stops, pivots, turns).
  - **Lyra** (pistol and rifle sets).

  Both come under Epic's licence for use in Unreal projects. That covers her locomotion; the
  commissar set in the animation plan only needs to provide what is unique to her.
- **Animation Blueprint** (detail in the animation plan):
  - locomotion;
  - an upper-body override from `spine_01` with her ready pose;
  - an aim offset;
  - an additive recoil;
  - montages for melee, reload, draw/holster and sheathe;
  - the corrective and twist evaluation (§5) last.

---

## 10. The order that works

1. Export (§1). Read the proof outputs.
2. Import (§2), then check it (§3).
3. Correctives and twist (§5). Compare with the CSV.
4. Masks (§4). Equip and unequip each piece and look at body and shadow.
5. Physics asset (§7), then cloth (§8).
6. Expressions (§6).
7. Retargeting and the AnimBP (§9).

---

## 11. Known limits

- **Her hair goes through the jacket.** The hair is part of `Body_Rigged`, and nothing in
  Blender fixes it. The hair-chain physics with the Spine02 and clavicle colliders is the first
  thing to try.
- **The jacket's front panel crosses its own sleeve** in some poses. That is left to cloth plus
  the thick capsules.
- **The inner-thigh skin marks in deep squats** are deformation, not the masks. The `CORR_*` keys
  reduce them; they are visible with all masks off too.
- **The katana has no hand socket yet.** It waits for sheathe/unsheathe clips (animation plan);
  the scabbard socket is in `sophia_soquetes.json`.
- **The retargeted clips key the face bones** (`CC_Base_FacialBone`, `JawRoot`, `UpperJaw`,
  the eyes). Expressions belong to the blendshapes and the expression controller, so strip those
  tracks on import, or run the controller after the clips in the AnimBP. The idles and their
  transitions do not key them.
- **The hips mask hides the crotch.** Taking the panty off while the skirt is on shows a hole.
