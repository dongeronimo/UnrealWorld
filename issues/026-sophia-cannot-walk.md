# 026 — Sophia can't walk: no IK Rig, and no locomotion retargeted to her

**Area:** anim · **Status:** open · **Blocked by:** 020 · **Blocks:** 027, 029

## Context

*Filed 2026-10-23.*

Phase 0 of `Sophia_Animation_Plan.md` §6 is "Sophia imported … Game Animation Sample retargeted to
her", done when "she walks around with the GAS locomotion". Her locomotion comes from Epic's free
sets: the **Game Animation Sample** (starts, stops, pivots, turns) and **Lyra** (pistol sets),
through Manny → her IK Retargeter. The IK Rig is built as Ratoman's (014), because it's the same
CC_Base skeleton.

The clips she already has: `hold_gun_fastrun_forward` (start, loop, end), `c08_low_hold_gun_turn180_l`,
the four idles and their transitions (`idle_hand_on_hip`, `idle_look_nails` and their 40-frame
transitions), and the dances.

## What to do

- `IK_Sophia`, using 014's chain table. Leave the twist bones, the hair, `CC_Extra_Holster`,
  `CC_Extra_Scabbard` and `CC_Extra_Katana` unmapped.
- `RTG_Manny_to_Sophia`. She's in an A-pose, so use Auto Align on the arms. Check her stride and
  crotch height, because she's much shorter than Ratoman.
- Retarget the GAS locomotion set, or migrate GAS's motion-matching setup if it's affordable on
  mobile. Measure before committing: a state machine is the safe default for the phone.
- `ABP_Sophia` v0: full-body locomotion by speed and direction, plus her idles as the standing
  state, with the transitions entered at their start (§0's note: they line up frame-exactly).

## The tempting wrong fixes

- **Motion matching on the phone without measuring.** Its pose search costs CPU per character. The
  arena has one Sophia, but Ratomen may want the same system later.
- **Mapping `CC_Extra_Katana` to Manny's `weapon_r` or similar.** The katana bone is keyed by the
  Grruzam clips (028). Retargeted locomotion must leave it alone.

## Done when

- She walks, jogs, runs, starts, stops and turns with GAS clips, plays her own idles standing, and
  her feet plant.
- The correctives (021) show no collapse during the locomotion, if 021 is done. Otherwise this card
  records that it isn't.

## Files

```
Sophia_Animation_Plan.md   §2 (locomotion row), §5, §6 (phase 0)
Sophia_Unreal.md           §9
issues/014-ratoman-has-no-ik-rig.md   the chain table
```
