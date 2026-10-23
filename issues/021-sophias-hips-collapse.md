# 021 — Sophia's hips collapse in every crouch: the correctives and thigh twist have no driver in Unreal

**Area:** anim · **Status:** open · **Blocked by:** 020 · **Blocks:** 029

## Context

*Filed 2026-10-23.*

In Blender, 26 `CORR_*` shape keys and 4 thigh-twist fractions are driven by the joint angles.
**Drivers don't survive FBX.** `Sophia_Unreal.md` §5: "Without this step her hips collapse in every
crouch. It matters more than anything else here." The skirt and the panty carry the same 26 `CORR_*`
names, so one evaluation drives all three meshes.

The rule table and its reference values are already written:
- `Art/Sophia_corretivos_UNREAL.md` has the rules;
- `Art/Sophia_corretivos_referencia.csv` has the values to check against.

The same problem in Unity is gurps card 095.

## What to do

- Implement the rule table as a Control Rig: read the joint angles in the pose's space, compute
  each `CORR_*` weight, and write it as a curve that drives the morph target.
- Drive the 4 thigh-twist fractions the same way, in the same rig.
- It runs **last**, on the final pose: after locomotion, the upper-body layer, the aim offset and
  the additives (`Sophia_Animation_Plan.md` §5). As a post-process ABP on the mesh, like
  Ratoman's 015, it runs after everything for free.
- Verify against the CSV. Pose her at the CSV's sampled angles, read the morph weights, and
  compare. The tolerance is written into the doc or this card.

## The tempting wrong fixes

- **Baking the correctives into each clip in Blender.** Retargeted clips (GAS locomotion) never pass
  through Blender, and the blends between clips need correctives evaluated on the blended pose.
- **A Pose Driver node per corrective, set up by eye.** The weights were solved against exact
  angle rules. Reproduce the rules, then check them against the CSV.
- **Cutting the influences to 4 after this card.** The correctives were solved against those
  exact weights. If 020 has to cut influences, do it before this card, and re-check the CSV.

## Done when

- A deep squat and a lunge show no hip collapse.
- Her morph weights match the CSV within tolerance at every sampled pose, and the comparison is
  recorded here.

## Files

```
Sophia_Unreal.md   §5
Art/Sophia_corretivos_UNREAL.md, Art/Sophia_corretivos_referencia.csv
D:\gurps\issues\095-corrective-shape-keys-have-no-driver-in-unity.md
```
