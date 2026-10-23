# 034 — Nothing walks the real room

**Area:** ar + ai · **Status:** open · **Blocked by:** 012, 019 · **Blocks:** 002's room session

## Context

*Filed 2026-10-23.*

The room session's deliverable (002): the phone scans a room, a navmesh is generated on it that
stays put (012), and **something walks on it**. Here the something is a Ratoman (019), using the same
character and controller as the arena, with a `GoTo(point)` behaviour instead of chasing Sophia.
Sophia in the real room is the next milestone.

## What to do

- `RoomGameMode` (from `ReconGameModeBase`), and the Room entry in the front door (033).
- A flow:
  1. **Scan:** the reconstruction runs, the navmesh builds, and a stability indicator from 011
     shows when the walkable area has settled.
  2. **Place:** tap the floor to spawn a Ratoman on the navmesh, then tap again to send him
     somewhere.
- **The room has to hide him.** When he walks behind the sofa, the sofa covers him. The chunks get
  an **occluder material** that writes depth and no colour, so the camera feed shows through and
  hides whatever is behind real geometry. The feed's post process only paints where depth is the
  far plane (Step 10), so check how that interacts with an occluder that writes depth. 003's
  colour material is the debug alternative.
- **His scale.** Life-size (2 m, which barely fits a room) or toy-sized (the ToySoldiers premise).
  Decide, record it in 002, and match the agent settings in 012.

## The tempting wrong fixes

- **Walking him on ARCore planes only.** It works, and it proves nothing about the reconstruction.
  The point is a navmesh from the TSDF, with the furniture as obstacles.
- **No occlusion "for now".** A character drawn over the furniture he is behind reads as a sticker
  on the screen, not as something in the room. Judging the session needs occlusion.

## Done when

- On the Galaxy: scan a room, wait for the indicator, place a Ratoman, and send him across the room
  around a piece of furniture. He walks without falling through or floating, and the furniture
  hides him when he's behind it. A video or screenshots go here.

## Files

```
issues/011 (the indicator), 012 (the navmesh), 019 (the controller), 003 (materials)
UnrealWorld/Source/UnrealWorld/ReconGameModeBase.*, ReconChunkActor.*
UnrealWorld/Content/Materials/M_CameraRGBFeed   the post process the occluder has to work with
```
