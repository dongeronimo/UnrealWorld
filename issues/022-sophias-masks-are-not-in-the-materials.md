# 022 — Sophia's body and shirt masks aren't in the materials: skin shows through what she wears

**Area:** art + render · **Status:** open · **Blocked by:** 020 · **Blocks:** 029 (equipment that can come on and off)

## Context

*Filed 2026-10-23.*

The garments are worn over the full body mesh. Where a piece is worn, the body's skin under it has
to disappear, or it pokes through in every pose. The method is the same as in gurps (card 019):
- the vertices to hide are marked in a mask texture addressed by **UV 1**, one texel per vertex;
- a vertex shader returns a **NaN offset** for a hidden vertex whose slot is worn;
- that drops every triangle touching it, in every pass including the shadows.

The textures:
- **`Art/sophia_masks/masks_rgba.png`** is the body mask, 128×128: R arms (the jacket), G chest
  (the shirt), B hips (the skirt), A legs (the boots).
- **`Art/sophia_shirt_masks/masks_rgba.png`** is the shirt mask, 64×64: R means the jacket hides
  the shirt.

The full recipe and the HLSL are in `Art/sophia_jaqueta_chaos_cloth.md`, under "Body masks" and
"Shirt mask".

## What to do

- Import the mask textures uncompressed: sRGB off, VectorDisplacementmap (RGBA8), Nearest,
  NoMipmaps, Never Stream (`Sophia_Unreal.md` §2).
- A Custom node on **World Position Offset**: `SampleLevel(…, UV1, 0)`. A NaN where `mask & Wear`.
- `Wear` is a float4 vector parameter (arms, chest, hips, legs) on **both** the body and the shirt
  material instances. A small C++ or BP helper sets both whenever a piece goes on or off.
- Keep **WPO Disable Distance = 0** and **Max WPO Displacement = 0**.
- Test **on the phone**. Mobile has no TSR, VSM or Lumen, but the NaN trick must survive the mobile
  renderer and its shadow pass. The Masked-material fallback is in the notes, if it doesn't.

## The tempting wrong fixes

- **Cutting the body mesh into regions.** It was measured and discarded in gurps (045 §2): seams,
  normals and correctives all break at the cuts.
- **Compressing the masks.** BC compression bleeds between neighbouring texels, which are
  neighbouring vertices here, and that hides the wrong ones.
- **Proving it on the desktop only.** gurps 019's rule: a desktop proof proves nothing about the
  phone.

## Watch for

- **The hips mask hides the crotch.** Taking the panty off while the skirt is on shows a hole
  (`Sophia_Unreal.md` §11). Treat panty and skirt as one slot until a mask is split.

## Done when

- With every piece worn, no skin pokes through in the dance, a crouch or a run. Taking each piece
  off brings back the skin under it only.
- The same holds on the Galaxy, shadows included. A screenshot of the phone goes here.

## Files

```
Sophia_Unreal.md   §2 (textures), §4, §11
Art/sophia_jaqueta_chaos_cloth.md   the HLSL and the decisions
Art/sophia_masks/, Art/sophia_shirt_masks/
D:\gurps\issues\019-skeleton-and-mask-shader.md
```
