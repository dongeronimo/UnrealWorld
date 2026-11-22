# Fearing (Space Amazon) in Unreal

A step-by-step guide to bring Fearing up to date in Unreal and start working with her: import,
Control Rig, katana, and what comes after. Written 2026-11-03 for **UE 5.7**, in the same shape as
[`Sophia_Unreal.md`](Sophia_Unreal.md); where a step is the same as Sophia's, it says so instead of
repeating it.

**Where she stands.** She was imported on 2026-10-29 and again on 2026-11-01 (mesh, clips, Control
Rig, materials; commits `9782fd1`, `046f1fa`, `fb2c789`). Everything Blender added since then is
**not** in Unreal yet:
- the armour (14 pieces on one atlas), the gloves, the fins, the thigh plates and shoulder pads;
- the body masks and the HP wear;
- the anime eyes;
- the katana and its scabbard.

The export of 2026-11-03 has all of it. It checked out: five clips re-read within 0.009 mm of the
.blend, katana sockets equal to Blender's to 0.0007 cm, and 56 Control Rig recipes (8 twist, 48 corrective). Steps 1 to 4 bring the project up to date and have
commands. Steps 5 to 8 are what comes after, and none of them has been done for her yet.
**Nothing here has been run in the editor yet.**

---

## 0. Where everything is

