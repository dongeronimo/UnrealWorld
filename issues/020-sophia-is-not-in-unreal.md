# 020 — Sophia isn't in Unreal: export, import and the first check

**Area:** art + anim · **Status:** open, parked 2026-10-26: Blender side done, Unreal import waits for Sophia's own cards (see Progress) · **Blocks:** 021–029

## Context

*Filed 2026-10-23.*

Everything about Sophia is in Blender, in `D:\UnrealWorld\Art\`. `Sophia_Unreal.md` is the plan,
and it says "None of these steps has been run in an editor". §1–3 are this card:
- **§1, export:** `aplicar_escala.py`, then `exportar_unreal.py`;
- **§2, import:** as Ratoman, plus morph targets, Vertex Colour = Replace, imported normals,
  8 bone influences, the mask address on UV 1, and texture settings;
- **§3, check:** each morph alone, the jacket's vertex colours, and UV 1 as a grid of points.

Her skeleton is the same AccuRig `CC_Base_*` as Ratoman's, with 117 bones:
- `CC_Extra_Holster` and `CC_Extra_Scabbard`;
- three hair chains;
- the katana weapon bone `CC_Extra_Katana` under `R_Hand`.

**Which file to export is ambiguous**, and resolving it is the first step:
- `Sophia_Unreal.md` §0 says `sophia_idle.blend`.
- §11 (2026-10-16, katana) says `sophia_katana_clips.blend`, which has the clips `katana_intro` and
  `katana_embainhar`. That file is newer and has the scabbard moved to her back (`Spine02`).

Check that `sophia_katana_clips.blend` still carries the idles, the masks and the correctives. If it
does, it's the export file, and §0 gets corrected.

## What to do

- Resolve the export file, and fix §0.
- Run §1:
  - `aplicar_escala.py` has **never been run on Sophia**. Read its proof output: it refuses to save
    if any vertex moves more than 0.1 mm.
  - Take the props out of the character FBX: the pistol, the katana, the glasses and the headphones.
    The weapons are never children of the hand (user decision, 2026-10-16).
- Import to `Content/Chars/Sophia/` with §2's options, the texture table and the material sections.
- Run §3's three checks and Ratoman's §2 list (height, bone count, scale 1, A-pose reference).
- Find out the mobile skinning limit. If the target caps at 4 influences, run `limitar_influencias.py`
  in Blender. Don't let Unreal cut silently: 1,613 body vertices use more than 4.

## Progress

*2026-10-25, the Blender side is done* (see `Sophia_Unreal.md` §0, §1 and §11):
- **The export file is `sophia_katana_clips.blend`.** It has the idles, the masks and the 52 shape
  keys, and the Grruzam batch builds from it. §0 is fixed.
- `lote_grruzam.py personagem` ran `aplicar_escala.py` (worst 0.0008 mm) and exported
  `Art/grruzam_lote/unreal/Movements_Intro/Sophia.fbx`. It's in cm, has 118 bones, and the props
  are out: the new `sem_props` flag of `exportar_unreal.py`.
- The props are static mesh FBXs in `Art/grruzam_lote/unreal/Props/`, with `soquetes_unreal.json`
  holding the sockets already in Unreal terms. Not checked in the editor yet: check
  `katana_bainha` first.
- `katana_notifies.json` (from `lote_grruzam.py notificacoes`) is the swap frame for each of the
  465 clips, ready for when 026 imports them.
- The old FBX with props is not kept in the repo. Re-export it if needed: drop `sem_props`.

**Still open, Unreal side:** the import with §2's options, materials and textures (plus the three
wound textures of `Art/sophia_feridas_UNREAL.md`), the §3 checks, the sockets, and the mobile
skinning limit.

## The tempting wrong fixes

- **Exporting with modifiers on.** The MASK PREVIEW modifiers delete faces, and the shape keys are
  lost.
- **Letting the importer generate lightmap UVs.** UV 1 is the mask address, and a generated
  lightmap overwrites it silently.
- **Skipping `aplicar_escala.py` and fixing the scale in the importer.** That's Ratoman's first
  export: the ×100 ends up on the root bone, and every location key is wrong by the same factor.

## Done when

- Sophia stands in a test level in her A-pose, textured. All 52 shape keys appear as morph
  targets, the jacket's vertex colours show in the vertex colour view, and UV 1 is a grid.
- The weapons and props exist as separate static meshes.
- §0 of `Sophia_Unreal.md` names the right file.

## Files

```
Sophia_Unreal.md   §0–3, §11
Art/sophia_katana_clips.blend, Art/sophia_idle.blend
D:\gurps\tools\blender\aplicar_escala.py, exportar_unreal.py, limitar_influencias.py
Art/sophia_soquetes.json   the weapons' socket transforms
```
