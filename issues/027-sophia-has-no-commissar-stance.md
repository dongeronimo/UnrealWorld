# 027 — Sophia has no stance: no ready pose, aim offset or shot

**Area:** anim + tools · **Status:** open · **Blocked by:** 026 · **Blocks:** 038 (`GA_FirePistol`), 029

## Context

*Filed 2026-10-23.*

Her style (`Sophia_Animation_Plan.md`) is the commissar: **pistol in one hand, held almost straight
and fired unsupported; katana low in the other, lowered but ready.** Phase 1 (§6) is the half of the
set that is target-based and procedural. It's "most of what makes her read as a commissar: the
stance and the shot", and it needs nothing from the user except opinions:

| clip | what |
|---|---|
| ready pose | pistol arm almost straight (elbow 10–15°), muzzle on the aim line; katana low, tip near the floor; weight on the back foot |
| ready idle | the pose plus breathing, a small sway and a weight shift, looping |
| aim offset | 9 poses (yaw −90/0/+90 × pitch −45/0/+45): the spine and shoulder share the turn, the arm keeps the muzzle on target |
| fire | an additive recoil: wrist up 8–12°, about 4 frames out and 10 back |
| execution | arm up, a pause, one shot |

All are made in Blender by scripts that solve the poses from targets and measure the error, then
exported through `aplicar_escala.py` and `exportar_unreal.py`.

**Hands.** The plan's §2 says pistol right and katana left. The katana work (2026-10-16) put
`CC_Extra_Katana` under `R_Hand`, so the katana is now in the **right** hand. That puts the pistol in
the left, or makes the katana and the pistol alternate in the right. **Decide before solving any
pose,** and record it in the plan.

## What to do

- Settle the hands question.
- Write the pose solver in `D:\gurps\tools\blender\`. It solves an IK from targets (the muzzle at a
  point, the blade tip at a point, the feet) and bakes plain keys. Its proof is the muzzle
  direction error in degrees.
- Produce the five clips above. Render them from 3 angles for the user's judgement.
- In Unreal:
  - layer the ready pose and ready idle from `spine_01` over 026's locomotion (Layered Blend per
    Bone);
  - add the aim offset on the upper body, and the fire additive in an additive slot;
  - put an `AnimNotify_SendGameplayEvent(Event.Fire.Muzzle)` on the recoil's first frame. The
    fire additive is played by `GA_FirePistol` (038), not by the AnimBP on input.

## The tempting wrong fixes

- **Eyeballing the aim poses.** A muzzle 5° off reads as missing. The muzzle error is measured,
  and "< 1° across the aim offset" is phase 1's done-when.
- **Fire as a full-body clip.** It's additive, so it works while walking and at any aim angle.

## Done when

- Muzzle error is below 1° across the aim offset.
- In Unreal she walks with the ready upper body, aims where the camera points and recoils on fire,
  and the user agrees she reads as a commissar.

## Files

```
Sophia_Animation_Plan.md   §1, §2, §5, §6 (phase 1)
Sophia_Unreal.md           §1 (Weapons: sockets, never children of the hand), §11 (the katana bone)
Art/sophia_soquetes.json
```