| what | where |
|---|---|
| **The export (read-only for you)** | `Art\space_amazon\unreal\` |
| ⤷ the character | `SpaceAmazon.fbx` (cm, A-pose bind, no weapon), its textures `SpaceAmazon_*.png` |
| ⤷ clips | `SpaceAmazon_aerobic_dance_315220.fbx`, `_c08_low_hold_gun_turn180_l`, `_dance_graceful_378939`, `_katana_intro`, `_katana_embainhar` |
| ⤷ Control Rig recipes and the parity reference | `SpaceAmazon_receitas.json`, `SpaceAmazon_curvas_ref.json` |
| ⤷ the katana | `Props\Katana.fbx` (static mesh, pivot mid-grip), `Props\soquetes_unreal.json` (socket values, already in Unreal bone space) |
| ⤷ body masks | `mascaras\masks_rgba.png`, `mascaras\masks_rgba_2.png` |
| ⤷ HP wear | `feridas\SpaceAmazon_Feridas_*` |
| ⤷ what the export did | `SpaceAmazon_export.log` |
| Blender source | `Art\space_amazon\expr\e32_katana.blend` (built on e30, not on e31: see `Art\space_amazon\katana_UNREAL.md`) |
| Notes | `Art\space_amazon\katana_UNREAL.md` (katana), `Art\space_amazon\feridas_UNREAL.md` (wear), `Art\sophia_jaqueta_chaos_cloth.md` "Body masks" (the mask HLSL) |
| Unreal tools | `UnrealWorld\Tools\import_space_amazon.py`, `gerar_control_rig.py`, `paridade_control_rig.py` |
| In the project | `/Game/Chars/SpaceAmazon/` (mesh, skeleton, `CR_SpaceAmazon`, `animclips/`, `Materials/`, `Textures/`; `Props/` after step 1) |

### What is in her

- **Skeleton:** 142 bones in the FBX: the AccuRig `CC_Base_*` body, root `RL_BoneRoot`, plus these extras:
  - ears `CC_Extra_{L,R}_Ear01..03`;
  - hair: `CC_Extra_Ponytail..08`, `{L,R}_Lock..02`, `{L,R}_FrontLock..03`;
  - fins `CC_Extra_{L,R}_Fin01..03` (a chain off Spine02);
  - plates `CC_Extra_{L,R}_ThighPlate` (on Pelvis) and `CC_Extra_{L,R}_Shoulderpad` (on the clavicles);
  - `CC_Extra_Scabbard` (on Spine02; the scabbard mesh is 100% on it);
  - `CC_Extra_Katana` (on R_Hand, no weights; the katana clips key it).

  The fins, plates, scabbard and katana bones are **new to Unreal** (12 bones).
- **12 material slots:**
  - body;
  - lashes;
  - hair;
  - teeth;
  - mouth;
  - eyes;
  - tongue;
  - eye sockets;
  - armour atlas: Cuirass, arms, cannon, fins, glove caps, pads, plates, leggings, skirt;
  - left glove;
  - right glove;
  - scabbard.

  The bikinis are hidden in Blender and stay out of the FBX.
- **Morph targets:** 48 correctives (`CORR_*`, driven by the Control Rig) and 24 expressions with ARKit
  names (`eyeBlink_L`, `mouthSmile_R`, ...), plus `V_None`.

---

## 1. Import

Close the editor first (the commandlet and an open editor fight over the same assets), then:

```
"D:\UE5.7\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "D:\UnrealWorld\UnrealWorld\UnrealWorld.uproject" -run=pythonscript -script="D:/UnrealWorld/UnrealWorld/Tools/import_space_amazon.py"
```

Or, with the editor open: Output Log, switch the box to **Python**, and run
`py "D:/UnrealWorld/UnrealWorld/Tools/import_space_amazon.py"`.

It reimports over the existing assets, so whatever points at them keeps working. In order:

1. The mesh. The skeleton gains the 12 new bones.
2. The textures.
3. The 12 material instances, assigned by slot.
4. The five clips: `katana_intro` is replaced (now a retarget straight onto her), and `dance_graceful` and
   `katana_embainhar` are new.
5. **`Props/Katana`** as a static mesh with the scabbard's material.
6. It saves the whole folder.

**Read the last lines of the log.** You want:
- `SpaceAmazon: 142 bones, 73 morph targets, 12 material slots; hair bones missing: none` (72 morphs is fine
  too, if Unreal drops the empty `V_None`);
- a `SpaceAmazon: prop /Game/Chars/SpaceAmazon/Props/Katana -> MI_SpaceAmazon_Katana` line.

If it stops with `slots with no material in INSTANCES: [...]`, a slot name changed in Blender. Add
it to the `INSTANCES` table at the top of the script and run it again.

If the katana line is a warning instead, import `Props\Katana.fbx` by hand:
- Content Browser → Import, into `/Game/Chars/SpaceAmazon/Props`, as a **static mesh**;
- Import Materials **off**, Convert Scene **on**, Force Front X Axis **off**;
- then set its material to `MI_SpaceAmazon_Katana`.

## 2. Control Rig and the parity test

The 48 corrective curves and the thigh/forearm twist live in `CR_SpaceAmazon`, generated from the
recipes Blender exported. Never edit that graph by hand; regenerate it:

```
"D:\UE5.7\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "D:\UnrealWorld\UnrealWorld\UnrealWorld.uproject" -run=pythonscript -script="D:/UnrealWorld/UnrealWorld/Tools/gerar_control_rig.py D:/UnrealWorld/Art/space_amazon/unreal/SpaceAmazon_receitas.json /Game/Chars/SpaceAmazon/SpaceAmazon /Game/Chars/SpaceAmazon/CR_SpaceAmazon"
```

Then prove it on a clip that moves a lot. It fails loudly (nonzero exit) above 0.05 degrees or 0.002
in curve value:

```
"D:\UE5.7\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "D:\UnrealWorld\UnrealWorld\UnrealWorld.uproject" -run=pythonscript -script="D:/UnrealWorld/UnrealWorld/Tools/paridade_control_rig.py D:/UnrealWorld/Art/space_amazon/unreal/SpaceAmazon_receitas.json /Game/Chars/SpaceAmazon/animclips/SpaceAmazon_aerobic_dance_315220 /Game/Chars/SpaceAmazon/CR_SpaceAmazon 0.05 D:/UnrealWorld/Art/space_amazon/unreal/SpaceAmazon_curvas_ref.json"
```

Run it again with `SpaceAmazon_katana_intro` and `SpaceAmazon_katana_embainhar` in place of the
aerobic clip. On 2026-10-29 it passed at 0.0115 degrees worst (twist) and 0.0003 (curves).

**Hook it up.** She has no Anim Blueprint yet. Make one now; it is where everything below goes:
- Content Browser → right-click `SpaceAmazon_Skeleton` → Create → Anim Blueprint `ABP_SpaceAmazon`.
- AnimGraph: the clip or state machine first → a **Control Rig** node with `CR_SpaceAmazon` **last**
  → Output Pose. The correctives must run after everything that moves the bones.
- To preview the clips with correctives, set `ABP_SpaceAmazon` as the mesh's **Post Process Anim
  Blueprint** instead (Skeletal Mesh editor → Asset Details).

## 3. Look at her

- **Skeletal mesh editor.** All 12 slots are textured. The armour is the Tripo atlas, the gloves
  have their own textures, and the scabbard sits diagonally on her back with the mouth behind her right
  shoulder.
- **Skeleton tree.** Look for `CC_Extra_Scabbard`, `CC_Extra_Katana`, `CC_Extra_L_Fin01..03`,
  `CC_Extra_L_ThighPlate`.
- **Morph targets**, one at a time at 1.0: `eyeBlink_L` closes only the left eye; a `CORR_*` key
  changes only its own joint.
- **Clips with the Post Process ABP on:** `aerobic_dance` (squats are where missing correctives
  show), and both katana clips.
- **UV channel 1** is a grid of single points, one texel per vertex: that is the mask address
  (step 6). If it looks like an unwrap, the import swapped the UV channels.

## 4. The katana: sockets, notifies, attach

The weapon is never a child of the hand. It is a static mesh on a socket, and a notify moves it
between the scabbard socket and the hand socket.

**Sockets.** In the Skeleton editor, right-click the bone → Add Socket, then type the values from
`Props\soquetes_unreal.json`:

| socket | bone | Relative Location (cm) | Relative Rotation (X roll, Y pitch, Z yaw) |
|---|---|---|---|
| `katana_bainha` | `CC_Extra_Scabbard` | 0.014, 19.003, -0.980 | 58.256, 85.991, 148.096 |
| `katana_mao` | `CC_Extra_Katana` | 0, 0, 0 | -90, 0, 0 |

Check each one: right-click the socket → Add Preview Asset → `Props/Katana`.
- `katana_bainha` in the reference pose: the blade must vanish into the scabbard, with the guard sitting on the
  mouth.
- `katana_mao`: play `katana_intro` and the grip must stay in her fist.

The conversion from Blender assumes the FBX's Y flip. If `katana_bainha` is wrong, the other one
is too, and the fix is the rotation order, not new numbers. Tell me what you see.

**Notifies.** Unreal counts frames from 0, one less than Blender: <---- Parei aqui

| clip | frame | time | notify |
|---|---|---|---|
| `SpaceAmazon_katana_intro` | 4 | 0.133 s | `KatanaToHand` |
| `SpaceAmazon_katana_embainhar` | 29 | 0.967 s | `KatanaToScabbard` |

Add them as plain Skeleton Notifies (right-click the Notifies track → Add Notify → New Notify).

**Attach.** In her character Blueprint (or a test actor with a Skeletal Mesh component and
`ABP_SpaceAmazon`):
- A Static Mesh component `Katana` with `Props/Katana`; on BeginPlay, **Attach Component To
  Component** to the Mesh at `katana_bainha`, rules **Snap to Target** for location and rotation,
  **Keep World** for scale.
- In `ABP_SpaceAmazon`'s Event Graph, the events `AnimNotify_KatanaToHand` and
  `AnimNotify_KatanaToScabbard` re-attach the same component to `katana_mao` and `katana_bainha`.

Known: on Unreal frames 5 to 11 of the draw, the blade swings out through the side of the
scabbard. That is Grruzam's draw, not the sockets.

## 5. Plates and pads outside the exported clips

In Blender, each thigh plate and shoulder pad turns halfway (influence 0.5) towards a point on the
limb. The **exported clips have that baked in**, so they are right as they are. The constraint
itself does not travel through FBX. Any motion made in Unreal (retargeted locomotion, IK, aim
offsets) leaves the plates at rest, and the thigh goes through them.

When that matters, rebuild it in the Anim Blueprint, **not** inside `CR_SpaceAmazon` (it is
regenerated). Use a second Control Rig, or an AnimBP **Look At** / Control Rig **Aim**:
- bone: the plate;
- aim axis: the plate bone's length axis;
- target: a socket on the limb;
- weight 0.5.

The targets, in the limb bone's space, Unreal cm (Blender's Y flipped):

| plate bone | target socket on | location (cm) |
|---|---|---|
| `CC_Extra_L_ThighPlate` | `CC_Base_L_Thigh` | -14.46, -19.43, 0.86 |
| `CC_Extra_R_ThighPlate` | `CC_Base_R_Thigh` | 14.46, -19.43, 0.89 |
| `CC_Extra_L_Shoulderpad` | `CC_Base_L_Upperarm` | -2.81, -8.84, -6.10 |
| `CC_Extra_R_Shoulderpad` | `CC_Base_R_Upperarm` | 2.88, -8.94, -6.04 |

## 6. Body masks: armour on and off

The skin under each armour piece is hidden by the same trick as Sophia's (§4 of her guide, HLSL in
`Art\sophia_jaqueta_chaos_cloth.md` "Body masks"). A Custom node on World Position Offset reads the
mask on UV 1 and returns NaN for a hidden vertex whose piece is worn. Fearing has six slots in two
textures (0 = hidden where the piece is worn):

| texture | R | G | B | A |
|---|---|---|---|---|
| `mascaras\masks_rgba.png` | left arm (`Left_Arm`) | right arm (`Right_Arm`) | left hand (`Left_Glove`) | right hand (`Right_Glove`) |
| `mascaras\masks_rgba_2.png` | chest (`Cuirass` + both pads) | legs (`Leggins`) | | |

- Import both textures with sRGB **off**, compression **VectorDisplacementmap (RGBA8)**, filter
  **Nearest**, **NoMipmaps**, **Never Stream**.
- Make `M_SpaceAmazon_Body` = `M_SpaceAmazon_Base` + the mask node, and point `MI_SpaceAmazon_Body`
  at it.
- Two vector parameters: `Wear` = (left arm, right arm, left hand, right hand) and `Wear2` = (chest, legs, -, -).
  1 means worn.
- Keep **WPO Disable Distance** and **Max WPO Displacement** at 0, or the masks switch off quietly.
- The skirt, fins, plates, cannon and glove caps have no slot: they hang over other pieces.

Until this step, skin can show through the armour in places.

## 7. HP wear

Follow `Art\space_amazon\feridas_UNREAL.md`. One `HP` scalar (0..1) reveals each set's 0 HP layer:
- skin and hair: a multiply tint;
- armour and gloves: a cover with exposed metal.

The textures are in `unreal\feridas\`. It adds nodes to the body, hair, armour and glove materials, so
do it after step 6 (both touch the body material).

## 8. After that

- **Physics asset.**
  - The hair chains need a physics chain or AnimDynamics: the ponytail (9 bones), the locks and the front locks.
  - Colliders on Spine02 and the clavicles.
  - The fins are rigid on Spine02, and the scabbard is rigid on its bone.
  - The scabbard's tassel is rigid too; it could get its own bone later.
- **Expressions.**
  - The 24 ARKit morphs can be driven by curves or a Pose Asset, as for Ratoman and Sophia.
  - Her presets (laugh, evil laugh, happy, frown, loathing, pain, scream, cry) also turn the ear bones and
    the jaw. Those are Blender drivers on custom properties and do not cross the FBX. They need an
    expression controller in Unreal: a separate piece of work.
- **More clips.** The Grruzam katana clips are converted onto her by the batch (§10). Other locomotion could come
  from Manny/Quinn by IK Rig retargeting (Sophia §9).
- **Waiting in Blender** (the Fearing backlog): the wrist-cannon shot, the force field, and the fin animations.

## 9. The order that works

1. Import (§1). Read the last log lines.
2. Regenerate the Control Rig and run the parity test (§2). Make `ABP_SpaceAmazon`.
3. Look at her (§3).
4. The katana sockets, notifies and attach (§4). This is the first thing that is new for her in Unreal.
5. Masks (§6), then wear (§7).
6. Plates (§5) when the first Unreal-side motion arrives. Physics and expressions after that (§8).

## 10. The Grruzam clips (the batch)

These are Fearing's own conversions of the 465 Grruzam katana clips, made in her file. Sophia's clips cannot be
used: Fearing's twist, plates, pads, fins and scabbard exist in a clip only as baked bones. The process is in
gurps `tools/blender/grruzam-batch-plan.md` (the Fearing section at the top). The clip list is in
`grruzam-clip-map-fearing.md`, next to it.

**Blender side** (gurps `tools/blender`, system Python):

```
python lote_grruzam.py --quem fearing rodar 4 5 10 --paralelo 3 --ate 22:00
python lote_grruzam.py --quem fearing exportar 4        (one folder at a time)
python lote_grruzam.py --quem fearing notificacoes      (after every export)
python lote_grruzam.py --quem fearing mapa
```

The FBX files land in `Art/space_amazon/grruzam_lote/unreal/<folder>/SpaceAmazon_*.fbx`. They hold only the
armature, on the same 142-bone skeleton as `SpaceAmazon.fbx`, so the character never needs a reimport for them.

**Import**, with the editor closed:

```
"D:\UE5.7\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "D:\UnrealWorld\UnrealWorld\UnrealWorld.uproject" -run=pythonscript -script="D:/UnrealWorld/UnrealWorld/Tools/clipes_space_amazon.py Movements_Intro Movements_Idle Movements_Walk_A"
"D:\UE5.7\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" "D:\UnrealWorld\UnrealWorld\UnrealWorld.uproject" -run=pythonscript -script="D:/UnrealWorld/UnrealWorld/Tools/notifies_space_amazon.py"
```

With the editor open, use the Output Log (Python): `py "D:/UnrealWorld/UnrealWorld/Tools/clipes_space_amazon.py" Movements_Walk_A`.
Run it without folder names to import every exported folder.

- **One Unreal folder per batch folder.** The clips go to `/Game/Chars/SpaceAmazon/animclips/<folder>/`. Grruzam
  reuses 10 clip names across two folders, so a flat folder would overwrite one clip of each pair.
- **Root motion.** Clips named `_Root`, and every clip in a `RootMotion` folder, get **Enable Root Motion**. The travel is
  on `RL_BoneRoot`. The in-place twin of each one has its root at rest.
- **Notifies.** `notifies_space_amazon.py` owns every `Attach To Socket` notify on these clips. It removes the ones that
  are there, including the hand-placed ones, then adds the json's on a track named `Katana`: `katana_mao` at the draw,
  `katana_bainha` at the sheathe. It does the same for the flat `animclips/SpaceAmazon_katana_intro` and
  `_katana_embainhar`, which are the same clips (checked to 0.001 mm in Blender). Running it a second time changes
  nothing. A clip that starts or ends with the katana in her hand gets no notify for that. The state machine must
  already have the katana in her hand.
- **Expressions** stay at rest in these clips (jaw and ears included). The Pose Blender's additive expressions ride on top.
