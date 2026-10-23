# 017 — Ratoman's physics asset is the auto-generated one

**Area:** anim + physics · **Status:** open · **Blocks:** 016 (its capsules), 030 (hit detection on his body), ragdoll on death

## Context

*Filed 2026-10-23.*

`Ratoman_Brute_PhysicsAsset` came from the import. `Ratoman_Brute_Unreal.md` §1 says to delete it,
and §7 says to rebuild it: the default puts a body on every twist and finger bone. The arena needs
him to be **hit** (030: sword traces and pistol line traces against his bodies) and to **fall**
(a ragdoll, or at least a physics-blended death).

## What to do

- Delete the import's asset. Create one with a minimum bone size of 8–10 cm, using capsules.
- **Keep:** Hip, Waist/Spine, Head, upper arm, forearm, hand, thigh, calf and foot.
- **Delete** whatever is left on the twist bones, fingers, toes, jaw, whiskers and ear ring.
- **Tail:** 3–4 small capsules along it, or none, if Kawaii (016) carries its own. Decide with 016.
- Give each body a physical material, and name the head body, because 030 may want headshots.
- Constraint limits that keep a ragdoll from folding the knees backwards.
- Assign it to the mesh, and set the collision profile so traces on the `Pawn` / weapon channel hit
  the bodies.

## The tempting wrong fixes

- **Keeping the import's asset and deleting bodies until it looks fine.** The bodies were sized
  for the wrong bone list, so rebuild it.
- **A body per tail bone.** That's ten unstable small bodies in a ragdoll.

## Done when

- The asset has the listed bodies only, and a ragdoll test (Simulate in the physics asset editor)
  collapses him plausibly.
- A line trace from a test actor reports the bone it hit.

## Files

```
Ratoman_Brute_Unreal.md   §1, §7
UnrealWorld/Content/Chars/RatomanBrute/Ratoman_Brute_PhysicsAsset
```
