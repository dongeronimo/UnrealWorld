# Sophia's jacket: Chaos Cloth in Unreal 5

The jacket's sleeves, shoulders and collar stay skinned to the bones. Only the front panels and
the hem are simulated. They hang from the skinned part instead of being dragged up when she
raises her arms.

## What is in Blender

`sophia_equipment_jaqueta_cloth.blend` is rig4 with the same weights plus the cloth mask:

- **Vertex group `Cloth_MaxDistance`** on the Jacket. It runs from 0 (follows the bones) to 1
  (free to hang).
- **Colour attribute `Cloth_Mask`**, the same values as grey. It goes into the FBX as vertex colour.

How the mask is built:

| area | value |
|---|---|
| sleeves and the 7 cm of jacket next to them | 0 |
| above the armpit line (z 1.16): shoulders, collar, upper chest | 0 |
| front panels, below z 1.02 | about 0.9 |
| back hem | about 0.2 |

Between those areas the value ramps smoothly. The preview render is
`sophia_saia/jaqueta_cloth_mascara.png` (white = free).

## 1. Export and import

1. Run `aplicar_escala.py`, then `exportar_unreal.py` as for the Ratoman.
   - The jacket goes into the same skeletal mesh as the body.
   - It keeps its own material, `Sophia_Jacket`, which gives it its own section in Unreal. The
     cloth setup works per section.
2. In the FBX import dialog, set **Mesh → Vertex Color Import Option: Replace**. Without it,
   the mask colours are dropped.

## 2. Physics asset: the colliders the cloth hits

Cloth only collides with the **physics asset of its own skeletal mesh**, and only with
**spheres and capsules**. Open Sophia's physics asset and check or add these:

- **Capsules:** Pelvis, Spine01, Spine02 (chest), both Clavicles, both Upperarms.
- **Two spheres on Spine02, one on each breast.** These matter most: the front panels hang
  over the chest, and without them the panels fall straight through her.
- Keep the shapes slightly inside the skin. A cloth collision thickness of about 1 cm adds the gap.

## 3. Create the cloth data

In the Skeletal Mesh editor:

1. In the LOD/Sections panel, right-click the **Sophia_Jacket** section and choose
   **Create Clothing Data from Section**.
   - Name it `Jaqueta_Cloth`.
   - Set Physics Asset to Sophia's.
2. Right-click the same section again and choose **Apply Clothing Data → Jaqueta_Cloth**.

## 4. Paint Max Distance

1. Click **Activate Cloth Paint** on the toolbar. In the Clothing window, select `Jaqueta_Cloth`.
   Under Masks, select **Max Distance**.
2. **Try importing the mask first.** Right-click the Max Distance mask and look for an option
   that takes values from the vertex colour.
   - I couldn't confirm this option exists in your Unreal version.
   - If it exists, use the **R** channel, then scale it so 1.0 becomes 5 (painted values are
     in cm).
3. **If there's no import, paint it by hand.** This takes a few minutes:
   - **Fill** tool, value **0**, applied to everything. The whole jacket now follows the bones.
   - **Gradient** tool on each front panel:
     - Start points: the vertices along the armpit line (value 0).
     - End points: the hem (value **5**).
   - **Brush**, value **1 to 1.5**, along the back hem.
   - **Smooth** tool once over the borders between areas.
   - Use the Blender render as the map of where each value goes.

Value guide, in cm:

| part | Max Distance |
|---|---|
| sleeves, shoulders, collar | 0 |
| front panel hem | 4–6 |
| back hem | 1–1.5 |

If the panels swing too much, lower the numbers. Don't add more colliders for that.

**Don't paint Backstop.** The jacket's normals point in inconsistent directions (we found that
in Blender), and a backstop pushes along the normal. Some areas would be pushed into the body
instead of out.

## 5. Cloth config

In the Clothing window, open the **Config** for `Jaqueta_Cloth`. These are starting values for
stiff leather:

