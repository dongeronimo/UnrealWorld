# 023 — Sophia has no physics asset, and her hair goes through the jacket

**Area:** anim + physics · **Status:** open · **Blocked by:** 020 · **Blocks:** 024, 030 (being hit)

## Context

*Filed 2026-10-23.*

Her physics asset does more than Ratoman's (017). The jacket cloth (024) and the hair chains collide
with it, so its shapes are chosen for **what rests on them**, not for the skin. `Sophia_Unreal.md` §7
has the table:
- thick capsules on the upper arms, as thick as the jacket sleeve, not the arm;
- two spheres on `Spine02` enclosing the shirt;
- constrained capsules on `CC_Extra_Holster` and `CC_Extra_Scabbard`;
- the three hair chains (`CC_Extra_HairBack` root + 5, `HairL` root + 3, `HairR` root + 3)
  simulated from the bone below each root.

**Known limit (§11): her hair goes through the jacket.** The hair is part of `Body_Rigged`, and
nothing in Blender fixes it. The hair-chain physics, with the `Spine02`, clavicle and breast-sphere
colliders, is the first thing to try.

**Note:** the scabbard moved to her back (`CC_Extra_Scabbard` is now a child of `Spine02`, katana
work 2026-10-16). §7's line "constraint to the Pelvis" was written before that, so check the
constraint's parent.

## What to do

- Build the asset to §7's table. Delete the bodies on fingers, twist bones and the face.
- Hair: Kawaii Physics (Fab) or AnimDynamics on the three chains, in her post-process ABP, colliding
  with the capsules and spheres. The roots stay kinematic (gurps 047's rule). A teleport resets
  them to rest.
- Holster and scabbard: the constrained bodies from §7, so they sway slightly when she runs.
- A trace-channel setup like 017's, so 030 can hit her.

## The tempting wrong fixes

- **Capsules fitted to the skin on the arms.** The jacket's front panel then slips into the sleeve
  (§7).
- **Simulating the hair roots.** The scalp lifts off the head.
- **Pushing the hair mesh outward so it clears the jacket.** Collision is the solver's job (gurps
  047, "The tempting wrong fixes").

## Done when

- In a run and a turn, the hair swings and stays outside the jacket's back and shoulders, or the
  card records the residual crossings with screenshots and moves them to Known.
- The holster and scabbard sway and don't pass through her thighs or back.

## Files

```
Sophia_Unreal.md   §7, §11
Art/sophia_jaqueta_chaos_cloth.md
D:\gurps\issues\047-hair-hangs-rigid.md
```
