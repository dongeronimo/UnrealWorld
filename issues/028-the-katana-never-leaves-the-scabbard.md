# 028 — The katana never leaves the scabbard: the draw, sheathe and combo clips are in Blender only

**Area:** anim + content · **Status:** open · **Blocked by:** 020, 026 · **Blocks:** 038 (`GA_KatanaCombo`, draw and sheathe), 029

## Context

*Filed 2026-10-23.*

The katana work is the newest thing on Sophia (2026-10-16, `Sophia_Unreal.md` §11):
- **The scabbard is on her back.** `CC_Extra_Scabbard` is a child of `Spine02`, because the
  Grruzam clips draw over the right shoulder.
- **The katana in hand rides the weapon bone `CC_Extra_Katana`** (a child of `R_Hand`, no
  weights), which every Grruzam clip keys. Its socket is `katana_mao` in `Art/sophia_soquetes.json`.
- `katana_intro` swaps from the scabbard socket to `CC_Extra_Katana` at **frame 5**.
- `katana_embainhar` (Grruzam's `Idle_B_to_A`, which actually sheathes) swaps back to the scabbard
  at **frame 30**.
- The Blender curve `katana_na_mao` in each action marks the in-hand frames.
- The clips come from `D:\gurps\tools\blender\retarget_biped.py`, not from Unreal retargeting.
- There are attack blends in `Art/`: `sophia_katana_Attacks_3Combos`, `_4Combos`, `_5Combos`.

The rule (user, 2026-10-16): **weapons are never children of the hand.** They are static meshes
attached by code, and notifies swap the socket.

## What to do

- Export and import `katana_intro`, `katana_embainhar` and the combo clips. Strip the face-bone
  tracks (025).
- Add the sockets on her skeleton: the scabbard socket, and `katana_mao` on `CC_Extra_Katana`, from
  the JSON. Check each with the katana as the socket's preview mesh, because Unreal's bone axes can
  differ from Blender's.
- An `AnimNotify_SwapSocket(Weapon, Socket)` notify, placed at frame 5 of the intro and frame 30 of
  the sheathe. Cross-check them against the `katana_na_mao` curve, exported as an anim curve. The
  swap is cosmetic. The gameplay state, `State.Katana.Drawn`, is a tag that `GA_DrawKatana` and
  `GA_SheatheKatana` (038) set on the same frame via a gameplay event.
- Combos as one montage with a section per cut. Each cut carries
  `AnimNotify_SendGameplayEvent` notifies:
  - `Event.Melee.HitWindow.Open` and `.Close`, for the sweep;
  - `Event.Melee.ComboWindow`, for when the next input chains.

  The chaining and the sweep themselves are `GA_KatanaCombo`'s (038). This card delivers the
  montage and its events.
- Draw and sheathe as upper-body montages, so she can walk while drawing.

## The tempting wrong fixes

- **Parenting the katana mesh to the hand bone.** It breaks the moment a clip keys `CC_Extra_Katana`
  away from the hand, and it breaks the scabbard pose. That's the reason the weapon bone exists.
- **Retargeting the Grruzam clips in Unreal.** They were retargeted in Blender for a reason that's
  recorded in §11. Doing it again in Unreal duplicates the work and loses the weapon bone's keys.
- **Hit detection from the katana's collision every frame.** Use the swing windows, or the
  sheathed katana hits Ratomen from her back.

## Done when

- She draws over her shoulder (the katana leaves the scabbard at frame 5), runs a 3-hit combo with
  the notifies logging, and sheathes it back at frame 30, with no visible jump at either swap.

## Files

```
Sophia_Unreal.md   §1 (Weapons), §11 (Katana)
Art/sophia_katana_clips.blend, Art/sophia_katana_Attacks_*Combos.blend, Art/sophia_soquetes.json
D:\gurps\tools\blender\retarget_biped.py
```
