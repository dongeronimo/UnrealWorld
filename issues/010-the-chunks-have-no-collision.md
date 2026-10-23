# 010 — The chunks have no collision

**Area:** recon + physics · **Status:** open · **Blocked by:** 004 (on the phone; the fixture can start now) · **Blocks:** 012, 034

## Context

*Filed 2026-10-23.*

`AReconChunkActor`'s `URealtimeMeshComponent` is created with no collision and no shadows. The
fixture pawn (`AFixturePawn`) was made collision-free on purpose, "once the chunks collide", so
looking at the room from outside stays possible. The navmesh (012) and anything that walks (034)
need the room to be solid.

ToySoldiers' notes (`D:\ToySoldiers\drafts\_articles\the-room-on-screen.md`) end with "collision:
never measured, and the item the whole port is gated on". The question is not whether Unreal can
collide with a mesh. **The question is the cost of re-cooking a collision mesh every time a chunk
is remeshed, on a phone.**

## What to do

- Turn on RealtimeMesh's complex collision for the chunk section groups, as triangle-mesh
  collision. It's cooked asynchronously, and RMC supports it.
- **Measure on the device, during a scan:**
  - cook time per chunk;
  - cooks per second;
  - the game-thread cost.

  Remesh runs at up to 8 chunks per tick (`RemeshBudgetPerTick`), so a careless setup cooks up to
  240 meshes a second.
- If the cost is too high, decouple collision from rendering. A chunk's collision updates only
  when its render mesh has been stable for N seconds, or at most once every M seconds. The render
  mesh stays live.
- The object channel is `WorldStatic`, and `CanCharacterStepUpOn` is yes.
- The fixture pawn stays collision-free. Use a test actor (a falling sphere, a capsule walked by
  hand) to prove it.

## The tempting wrong fixes

- **Simple collision (boxes or convex hulls) per chunk.** A 64 cm chunk with a floor and a table
  leg is badly approximated by a hull, and characters float over the gaps.
- **Cooking collision synchronously on the game thread.** That's a dropped frame per remesh.
- **Measuring on the desktop and calling it done.** The question is the phone.
- **Colliding with the TSDF directly** (sphere-casting into the field). It's possible, but
  nothing in Unreal (CharacterMovement, Recast, traces) would use it. That would be a different
  game architecture, and not this card's choice.

## Done when

- A physics capsule dropped in the fixture lands on `room1`'s floor and stops against a wall.
- On the phone, the cook statistics during a 60 s scan are recorded here, with frame times. The
  card records whether decoupling was needed.

## Files

```
UnrealWorld/Source/UnrealWorld/ReconChunkActor.h/.cpp
UnrealWorld/Source/UnrealWorld/FixturePawn.h/.cpp        stays collision-free
UnrealWorld/Plugins/RealtimeMeshComponent/              collision on section groups
D:\ToySoldiers\drafts\_articles\the-room-on-screen.md   the unmeasured gate
```
