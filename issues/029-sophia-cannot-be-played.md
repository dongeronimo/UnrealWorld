# 029 — Sophia can't be played: no character, controls or camera on the phone

**Area:** gameplay + anim · **Status:** open · **Blocked by:** 021, 026, 027, 028, 037, 038 · **Blocks:** 031, 032

## Context

*Filed 2026-10-23.*

Cards 020–028 produce a Sophia who moves well. This card makes her **the player** in the arena, on a
phone. It is the integration card, where phase 4 of `Sophia_Animation_Plan.md` ("a full loop: draw,
aim, fire, cut, sheathe") meets input.

## What to do

- `ASophiaCharacter : ACharacter` (Abstract, C++). `BP_Sophia` sets the mesh, `ABP_Sophia`, the
  weapon meshes, the tuning and her ability set (`AS_Sophia`), following the project's
  blueprint-set-assets pattern. Her AbilitySystemComponent lives on the PlayerState, with her as
  the avatar (037).
- The weapons are static mesh components attached to sockets and swapped by 028's notifies,
  never children of the hand.
- **Camera:** third person over the shoulder, on a spring arm with collision.
- **Touch controls** (Enhanced Input with a touch interface). Every fight button activates an
  ability through 037's input-tag map. Nothing calls a montage or a trace directly from input:
  - left stick to move, and drag on the right half to look and aim;
  - buttons for fire, katana attack (tap to chain the combo), draw/sheathe, and dodge if it's
    cheap.
  - Keyboard and mouse for PIE.
- `ABP_Sophia` complete, with the order from `Sophia_Animation_Plan.md` §5:
  1. locomotion;
  2. the upper body ready layer from `spine_01`;
  3. the aim offset;
  4. the fire additive;
  5. montages (combo, draw/sheathe, hit react);
  6. the face (025);
  7. correctives and twist last, as the post-process ABP (021).
- **The AnimBP reads GAS state.** `State.Katana.Drawn` picks the upper-body pose set, and
  `State.Stunned` and `State.Dead` gate locomotion. Read the tags through the ASC (a gameplay tag
  property map on the AnimInstance), not through bools copied onto the character.

## The tempting wrong fixes

- **Aiming from the camera's centre and ignoring the muzzle.** It looks fine until there's cover
  between the muzzle and the target. Trace from the camera to find the aim point, then from the
  muzzle to it.
- **Building the touch UI in code.** Use a UMG widget with an Enhanced Input touch mapping, so it
  can be laid out for real phone sizes.

## Done when

- On the Galaxy, in a test level, she runs, aims, shoots, draws the katana, runs a combo and
  sheathes, all from touch, at a stable frame rate. The frame time is recorded here.

## Files

```
Sophia_Animation_Plan.md   §5, §6 (phase 4)
Sophia_Unreal.md           §9, §10
UnrealWorld/Source/UnrealWorld/   ASophiaCharacter (new)
```
