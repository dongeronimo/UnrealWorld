# 012 — No navmesh on the reconstructed room

**Area:** recon + ai · **Status:** open · **Blocked by:** 004, 010, 011 · **Blocks:** 034

## Context

*Filed 2026-10-23.*

The room session of milestone 1 (002) needs a navmesh generated from the real room that **stays
put**. ToySoldiers died here. Its later GDD (`D:\ToySoldiers\docs\GDD.md` §10) gave up on navmesh
for an A* grid sampled from the field, after the navmesh never converged. This card tries again,
with three things ToySoldiers didn't have:
- an anchor-pinned root (004);
- collision on the chunks (010);
- a measured stability threshold (011).

Navigation registers per component. ToySoldiers calls `FNavigationSystem::UpdateComponentData(*this)`
per chunk component. Chunks as child actors work the same way (Step 1 of
`running_the_reconstruction.md`).

## What to do

- **Recast with runtime generation set to Dynamic**, tiled. Choose the tile size against the chunk
  size (64 cm): the same size or a multiple, so one chunk's change dirties one tile or a few.
- **Nav-relevance comes from 011's stable layer, not from every remesh.** A chunk tells the
  navigation system that it changed only when it crosses the stability threshold that 011 sets.
  That one rule is the difference from ToySoldiers.
- **Agent size.** Pick the agent's radius, height and step height for the characters' scale in
  the room. That scale is a design decision (002) that isn't made yet: life-size or toy-sized.
  Record it here when it's made. Recast's cell size has to resolve it: a toy-sized agent in a
  real room needs cells of about 2–5 cm, and that cost grows fast.
- **Measure on the device:** tile rebuilds per minute, rebuild time per tile, and memory.
- Use the navmesh debug draw (`show Navigation`) and a log line of rebuilds per second, to see
  stability on screen.

## The tempting wrong fixes

- **Marking every chunk nav-relevant and letting Recast rebuild on every change.** That is the
  ToySoldiers failure, reproduced on purpose.
- **A static navmesh baked once after the scan.** It doesn't survive a moved chair, and baking in
  the editor isn't possible for a room that exists only at runtime.
- **Lowering the rebuild frequency with a timer and calling it stable.** A timer hides churn; it
  doesn't remove it. A tile that is wrong every time it rebuilds is wrong.
- **Navigation invokers around the player only.** They limit *where* tiles are built, not *how
  often* they change. Useful later, for a large room, but not the fix.

## Done when

- A navmesh is generated on a live scan on the phone, and is visible with `show Navigation`.
- After the scan stops, tile rebuilds fall below 011's threshold within the stated time, and the
  numbers are recorded here.
- The same works on a replay (006) in the fixture.

## Files

```
UnrealWorld/Source/UnrealWorld/ReconChunkActor.h/.cpp     nav relevance
UnrealWorld/Source/UnrealWorld/ReconstructionActor.h/.cpp
UnrealWorld/Config/DefaultEngine.ini                      RecastNavMesh settings
D:\ToySoldiers\docs\GDD.md                                §10: why ToySoldiers gave up on navmesh
```
