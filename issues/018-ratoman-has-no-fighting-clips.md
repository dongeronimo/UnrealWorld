# 018 — Ratoman has no clips to fight with: no locomotion, attack, hit react or death

**Area:** anim + content · **Status:** open · **Blocked by:** 014 (done 2026-10-24) · **Blocks:** 039, 019

## Context

*Filed 2026-10-23.*

His clips today are the aerobic dance and the two expression clips. The arena (031, 032) needs a
brute that walks or runs at Sophia, swings at her, flinches and dies. In the room session (034) he
has to walk.

He's 2.0 m, hunched, long-armed, with claws: he reads as a **melee brute**. The set:

| clip | source |
|---|---|
| idle, walk, run, plus starts, stops and turns if available | Manny's clips from the Third Person template, through 014's retargeter |
| 2–3 melee swings (claw or overhead smash) | Mixamo, retargeted (the `mixamorig:*` → `CC_Base_*` map), or Lyra |
| hit react, front and back | Lyra or Mixamo |
| death | a clip, or the ragdoll from 017 with a short physics blend |
| aggro roar | any clip, plus 013's Scream curve |

The licences are recorded in `Sophia_Animation_Plan.md` §4. Lyra is free for Unreal
projects. Mixamo is royalty-free in games, and the raw files can't be redistributed.

## What to do

- Retarget the set through 014. Each clip gets checked through `ABP_Ratoman_Post` (015).
- `ABP_RatomanBrute`:
  - a locomotion blend by speed;
  - a montage slot for attacks and hit reacts;
  - the face additive (013).
- **Anim notifies** on each swing are `AnimNotify_SendGameplayEvent` with `Event.Melee.HitWindow.Open`
  and `.Close` (037's tags). They don't run gameplay: `GA_RatomanClaw` (039) listens and sweeps.
  Add a footstep notify too.
- The AnimBP plays what the abilities start. Attacks and hit reacts are montages that abilities
  play (039, 030), not states the AnimBP enters on its own.
- **Root motion:** attacks with lunges use root motion, and locomotion is in place, driven by the
  movement component's speed.

## The tempting wrong fixes

- **Animating his attacks by hand in Unreal's editor.** It's slow and stiff. The free sets cover
  a first version, and the claw specifics can be keyed later.
- **Hit detection from a sphere around the hand on every frame.** Swing windows come from
  notifies, or every idle twitch hits.
- **Speeding up Manny's walk to make him "heavy".** A brute reads heavy when he's *slower* with
  longer strides. Scale the play rate down, and use the retargeter's stride settings.

## Done when

- In `RatomanBrute_Test`, he idles, walks, runs, swings with notifies firing in the log, flinches
  and dies, all through `ABP_RatomanBrute` with the face and twist layers on.

## Files

```
Ratoman_Brute_Unreal.md   §3, §9
Sophia_Animation_Plan.md  §4: where free clips can legally come from
UnrealWorld/Content/Chars/RatomanBrute/
```
