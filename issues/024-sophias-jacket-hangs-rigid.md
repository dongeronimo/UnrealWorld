# 024 — Sophia's jacket hangs rigid: the cloth masks are painted, but nothing simulates them

**Area:** art + physics · **Status:** open · **Blocked by:** 020, 023

## Context

*Filed 2026-10-23.*

The jacket carries its cloth setup from Blender:
- the colour attribute `Cloth_Mask` (bright front panels, black sleeves);
- the vertex group `Cloth_MaxDistance`.

`Sophia_Unreal.md` §8:
- Chaos Cloth on the **front panels and the hem only**, with self-collision **off**. The sleeves
  aren't cloth, and self-collision is Chaos's most expensive part.
- The panel-against-sleeve problem is solved by 023's thick arm capsules.
- The skirt hem is optional, with the same recipe.
- If Chaos is too heavy on the phone, use **Kawaii Physics** on bone chains in the panels
  (`rig_saias.py` has a chain mode).

The starting values and the reasons are in `Art/sophia_jaqueta_chaos_cloth.md`.

**Known limit (§11): the front panel crosses its own sleeve in some poses.** That is left to the
cloth and the thick capsules.

## What to do

- Paint the Max Distance from `Cloth_MaxDistance` in the Clothing tool, with the notes' values.
- Collide with 023's physics asset.
- **Measure on the phone:** the jacket alone, then Sophia plus five Ratomen. If the cost is too
  high for the arena, switch to the Kawaii chain mode. That needs a Blender pass with `rig_saias.py`
  and a re-export (020).
- The skirt hem stays rigid unless the jacket is cheap enough.

## The tempting wrong fixes

- **Self-collision on to stop the panel crossing the sleeve.** The sleeve isn't cloth, so
  self-collision doesn't see it. The capsules do.
- **Simulating the whole jacket.** The sleeves are skinned and should stay skinned. Only the panels
  and the hem hang free.
- **Deciding Chaos against Kawaii on the desktop.** It's a phone budget question.

## Done when

- The front panels and the hem swing in a run and a turn, and stay outside the shirt and the
  sleeves in the common poses.
- The phone's cost is recorded here, along with which solver was kept.

## Files

```
Sophia_Unreal.md   §8, §11
Art/sophia_jaqueta_chaos_cloth.md
D:\gurps\tools\blender\rig_saias.py   (the Kawaii fallback)
```
