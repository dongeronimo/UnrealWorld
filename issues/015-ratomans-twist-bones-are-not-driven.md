# 015 — Ratoman's twist bones are not driven: candy-wrapper wrists on every retargeted clip

**Area:** anim · **Status:** open · **Blocks:** 016 (it adds to the same post-process ABP), 018 looking right

## Context

*Filed 2026-10-23.*

The skin of his arms and legs is weighted across `UpperarmTwist01/02`, `ForearmTwist01/02`,
`ThighTwist01/02` and `CalfTwist01/02`. Nothing animates them. Clips from other skeletons leave them
in the reference pose, so the skin twists all at once at one point: a candy-wrapper wrist, or a
fold at the hip. Section 2 of `Ratoman_Brute_Unreal.md` already notes that the forearms and thighs
look stiff in the dance.

§5 of the guide is the recipe. Its key point is that there are two kinds of twist bone:

- **The upper arm and the thigh counter-twist.** The twist bones are children of the bone that
  rotates and inherit all of its twist, so Twist01 gets −0.8 × and Twist02 +0.6 × the driver's local
  twist.
- **The forearm and the calf spread the child's twist.** They are siblings of the hand and foot and
  inherit none of it, so Twist01 gets +0.25 × and Twist02 +0.5 × the hand's or foot's twist.

## What to do

- `CR_Ratoman_Twist`, a plain Control Rig, Forwards Solve only.
  - One function, `DistributeTwist(Driver, Twist01, Twist02, F01, F02, Axis)`: To Swing & Twist,
    then To Axis And Angle, then Set Rotation Local.
  - Eight calls, using §5's table.
- Find the twist axis on `CC_Base_L_Forearm` first. It's probably Y from a Blender export. If the
  twist comes out as a bend, the axis is wrong.
- `ABP_Ratoman_Post`: `Input Pose → Control Rig → Output`. Set it as the skeletal mesh's **Post
  Process Anim Blueprint**, so every clip gets it.

## The tempting wrong fixes

- **The built-in Twist Bones node.** It spreads the twist of a chain's end along that chain. The
  CC twist bones are siblings, and the upper ones must counter-twist.
- **The dual-quaternion deformer instead.** It changes how all of his skin deforms, and his
  weights were tuned for linear skinning. Try it later as a comparison.
- **Mapping them in the retargeter** (see 014).

## Watch for

- The angle out of To Axis And Angle can come back as 0..360° with a flipped axis. Normalise it to
  −180..180 before multiplying, or a twist bone snaps 180°.

## Done when

- In the Control Rig preview, turning a palm rolls the forearm gradually instead of pinching at the
  wrist, and the hip has a soft crease instead of a fold.
- The dance and a retargeted walk play through `ABP_Ratoman_Post` with no candy-wrapping. Before
  and after screenshots go here.

## Files

```
Ratoman_Brute_Unreal.md   §4, §5, §9
UnrealWorld/Content/Chars/RatomanBrute/
```
