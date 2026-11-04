# 043 — Sophia's wounds never show: the HP wound layer is in Blender only

**Area:** art + render + gameplay · **Status:** open · **Blocked by:** 020 (the material half), 030 (the Health half) · **Blocks:** —

## Context

*Filed 2026-10-27.*

She takes damage in stages. One material scalar, `HP` (0..1), reveals a pre-made "0 HP" layer of
bruises, scrapes, cuts and blood. Each wound grows from its centre as HP drops. The textures, the
material maths and the pacing are done and checked in Blender (EEVEE).
`Art/sophia_feridas_UNREAL.md` has everything:

- `feridas/Sophia_Feridas_Tint.png`: a multiply tint;
- `feridas/Sophia_Feridas_Mask.png`: R reveal, G wetness, B height;
- `feridas/Sophia_Feridas_Normal.png`: OpenGL normals;
- the node list for `M_Sophia_Body`, and how to drive it from health.

Nothing of it is in Unreal yet. It has two halves:
1. **The material.** It needs only the imported body (020), and can be checked by scrubbing `HP`
   by hand.
2. **The driver.** `HP` follows the `Health` attribute (037, 030). The wounded run and the pained
   face switch at the same thresholds, so the material, the animation and the face agree.

## What to do

**Material half (after 020; it lives in the same `M_Sophia_Body` as 022's masks):**
- Import the three textures with the doc's table: Tint sRGB on and BC7; Mask sRGB **off** and BC7;
  Normal as Normalmap with **Flip Green Channel**. Mips on, UV 0.
- Add the doc's nodes to `M_Sophia_Body`: `HP` (default 1), `WoundSoft` (0.06),
  `vis = saturate((mask.r − HP) / Soft)`, then BaseColor, Roughness and Normal through `vis`.
- Check by scrubbing `HP` in a material instance: 0.85, 0.7, 0.55, 0.4, 0.25, 0.15, 0. Compare
  with `feridas/preview/montagem_*.png`.

**Driver half (after 030):**
- `ASophiaCharacter` makes the body slot's Dynamic Material Instance at BeginPlay (the same DMI
  022's `Wear` uses).
- It binds to Health with `ASC->GetGameplayAttributeValueChangeDelegate(Health)` (checked in 5.7's
  `AbilitySystemComponent.h`). The target is `Health / MaxHealth`, and the shown `HP` eases toward
  it over 0.3–0.5 s.
- The wounded run (`Movements_Run_Injured`, imported in 044) and the pained face baseline (025)
  read the same value with the same thresholds. Put the thresholds in one place on `BP_Sophia`.
- Healing runs it back up. The wounds close in reverse order with no extra work.

## The tempting wrong fixes

- **A second "0 HP" body texture lerped in.** It needs one copy per body alt. The multiply tint
  works on every alt unchanged (the doc, "Why it is built this way").
- **Setting `HP` from the damage event.** Then healing, regeneration and a respawn each need
  their own path. The attribute is the source (037). Listen to it.
- **Snapping `HP`.** The wounds pop on. Ease it.
- **Wounds per hit location.** That's out of scope by design. Every fight shows the same wounds in
  the same order (the doc's "Known limits").

## Watch for

- **The mobile path.** It adds three samples on top of the base colour and the mask WPO. Check the
  body's shader cost on the Galaxy along with 022's test.
- **The split lip and nosebleed under expressions** (025) were checked on the neutral face only.

## Done when

- Scrubbing `HP` in the editor matches the Blender contact sheets at the six thresholds.
- In play, each Ratoman hit makes her wounds bloom in over about half a second. At low health she
  runs injured and her face is pained, and all three change at the same HP.
- A phone screenshot at HP 0.25 goes here.

## Files

```
Art/sophia_feridas_UNREAL.md          the whole recipe
Art/feridas/                          the three textures and the previews
Sophia_Unreal.md                      §2 (material map: M_Sophia_Body)
issues/022 (same material), 030 (Health changes), 025 (the face), 044 (the injured run)
```
