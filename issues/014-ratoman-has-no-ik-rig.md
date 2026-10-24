# 014 — Ratoman has no IK Rig, so no animation from another skeleton can reach him

**Area:** anim · **Status:** done (2026-10-23) · **Blocks:** 018

## Context

*Filed 2026-10-23.*

He has the 101-bone CC_Base skeleton plus 14 extras: the tail (10), the ears (2) and the whiskers (2).
Every clip he needs for the arena (018) comes from somewhere else: the Game Animation Sample or Lyra
(Manny), or Mixamo. That means an IK Rig on him and an IK Retargeter from each source.
`Ratoman_Brute_Unreal.md` §3 has the full recipe for UE 5.7. In 5.6 and 5.7 the Retargeter became an
op stack: Pelvis Motion, FK Chains, IK Chains, Root Motion, plus Copy Base Pose, Stretch Chains and
Pole Vector Alignment.

## What to do

- `IK_Ratoman`:
  - retarget pelvis `CC_Base_Hip`;
  - the chains from §3's table (Spine `Waist→Spine02`, Neck, Head, the clavicles, the arms
    `Upperarm→Hand`, the legs `Thigh→Foot`, the fingers);
  - foot and hand IK goals.
- **Leave unmapped:** the twist bones (015), `CC_Base_Pelvis`, the tail, ears, whiskers and jaw.
  Unmap by hand whatever the fuzzy auto-map matched to them.
- `RTG_Manny_to_Ratoman`, with Add Default Ops.
  - His reference pose is an A-pose with long arms and claws. Use Auto Align on the arms against
    Manny's A-pose.
  - Rotate `CC_Base_Head` a few degrees in his retarget pose if the head looks at the floor.
    He's 2.0 m tall and hunched.
  - Use the 5.7 crotch-height setting and the floor constraint if the pelvis sinks.
- Export one GAS walk and one jog to his skeleton as a check.

## The tempting wrong fixes

- **Mapping the twist bones in the retargeter.** It copies only what the source animates, and the
  distribution was tuned for another body. 015 drives them from the main bones.
- **Mapping the tail to Manny's spine or anything else.** It has its own motion (016).
- **Accepting the auto-chains as they come.** Fuzzy mapping matches `Tail`, `Twist` and `Ear` to
  something on the source.

## Done when

- A GAS walk and jog play on him with planted feet, the claws clear of the thighs, and the head
  looking forward.
- The IK Rig and the Retargeter are saved under `Content/Chars/RatomanBrute/`.

## Files

```
Ratoman_Brute_Unreal.md   §3
UnrealWorld/Content/Chars/RatomanBrute/
```

- Created IK_RatomanBrute.
- Mapped the chains according to AccuRig_Skeleton.md.
- Third person template imported to get Manny
- RTG_Manny_to_Ratoman: most manny anims worked fine at first attempt. Pistol and rifle will need some fixing but we can use the tooling at d:\gurps that converted Grruzam katana anims to the accurig skeleton in blender.
- Export one GAS walk and one jog to his skeleton as a check : no need. I don't know which anims i'll need and i'll export on an as-needed basis. SSD aint cheap.