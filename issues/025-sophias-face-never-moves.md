# 025 — Sophia's face never moves: 22 expression keys and no Pose Asset

**Area:** anim · **Status:** open · **Blocked by:** 020

## Context

*Filed 2026-10-23.*

`Body_Rigged` carries 22 expression shape keys with **ARKit names** (`eyeBlink_L`, `mouthSmile_R`, …).
`Sophia_Unreal.md` §6 says to use a Pose Asset, as for Ratoman (013). The ARKit names mean Live Link
Face can drive them directly later.

**The retargeted clips key the face bones** (`CC_Base_FacialBone`, `JawRoot`, `UpperJaw`, the
eyes), per §11. Expressions belong to the blendshapes and the expression controller. So either strip
those tracks on import, or run the face layer **after** the clips in the AnimBP. The idles and their
transitions don't key them.

## What to do

- Build a small set of expressions from the 22 keys. For a commissar: neutral, a focused glare
  for aiming, a battle cry for melee, pain, and a smirk at extraction. Make them an additive Pose
  Asset driven by curves, as in 013.
- **Blink:** a procedural `eyeBlink_L/R` curve on a random 2–6 s timer, so she never stares
  frozen.
- Strip the face-bone tracks from retargeted clips, or order the layer so it wins.

## The tempting wrong fixes

- **Leaving the face-bone tracks in and adding the expressions on top.** The clip's jaw and the
  expression's jaw sum, and her mouth opens on every step of the run.
- **Driving all 22 morphs from gameplay one by one.** Gameplay names a mood. The Pose Asset turns
  it into morphs.

## Done when

- During the arena loop she blinks, glares while aiming, shouts on a cut and winces on a hit.
- No clip moves her jaw by accident.

## Files

```
Sophia_Unreal.md   §6, §11
issues/013-ratomans-face-is-not-in-an-animbp.md   the same recipe
```
