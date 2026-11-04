# 044 — Sophia has no clips to be hurt with: hit react, death, dodge and the injured run

**Area:** anim + content · **Status:** open · **Blocked by:** 020, 026 (`ABP_Sophia` to check them in) · **Blocks:** 030 on her (`GA_HitReact`, `GA_Death`), 038 (`GA_Dodge`), 043 (the injured run)

## Context

*Filed 2026-10-27.*

030 plays a hit react and a death on whoever is hit, and 038's `GA_Dodge` plays a root-motion
dodge. The Ratoman's versions are 018. Sophia's had no card: 030 only says "Lyra or GAS clips".

They don't need Lyra. **The Grruzam batch already exported them to her skeleton**
(`Art/grruzam_lote/unreal/`, built by `lote_grruzam.py` from `sophia_katana_clips.blend`, 2026-10-25):

| folder | clips |
|---|---|
| `Damages_Front` | 15: small and big hits, ver A–D |
| `Damages_Back`, `_Left`, `_Right` | 5, 2, 3 |
| `Damages_Die` | `Damage_Die`, `_Loop`, `_Root` |
| `Damages_KnockDown` | 18: knockdown, ground loop, roll and stand up |
| `Movements_Dodge` | 6: front, back, left, right, … |
| `Movements_Run_Injured` | 6: the injured run, with damage variants |

They are retargeted in Blender and key `CC_Extra_Katana`, like 028's clips.
`grruzam_lote/unreal/katana_notifies.json` says where the katana is in each one.

## What to do

- Import the set onto her skeleton. Strip the face-bone tracks (025, `Sophia_Unreal.md` §11).
- **Pick the minimum for the arena.** Don't wire all 52:
  - hit react: one small and one big front, one back, left and right;
  - death: `Damage_Die`, ending in `Damage_Die_Loop`, or the ragdoll from 023;
  - dodge: the four directions;
  - the injured run.
- Montages:
  - `AM_Sophia_HitReact` with a section per direction. `GA_HitReact` (030) picks the section from
    the hit result's direction;
  - `AM_Sophia_Death`;
  - `AM_Sophia_Dodge` with a section per direction, root motion on.
- **The katana in these clips.** A hit react must not draw or sheathe it. Check each picked clip in
  `katana_notifies.json`: use the variant that matches `State.Katana.Drawn`, or pick clips that
  keep the katana where it was.
- The injured run goes into `ABP_Sophia`'s locomotion as an alternative run, selected by the HP
  threshold from 043.

## The tempting wrong fixes

- **Retargeting Lyra's hit reacts through `RTG_Manny_to_Sophia` instead.** These were already
  made for her, with the katana bone keyed. Lyra's leave `CC_Extra_Katana` at rest.
- **A full-body hit react while she's shooting.** Small hits go in the UpperBody slot so the legs
  keep moving. Only the big hits and the knockdown take the full body.
- **Playing the montages from the AnimBP on a Health change.** The abilities play them (030, 038).
  The AnimBP only has the slots.

## Done when

- In a test level, each montage section plays on her through `ABP_Sophia`, with no katana jump
  and no jaw moving.
- The dodge travels by root motion, and the injured run blends in and out of the normal run.

## Files

```
Art/grruzam_lote/unreal/Damages_*, Movements_Dodge, Movements_Run_Injured
Art/grruzam_lote/unreal/katana_notifies.json
Sophia_Unreal.md   §11 (the katana bone, the face-bone tracks)
issues/030, 038 (the abilities that play these), 043 (the injured run's threshold)
```
