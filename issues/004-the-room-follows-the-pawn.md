# 004 — The room follows the pawn instead of an ARCore anchor

**Area:** ar + recon · **Status:** open · **Blocks:** 005, 010, 012

## Context

*Filed 2026-10-23.*

`AReconstructionActor`'s transform maps ARCore tracking space to the Unreal world, and every chunk
actor is attached under it. Today `bFollowPawnOrigin` **copies the player pawn's transform onto it
every tick**. The AR camera is a child of the pawn, and the camera's relative transform is the
tracking pose. The actor's header already says where this goes next: "Later this is where an ARCore
anchor goes."

Why it matters now:

- **ARCore revises tracking space.** When it closes a loop or corrects drift, the anchors move
  with the correction, and content attached to them stays put relative to the room. Content
  attached to the session origin does not. The room is fused in tracking space, so whatever pins
  the root must be what ARCore keeps consistent with the world.
- **Physics and navigation want a root that doesn't move.** A collision body or a navmesh tile
  in world space under a root that is rewritten every tick is either rebuilt every tick or
  wrong (010, 012).
- **Saving needs an anchor to save** (005).

## What to do

- At session start, once tracking is `Tracking`, create an anchor at the tracking origin, or at the
  first good pose. Use Unreal's AR API (`UARBlueprintLibrary::PinComponent` / `UARPin`) if it
  exposes what is needed, or `ArSession_acquireNewAnchor` through the raw pointers
  `UARSessionStarter` already obtains.
- Each tick, set the root's transform from the anchor's pose. Stop when the anchor's tracking state
  isn't `Tracking`.
- Keep `bFollowPawnOrigin` as a fallback switch until the anchor is proven, then delete it.
- The fused field stays in tracking space. The anchor only maps that space to the world.

## The tempting wrong fixes

- **Re-expressing the voxels in anchor space.** OpenChisel integrates in the space the pose is
  given in, and changing that now means converting every pose on the way in, with no gain. The
  anchor is a transform on the root. Nothing else changes, which is what the actor design is for
  (Step 1 of `running_the_reconstruction.md`).
- **One anchor per chunk.** ARCore can correct anchors independently, so the chunks would tear
  apart at their seams, and the TSDF is one rigid field. One anchor, on the root.
- **Leaving the root fixed at identity.** It's the same as following the session origin, which
  is exactly what drifts.

## Done when

- The root's transform comes from an anchor, and `bFollowPawnOrigin` is off.
- Walking around the room and back, the mesh stays registered with the camera feed (003's blend
  view) at least as well as before.
- The log records anchor tracking-state changes.

## Files

```
UnrealWorld/Source/UnrealWorld/ReconstructionActor.h/.cpp   bFollowPawnOrigin, Tick
UnrealWorld/Source/UnrealWorld/ARSessionStarter.h/.cpp      the session and its raw pointers
UnrealWorld/Source/UnrealWorld/ARPawn.h/.cpp
arcore_in_unreal.md
```