| setting | value |
|---|---|
| Mass mode | Density, about 0.6 kg/m² (leather is heavier than the 0.35 default) |
| Edge stiffness | 1.0 |
| Bending stiffness | 0.8–1.0 (leather doesn't crumple like cotton) |
| Damping | 0.15–0.25 (stops the panels flapping) |
| Collision thickness | 1.0 cm |
| Friction | 0.3–0.5 (helps the panels rest on the chest) |
| Self collision | off (expensive, and the hanging area is small) |
| Gravity | default |

## 6. Test

1. Set the preview to the dance clip and scrub to frame 561.
2. Then try the gun clip at frame 31. The front panels should stay down and rest on the breast
   spheres when the arm goes up.

| what you see | fix |
|---|---|
| A panel sinks into the body | Enlarge or move the Spine02 spheres, or raise collision thickness |
| The border between pinned and free cloth stretches | That border is too sharp. Smooth the mask over more rows |
| It jitters at the start of a clip, or after a cut | On the Skeletal Mesh Component in the Blueprint, check the **Teleport Distance / Rotation Threshold** |

## What this doesn't fix

- **Skin showing at the right shoulder blade in the gun pose.** That area is pinned (value 0),
  so it is still a weights and fit problem.
- **The sleeves.** They stay exactly as rig4.

---

# Shirt, skirt and boots (2026-10-15)

File: **`sophia_equipment_roupa_longa_cloth3.blend`** (the jacket file plus these three pieces; the skirt is 7 cm longer than in `sophia_equipment_roupa_cloth.blend`, which is superseded, as is `sophia_equipment_roupa_longa_cloth.blend`). The thigh strap (two loose pieces of the Skirt mesh) is not stretched with the skirt. It is slid 11.8 cm down the right thigh so it sits under the new hem, keeps its distance to the skin, and is weighted 100% to `R_ThighTwist01/02` and pinned (mask 0). The extra length is a vertical stretch of the part below z 0.88, with the lower band widened up to 19% to clear the thighs. All three
are skinned with at most 4 bones each.

| piece | how it moves | Chaos Cloth |
|---|---|---|
| Shirt | weights from the nearest skin point, smoothed | **no**: it is tight and sits under the jacket |
| Skirt | skin weights plus the body's 26 `CORR_*` morph targets (same names); the front hem blends toward hip→thigh weights | **optional**: own material `Sophia_Skirt`, mask `Cloth_Mask` / `Cloth_MaxDistance` |
| Boots | unchanged from the earlier session (calf twist, foot, toe; sole stiff) | no |

**The skirt's morph targets.** The skirt has the same `CORR_*` names as the body, so the curves you
build for the body drive the skirt too. Without them, the buttocks come through the back of the
skirt in squats and knee lifts.

**Why the shirt is not cloth.** Chaos Cloth collides only with the physics asset's spheres and
capsules, never with another mesh. That has two consequences:
- A simulated shirt would fall through the jacket.
- The jacket's front panels don't see the shirt either, so the **breast spheres must enclose the
  shirt, not the skin**. The shirt sits 9 mm off the skin (median) and up to 3 cm off it at the
  front.

**If you simulate the skirt hem:**
- Make clothing data from the `Sophia_Skirt` section, as for the jacket.
- Max Distance: 0 above the buttocks, rising to **2–3 cm** at the hem. The mask is 0 above z 0.78
  and 1 at the hem (z 0.62).
- Colliders: capsules on both thighs (ThighTwist01) and on the Pelvis.
- Leather or latex: bending stiffness high, damping 0.2.
- I couldn't confirm whether Chaos Cloth includes morph targets in the position it simulates from.
  If the hem jumps when the `CORR_*` keys are active, lower the Max Distance.

Measured over three clips. "Skin through" counts the garment vertices that end up more than 3 mm
inside the skin.

| | skin through (worst frame) | skirt edge stretch, max |
|---|---|---|
| skirt, hip→thigh weights only | 346 / 2027 | 2.8× |
| skirt, final | 105 / 2027 (aerobic 101) | 26× (front hem between the legs, high knee) |
| shirt | 22 / 1757 (5 already at rest) | 12× |

The 26× stretch is the front hem stretching between the legs on a knee lift. Cloth on the hem
smooths it.

## Shirt and skirt textures (2026-10-15)

File: **`sophia_equipment_roupa_textura.blend`** (`roupa_longa_cloth3` with the new textures; it
supersedes cloth3 for export).

Tripo's atlas mapped both pieces onto the wrong regions (skin, fishnet, the headphones), which gave
the white and pink blots. Each piece now has its own UV and its own textures, as the jacket does:

| piece | UV | textures | material |
|---|---|---|---|
| Shirt | `UV_Shirt` | `Sophia_Shirt.png`, `Sophia_Shirt_ORM.png` (2048) | `Sophia_Shirt`: black linen weave, roughness 0.88, silver zipper down the front |
| Skirt | `UV_Skirt` | `Sophia_Skirt.png`, `Sophia_Skirt_ORM.png` (2048) | `Sophia_Skirt`: black latex, roughness 0.14; buckle, waist rings and snap are silver metal |

**ORM** uses Unreal's packing: R = occlusion (always 1), G = roughness, B = metallic.

In Unreal:
- Import the `_ORM` textures with **sRGB off** (compression: Masks).
- Wire G → Roughness and B → Metallic.

The shirt now has its own material, so it gets its own section too. It is not cloth.

## Katana and the stray body vertex (2026-10-15)

File: **`sophia_equipment_roupa_textura2.blend`** (supersedes `roupa_textura`).

**Body vertex 12783** (perineum) had no bone weights, left over from the hand edit, so it stayed in
rest and made a spike. It now has the mean weights of its three neighbours: Pelvis 0.16, both
ThighTwist01. In every shape key its offset is now the mean of theirs.

**Katana** has its own material, `Sophia_Katana`, with the same UVs.
- Textures: `Sophia_Katana.png` and `Sophia_Katana_ORM.png`, 2048.
- The hand that Tripo painted over the handle next to the guard is replaced by repeats of the clean
  wrap.
- ORM (same packing as the shirt and skirt):

| part | metallic | roughness |
|---|---|---|
| blade | 1 | 0.16, brighter steel base colour |
| collar | 1 | 0.3 |
| guard and pommel cap | 1 | 0.45 |
| wrap | 0 | 0.75 |

The shared Tripo texture is unchanged for the belt, boots, holster, pistol and scabbard.

## Choker (2026-10-15)

File: **`sophia_equipment_final2.blend`** (`roupa_textura2` plus the choker; supersedes it and
`sophia_equipment_final.blend`, whose choker had Head weights and a teardrop shape).

**Fit.** The choker came unrigged and at jaw height (z 1.36–1.41), inside the face and hair.
- Moved 7.5 cm down onto mid-neck and slid 8 mm back.
- Scaled as a whole: width x1.16, depth x1.36. These are the smallest scales that keep every band
  vertex at least 2 mm outside the neck skin. The check casts a ray from the neck's axis.
- Then pulled in toward the skin per 10° sector by its gap, smoothed over ±40°. Inner and outer
  faces move together, so the band keeps its thickness.
- Its own tilt is kept: lower at the throat, higher at the nape. It was already within 2° of square
  to the neck.
- Gap to the skin: 1.1 mm minimum, 8 mm median.

**Rig.** Parented to the armature.
- Band: NeckTwist02 and NeckTwist01 only, by height (at least half on NeckTwist02). It is the same
  all round, so the band moves as one ring. There is **no Head and no Spine02 weight**: the Head
  pulled the band into the chin when she looked down.
- Link and ring: rigid, with the band's weight.

**Texture.** Material `Sophia_Choker`, own UV `UV_Choker`, textures `Sophia_Choker.png` and
`Sophia_Choker_ORM.png` (512).

| part | colour | metallic | roughness |
|---|---|---|---|
| band | black | 0 | 0.55 |
| link and ring | gold | 1 | 0.22 |

## Pistol (2026-10-15)

File: **`sophia_equipment_final3.blend`** (`final2` plus the pistol; supersedes it).

Tripo's atlas had the hand that held the pistol painted onto it in pink. The pistol now has its own
UV `UV_Pistol`, material `Sophia_Pistol`, and textures `Sophia_Pistol.png` and
`Sophia_Pistol_ORM.png` (2048).

| part | look | metallic | roughness |
|---|---|---|---|
| steel | brushed: fine streaks along the slide | 1 | about 0.38, streaked |
| grip panels (the grip's two sides, between hammer and butt) | aged ivory: warm cream, faint Schreger cross-hatching | 0 | 0.3 |

The back strap, front strap, butt, screws and small parts stay steel.

## Panty, prop bones, fishnets, hair (2026-10-15)

File: **`sophia_equipment_final5.blend`** (supersedes final3 and final4).

**Panty (easter egg).** `Lower_Bikini` keeps its mesh, UVs, weights and 27 keys; only the material
changed.
- Material `Sophia_Panty`; textures `Sophia_Panty.png` (RGBA) and `Sophia_Panty_ORM.png`, 2048.
- Salmon satin, lace bands on the waist and leg openings (net, flowers, scallops), a satin bow,
  and a solid gusset.
- In Unreal set the material to **Masked**, with alpha → Opacity Mask. The lace holes are also
  painted darker salmon, so it still works opaque.

**Holster and scabbard bones.** `CC_Extra_Holster` (20 cm) and `CC_Extra_Scabbard` (86 cm) are
children of `CC_Base_Pelvis`. Each runs from where the piece hangs off the belt to its tip, and
each piece is weighted 100% to its bone. Without physics they follow the hips exactly as before.

In the physics asset:
- one capsule per bone, on a constraint to the Pelvis;
- swing limited to about 25° for the holster and 20° for the scabbard; twist locked;
- they collide with the thigh capsules and the Pelvis/buttock bodies.

**Fishnets.** `Sophia_Body_Fishnet.png` is a copy of `Sophia_vag.png` with fishnet tights painted
on. Material `Sophia_Body_Fishnet` is a copy of the body material with it. It is kept with a fake
user and **not assigned**; swap it onto the body section to put the tights on.
- The grid is laid out around each leg's axis and closes around the leg without a seam. The only
  seam is the centre line.
- Diamonds are 1.8 cm, threads 1.3 mm, with a dark waistband in the top 2.2 cm (hidden under the
  panty and skirt).

**Hair.** Three chains, all children of `CC_Base_Head`:

| chain | bones | runs |
|---|---|---|
| `CC_Extra_HairBack` | root + 5 | down her back to z 1.01 |
| `CC_Extra_HairL` | root + 3 | the big lock over her left shoulder and chest |
| `CC_Extra_HairR` | root + 3 | the small lock on her right |

- The hair stays inside `Body_Rigged`, so the body's shape keys are unaffected.
- Weights follow `tools/blender/cabelo.py`: near the skull → the root (rigid with the head);
  loose → the chain bone at that height; at most 4 bones per vertex.
- Without physics the chains are rigid with the head, so the back hair can go through her shoulders
  when she turns or bows her head.
- In Unreal, simulate the chain bones, not the roots: AnimDynamics or a physics-asset chain, with
  colliders on Spine02, both clavicles and the breast spheres the jacket already needs.

---

# Body masks: hide the skin under each piece (2026-10-16)

File: **`sophia_masks.blend`** (`final5_fishnet` plus the masks; it supersedes it for export).
The mask files are in **`sophia_masks/`** next to it. These masks stop the skin from poking
through the clothes. They use the same method as Shahzadah's in Unity: an address UV plus a lookup
texture, and the vertex shader drops every triangle that touches a hidden vertex.

| slot | piece | channel in `masks_rgba.png` | hidden vertices |
|---|---|---|---|
| arms | Jacket | R | 697 |
| chest | Shirt | G | 196 |
| hips | Skirt | B | 1602 |
| legs | Boots | A | 1668 |

Choices that differ from Shahzadah, set in `tools/blender/outfits/sophia.json` (`mask_options`):
- **hips is `torso_only`.** It hides the waist, pelvis and buttocks, but never thigh skin. The skirt
  is open at the hem, so in a squat the inner thighs are seen from below.
- **chest erodes 3 rings, not 1.** The shirt slides over the skin when she moves. With one ring,
  the neckline uncovered a hole in the cleavage in the squat.
- **The jacket only hides arm skin.** It also covers part of the back, but that skin stays (the
  shirt covers most of it).
- **The panty is not a slot.** The hips mask hides the crotch. Taking the panty off while the
  skirt is worn shows a hole there.

## In Blender

- **Preview.** Select `Body_Rigged` and open the Modifier panel. On **MASK PREVIEW - evaluate
  triangle masks**, turn **Wear arms / chest / hips / legs** on or off. The faces are deleted for
  real, so this works in Solid mode too. When you hide a piece with the eye icon, also turn off its
  Wear. The materials are untouched, so their names reach Unreal unchanged.
- **Edit.** In Edit Mode, select body vertices, right-click, and use the **Gambis** section: Hide /
  Restore selected in a mask, or Select hidden in a mask. The preview updates as you edit.
- **Export.** Gambis > **Export masks...** rewrites `sophia_masks/` (one PNG per slot and
  `masks_rgba.png`). Then save the `.blend`, because the decisions live in the mesh.
- Gambis is inside the file (Text Editor: `gambis_masks.py`, Register on). It loads when the file
  is opened with scripts trusted. If the menu is missing, open that text and click Run Script.
  Your installed Gambis add-on is the same version and takes precedence when it is enabled.
- **Do not remesh, reorder or add vertices on the body.** The masks address vertex i at texel i.
  Gambis refuses to export if that no longer holds. Regenerate instead:
  `blender -b sophia_equipment_final5_fishnet.blend -P D:/gurps/tools/blender/generate_outfit_masks.py -- sophia_masks.blend sophia_masks D:/gurps/tools/blender/outfits/sophia.json`
  (the output must not exist yet).

## In Unreal

1. **Export** with `exportar_unreal.py` as before, with modifiers off. The body's second UV channel,
   `MaskLookup`, arrives as **UV channel 1**. Do not let anything overwrite it.
2. **Import `masks_rgba.png`** with these texture settings. Each one matters: a wrong setting blends
   neighbouring vertices' decisions.
   - Compression: **VectorDisplacementmap (RGBA8)**, which is uncompressed.
   - **sRGB off**.
   - Filter: **Nearest**.
   - Mip Gen Settings: **NoMipmaps**.
   - **Never Stream** on.
3. **Body material**: keep it **Opaque**, with *Used with Skeletal Mesh* checked. Add:
   - Texture Object parameter `BodyMasks` (`masks_rgba`)
   - TextureCoordinate, index **1**
   - Vector parameter `Wear`, default (1,1,1,1). Its order is arms, chest, hips, legs, and 1 means
     the piece is worn. Feed it through **AppendVector(RGB, A)** to get a float4.
   - A **Custom** node, output type Float 3, with inputs `Tex`, `UV` and `Wear`, wired to **World
     Position Offset**:
     ```hlsl
     float4 m = Tex.SampleLevel(TexSampler, UV, 0);
     // 1 for every worn slot that hides this vertex
     float hidden = dot(step(m, 0.5), Wear);
     return hidden > 0.5 ? asfloat(0x7fc00000).xxx : float3(0, 0, 0);
     ```
     WPO runs per vertex, so this is the same NaN trick as Unity. A triangle with a NaN vertex is
     not drawn, and that includes the shadow pass, which runs the same WPO.
4. **Settings that would silently switch the masks off:**
   - Material *Max World Position Offset Displacement*: 0.
   - Component *World Position Offset Disable Distance*: 0.
   - Component *Evaluate World Position Offset*: on.
5. **Equipping from Blueprint:** on the body's material slot, call **Create Dynamic Material
   Instance**. Then **Set Vector Parameter Value** `Wear` whenever a piece goes on or off.

**Tests (on the phone first):**
- Equip and unequip each piece; check both the body and its shadow.
- Scrub the dance clip and the gun clip.
- Look at her from far away.

Expect FXAA/MSAA and cascaded shadows. Lumen, virtual shadow maps and TSR are not part of the
mobile renderer.

**If the desktop fallback ever turns TSR, virtual shadow maps or Lumen back on**, test again: a
NaN in the velocity or shadow-cache passes can smear. The fallback uses the same data with no
Blender changes:
- Compute `hidden` in a **Vertex Interpolator**.
- Set the material to **Masked**, with Opacity Mask = `hidden > 0.5 ? 0 : 1`.
- Remove the WPO.

---

# New clips, jacket re-weight, fishnet (2026-10-16)

**Export from `sophia_fishnet_pernas.blend`.** It contains everything below and supersedes
`sophia_masks.blend`, `sophia_clips.blend` and `sophia_jacket_repeso.blend`.

## Clips

The clips are `dual_gun_muzdn_end_pose`, plus `hold_gun_fastrun_forward` start, loop and end. They
were brought in with `tools/blender/retarget_movimento.py`, with a world rotation error of 0.000°.

These AccuRig exports put the bind T-pose at frame 1; the real motion starts at frame 2. The
script now removes that frame. Without the fix, the run loop would pop once per cycle.

- The run clips chain without a jump: start → loop → end.
- They run in place: the travel comes from the game.
- The loop's last frame is 4.8° from its first. Normal steps are 12–29°, so Unreal's wrap is
  smooth.
- The older dance clip (`dance-graceful`) still has its T-pose at frame 1.

## Jacket

The torso is re-weighted from the body with `tools/blender/pesos_do_tronco.py`. The sleeves keep
their hand weights.

Measured over all six clips with `diag_camadas.py` (worst frame per clip):

| measure | before | after |
|---|---|---|
| shirt through jacket | 15–26 | 7–18 |
| jacket ballooning >3 cm | 75–183 | 45–143 |

What remains:
- **The open front panel crosses the jacket's own sleeve.** In Unreal, make the **Upperarm
  capsules (and the forearm ones, if the panel reaches) as thick as the sleeve, not the arm**, so
  the simulated panel stays outside the sleeve. It is the same idea as the breast spheres that
  enclose the shirt.
- **Don't use self-collision.** The sleeves are not cloth (max distance 0), and self-collision is
  the most expensive part of Chaos.
- **If Chaos is too heavy on the phone,** use Kawaii Physics instead. Give each panel a bone chain
  (`rig_saias.py`, chain mode) and use the same thick capsules.
- **Her hair goes through the jacket.** That is a separate problem: the hair is inside
  `Body_Rigged`.

## Fishnet

The new texture is `Sophia_Body_Fishnet_pernas.png`. Assign it in Unreal in place of
`Sophia_Body_Fishnet.png`. The old texture had the net on the belly, the vulva and the hands.

The net now:
- **Ends at a stocking top** 5 cm below the hip joint, measured along the thigh, with a 2 cm dark
  band in the threads' colour.
- **Covers leg skin**, plus skin more than 6 cm from the midline in front and 2 cm behind. The
  buttocks are included; the vulva, perineum and cleft are not.
- **Never covers arm skin.**

It is rebuilt from the clean skin `Sophia_vag.png` by `tools/fishnet_pernas_uv.py` (in Blender)
and then `tools/fishnet_pernas_compor.py` (system Python). The cut, band and midline widths are
arguments.

## Shirt mask: the jacket hides the shirt (2026-10-16)

**Export from `sophia_camisa_masks.blend`.** It is `sophia_fishnet_pernas.blend` plus this mask,
and it supersedes it. The mask files are in `sophia_shirt_masks/`; the config is
`tools/blender/outfits/sophia_shirt.json`.

- **What it hides.** 330 of the shirt's 1,757 vertices: its upper back and shoulders, under the
  jacket. The front panel and the strip below the jacket's hem stay.
- **What doesn't count as cover.** The jacket's swinging front panels (`Cloth_MaxDistance` > 0.3,
  about 0.9 on them) are left out. Hiding the shirt under them would open a hole each time a panel
  swings. The back hem (about 0.2, so 1–1.5 cm in Unreal) still covers.
- **Result.** Shirt through jacket, worst frame per clip over all six clips: **2–7**. It was 15–26
  originally and 7–18 after the jacket re-weight.
- **The shirt has its own address UV.** `MaskLookup` is the shirt's **UV channel 1**. Its 64×64
  lookup is sized by the shirt's own vertex count and is unrelated to the body's 128×128.
- **Editing.** Select `Shirt` and use Gambis. Its slot is called **arms** because the jacket is the
  arms piece. Export masks writes to `sophia_shirt_masks/` (stored on the mesh), so it never
  overwrites the body's masks. To preview, use **Wear arms** on the shirt's MASK PREVIEW modifier.

**In Unreal:**
- Import `sophia_shirt_masks/masks_rgba.png` with the same settings as the body's (uncompressed
  RGBA8, sRGB off, Nearest, no mips, Never Stream).
- On the `Sophia_Shirt` material, wire the same Custom node to World Position Offset:
  - `Tex` = the shirt's texture
  - `UV` = TexCoord **1**
  - `Wear` = the body's `Wear` vector. Only R (arms = the jacket) matters, because G, B and A are
    all 1 in this texture.
- Settings: Opaque, *Used with Skeletal Mesh* checked, WPO Disable Distance 0.
- **Equipping:** when the jacket goes on or off, set `Wear` on both the body and the shirt
  material instances.
