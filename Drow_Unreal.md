# The drow in Unreal

Written 2026-11-21 for **UE 5.7**, the pilot of step 5 of the drow's plan (gurps `docs/drow-character-handoff.md`,
"Next: to Unreal"). Fearing's guide is [`SpaceAmazon_Unreal.md`](SpaceAmazon_Unreal.md); this one only says where
the drow differs.

**The difference:** she is **modular**. `Drow` is her body and face only. Each garment, hair, the holster and the
scabbard is its own skeletal mesh on the same `Drow_Skeleton`, and follows the body by **Leader Pose**. Her outfits
are alternatives over the same region (jacket / shirt / gym top, pants / miniskirt / bikini, boots / tennis), so one
merged mesh would need one asset per combination.

Everything below was run headless on 2026-11-21 and passed, and the user looked at section 3 in the editor the same
day: all OK. This is the first time she is in Unreal.

## 0. Where everything is

| what | where |
|---|---|
| The export (read only) | `D:\drow\unreal\` |
| ⤷ leader | `Drow.fbx` (body, eyes, teeth, tongue, mouth) |
| ⤷ pieces | `Pecas\Drow_<Piece>.fbx`, 14, each with all 158 bones |
| ⤷ clips | `Drow_aerobic_dance_315220`, `_c08_low_hold_gun_turn180_l`, `_dance_graceful_378939`, `_katana_intro`, `_katana_embainhar` |
| ⤷ props and sockets | `Props\{Katana,Pistol,Glass_Rayban,Kitty_Headphone}.fbx`, `Props\soquetes_unreal.json` |
| ⤷ what the import reads | `Drow_modular.json` (FBX, objects, shape keys, materials), `Drow_katana_notifies.json` |
| ⤷ Control Rig | `Drow_receitas.json`, `Drow_curvas_ref.json` |
| In the project | `/Game/Chars/Drow/`: `Drow`, `Drow_Skeleton`, `Pieces/`, `animclips/`, `Materials/`, `Textures/`, `Props/`, `CR_Drow`, `ABP_Drow_Post_Process`, `BP_Drow` |
| C++ | `Source/UnrealWorld/Drow.*` (`ADrow`), `SocketTools.*` (sockets from Python), `ModularChecks.*` (does a follower get the leader's correctives) |
| Tools | `Tools/import_drow.py`, `drow_control_rig.py`, `notifies_drow.py`, `abp_drow.py`, `bp_drow.py`, `check_drow_correctives.py` |

## 1. Rebuild it (editor closed)

`UE = "D:\UE5.7\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" D:/UnrealWorld/UnrealWorld/UnrealWorld.uproject -run=pythonscript -script=`

In order, each `UE"D:/UnrealWorld/UnrealWorld/Tools/<script>"`:

1. `import_drow.py`: textures, materials, the leader, the 14 pieces on its skeleton, clips, props, sockets on the
   `Drow` mesh. It fails if a piece lands on another skeleton, a slot has no material, or a piece lost a `CORR_*`.
   The 8K skin is capped at 4096 (Maximum Texture Size).
2. `drow_control_rig.py`: generates `CR_Drow` and runs the parity test on aerobic, katana_intro and katana_embainhar.
3. `notifies_drow.py`: `AttachToSocket` notifies: katana_intro frame 4 → `katana_mao`, katana_embainhar frame 29 →
   `katana_bainha`.
4. `abp_drow.py`: `ABP_Drow_Post_Process` (a copy of Fearing's, pointed at `Drow_Skeleton` and `CR_Drow`), set as
   the Post Process Anim Blueprint of `Drow`.
5. `bp_drow.py`: `BP_Drow` over `ADrow`, and a check of its pieces, props and sockets.
6. `check_drow_correctives.py`: the pants and the jacket get the body's correctives (section 3, item 1).

**Only textures changed** (same PNG paths, e.g. the 2026-11-22 recolour: light skin, green eyes, dark red hair):
`UE"D:/UnrealWorld/UnrealWorld/Tools/import_drow.py texturas"` reimports the manifest's textures over `T_Drow_*` and
saves only them. A full run would also reimport every mesh and rewrite the whole `/Game/Chars/Drow` tree. The
script's own log lines (`Drow: ...`) are in `Saved/Logs/UnrealWorld.log`, not on the console.

**Only the pieces changed** (meshes, UVs, their textures, e.g. `textura_peca.py` on 2026-11-22):
`UE"D:/UnrealWorld/UnrealWorld/Tools/import_drow.py pecas"` reimports the pieces' textures, their material
instances and the 14 `Pecas/*.fbx`, saves only those, and deletes the `T_Drow_*` textures the manifest no longer
names, if nothing references them. The leader, the skeleton, the clips and the props are not touched. Re-export
the package first (the manifest carries the PNG paths).

A C++ change needs the build first (`Engine\Build\BatchFiles\Build.bat UnrealWorldEditor Win64 Development
-Project=...`).

**Results of 2026-11-21:** 158 bones. Leader 78 morph targets (`V_None` is equal to the basis and does not come).
Jacket 48, Cargo_Pants 32, Shirt 36, Gym_Top 25, Miniskirt 26, Bikini_Bottom 20, Holster 20. Parity PASS: twist
worst 0.011°, curves worst 0.0002.

**2026-11-22:** `CR_Drow` regenerated with the forearm twist: 62 recipes, 8 of them twist. Parity PASS; the worst
forearm is 0.011°, against up to 80° without the recipe.

**Grruzam clips (gurps drow handoff, step 6)**, after the batch exports a folder
(`lote_grruzam.py --quem drow exportar N`, then `notificacoes`):

7. `clipes_drow.py [FOLDER ...]`: `D:/drow/grruzam_lote/unreal/<folder>/Drow_*.fbx` →
   `/Game/Chars/Drow/animclips/<folder>/`. Root motion is set on `_Root` clips and RootMotion folders, and frame
   counts are checked against the batch. No folder given = every exported folder.
8. `notifies_drow.py D:/drow/grruzam_lote/unreal/katana_notifies.json`: the katana swaps on the batch's clips.
   Without an argument it reads the pilot's `D:/drow/unreal/Drow_katana_notifies.json`, for the two flat clips.

Pilot imported 2026-11-22: `Movements_Intro` (1), `Movements_Idle` (8), `Movements_Walk_A` (24); 3 katana swaps.
**The whole batch, 2026-11-22:** 34 folders, 465 clips in `animclips/<folder>/`, 150 with root motion, 57 katana swaps.
The clip map, from Grruzam clip to Blender action to Unreal FBX, is `D:/gurps/tools/blender/grruzam-clip-map-drow.md`.
**Look at:** the right boot toe on planted frames (`Drow_katana_Walk_ver_A_Front_Root` around frame 14,
`Drow_katana_Idle_ver_B` around frame 33). Blender measures it 27 mm into the floor.

**2026-11-22, textures (gurps drow handoff, steps 7-8):** each piece and hair has its own texture with only
itself in it, in `D:/drow/textures/unreal/Drow_<Piece>.png`: 1024 for Jacket, Boots, Tennis, Katana_Sheat,
Hair_Braid and Hair_Ponytail, 512 for the other 8. About 120 MB of GPU memory down to about 5.6 MB. `pecas`: 42
assets changed, 5 old 4K textures deleted, morph counts as on 2026-11-21, `check_drow_correctives.py` PASS.

## 2. What is in her

- `BP_Drow` (parent `ADrow`): the body, plus a skeletal mesh component per piece, named as in Blender. **Visible =
  worn.** On by default: Jacket, Cargo_Pants, Boots, Hair_Braid (the pilot), Holster, Katana_Sheat. The other 8 are
  there and hidden.
- Props: `Katana` (tag `Katana`, on `katana_bainha`), `Pistol` (`pistola_coldre`), `Glasses` (`glass_rayban`),
  `Headphone` (`kitty_headphone`). Their materials are Sophia's instances.
- Sockets are on the **`Drow` mesh**, not the skeleton (Mesh editor → Skeleton Tree). `pistola_mao` does not exist
  yet (step 11).
- Two-sided materials: only the braid (its thin locks are open sheets) and the mouth. The rest rely on culling.
- The skin under a garment still renders. Body masks are step 9.

## 3. Look at her (done 2026-11-21, all OK)

Drop `BP_Drow` into a level. Select it → `Mesh` (the body) → Animation → **Anim to Play**, then **Simulate**
(Alt+S) or PIE. Animations do not play in the editor viewport.

1. **The correctives move the pieces too. Verified headless 2026-11-21** (`Tools/check_drow_correctives.py`, by the
   C++ `UModularChecks::FollowerMorphReport`). It poses the body at a frozen time of the aerobic clip, runs the post
   process on and off, puts a piece in Leader Pose beside it, and reads the morph weights. With the post process on,
   each curve is identical on the body and on the piece:

   | piece | time | curves (on) |
   |---|---|---|
   | pants | 8.53 s | `CORR_L_Quadril_f090_a00` 0.726, `CORR_L_Quadril_f125_a00` 0.216 |
   | jacket | 8.90 s | `CORR_R_Axila_b090_f045` 0.331, `CORR_R_Axila_b090_f000` 0.190 |

   With it off, everything is 0.

   **To see it** (optional):
   - The Post Process Anim Blueprint is a field of the **`Drow` mesh asset** (open `/Game/Chars/Drow/Drow`, Asset
     Details, search "post process"). It is not on `BP_Drow`. The per-instance switch is on the instance's body
     component: select the instance, click **Mesh (CharacterMesh0)** in the component list at the top of Details,
     and search "post process" to find **Disable Post Process Blueprint**.
   - Two instances, A and B. On both, Mesh → Animation: Anim to Play `Drow_aerobic_dance_315220`, Initial
     Position 8.53, Playing off. Tick Disable Post Process Blueprint on B only, then Simulate.
   - Look at her left hip and groin: the pants move up to 91 mm there. Then set both to 8.90 and look at her right
     armpit and the side of her chest: the jacket moves at least 78 mm, held for half a second.
   - The jacket's biggest move, 109 mm at 10.07 s, is a one-frame spike (`CORR_R_Axila_b045_f090`: 0.29, 0.87,
     0.50, 0 over Blender frames 302–305). Do not use it to look.
2. **No holes from normals.** Orbit the jacket (lapel, inside of the collar), the pants and the braid. The braid's
   thin locks by the face must be there from both sides.
3. **Sockets.** The katana's guard sits on the scabbard's mouth. The pistol is in the holster, grip back (a strip of
   the slide pokes through the pouch: known and accepted). The glasses sit on the nose and the headphone cups are on
   the ears.
4. **Katana notifies.** Play `Drow_katana_intro`: the katana jumps to her hand at 0.133 s and stays in her fist.
   `Drow_katana_embainhar`: it goes back to the scabbard at 0.967 s.

If any of these is wrong, it is a Blender fix plus a re-export, not an edit here.

## 4. Known

- **The forearm twist is not in `CR_Drow`.** Blender drives `ForearmTwist01/02` (0.25 and 0.5 × the hand's twist,
  `torcao_antebraco.py`), but those rows are missing from her recipe table. Only the 4 thigh rows are there. The
  clips carry the baked twist, so plain playback is right. Anything that turns the hand after the clip (IK, aim
  offsets) will leave the forearm behind.
- Six pieces (`Choker`, the three hairs, `Holster`, `Katana_Sheat`) have two material slots since 2026-11-22: a
  reimport keeps the old `tripo_mat_<hash>` slot when Blender renames the material. It is unused, and
  `import_drow.py` gives it the same instance. Removing it would shift the section indices.
- `T_Drow_jacket`, `_boots`, `_cargo_pants`, `_gym_top`, `_shirt` keep their old lower-case names (Unreal names
  are case-insensitive) and hold the new 512/1024 textures.
- `notifies_drow.py` and `bp_drow.py` own what they write. A hand edit to the Katana notify track is replaced on
  a rerun.
