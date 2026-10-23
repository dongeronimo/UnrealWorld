# 013 — Ratoman's expressions play only as a test clip: no Pose Asset in an AnimBP

**Area:** anim · **Status:** open · **Blocks:** 019 (an angry or screaming brute is part of how he reads as a threat)

## Context

*Filed 2026-10-23.*

Ratoman is imported and checked (`Ratoman_Brute_Unreal.md` §1–2, every box ticked). In
`Content/Chars/RatomanBrute/animclips/`:
- `Ratoman_Brute_Expressoes_teste` plays all four expressions in sequence, and the face, ears and
  jaw move.
- `Ratoman_Brute_Expressoes_poses` is the 5-frame clip that holds one pose per frame: neutral,
  angry, evil_laugh, pain, scream. It is untracked in git as of this card.

A clip that plays expressions is not a face that gameplay can drive. §8 of the guide is the recipe:
- an **additive** Pose Asset with base = Neutral;
- driven by curves (`Angry`, `EvilLaugh`, `Pain`, `Scream`, each 0..1);
- applied on top of whatever the body plays.

## What to do

- Create `PA_Ratoman_Faces` from `Expressoes_poses`. Rename the poses `Neutral`, `Angry`, `EvilLaugh`,
  `Pain`, `Scream`, and make it Additive with base pose Neutral.
- `ABP_Ratoman` (the gameplay AnimBP, which 018 and 019 grow): `[body] → Apply Additive (PA node driven
  by curves) → Output`.
- Float variables `AngryWeight`, … set the curves through Modify Curve. Gameplay sets them (pain on a
  hit, a scream on aggro, a laugh when Sophia goes down).
- A test: the dance plus `Angry = 1`, then `Pain = 0.5` mixed in.

## The tempting wrong fixes

- **Playing the expression clips as montages.** One expression at a time, no blending with each
  other, and they fight the body for the head and jaw bones.
- **Non-additive poses.** He then snaps to the 5-frame clip's body pose whenever he makes a face.
- **Driving the morph targets directly from Blueprint.** It loses the bone half of each
  expression (jaw, ears, whiskers, head), which lives in the pose, not the morphs.

## Watch for

- `evil_laugh` tips the head back 10° and `scream` raises it 6°. That is fine additively. Zero
  `CC_Base_Head` in those poses if the body should own the head.
- The jaw opens with a **negative** rotation on this rig.
- Put tail and ear physics (016) **after** this layer, so the ears react to their own expression
  rotation.

## Done when

- `PA_Ratoman_Faces` exists, is additive, and has its five named poses.
- In `RatomanBrute_Test.umap`, he dances with each expression layered on by variable, and two
  expressions blend at once.

## Files

```
Ratoman_Brute_Unreal.md   §8, §9
UnrealWorld/Content/Chars/RatomanBrute/animclips/Ratoman_Brute_Expressoes_poses
UnrealWorld/Content/Levels/RatomanBrute_Test.umap
D:\gurps\tools\blender\pele\ratoman_brute.json   the expression values, if a shape needs changing
```
