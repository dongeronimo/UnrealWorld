# 011 — Nobody knows whether the surface settles: no metric for how much the mesh keeps changing

**Area:** recon + tools · **Status:** open · **Blocked by:** 006 · **Blocks:** 012 · **Informs:** 007, 008, 009

## Context

*Filed 2026-10-23.*

ToySoldiers failed because its navmesh never converged to something stable and rarely changed,
since the mesh under it never stopped changing (user, 2026-10-23). The suspects:
- the weighting function (007, 008);
- the Galaxy S series' depth;
- **carving competing with accumulation.**

The last one is a contradiction built into TSDF reconstruction. Carving exists so the field can
forget (noise, a person walking by: the paper's §III-E). Accumulation exists so the field can
remember and settle. Both act on the same voxels near the surface, and with noisy depth the
surface's own samples carve the surface.

Today's knobs on that tension:

| knob | value | what it does |
|---|---|---|
| `MaxWeight` | 200 | a voxel's weight is capped, so it stays correctable |
| `CarvingDecay` | 0.85 | weight × 0.85 per carving observation |
| `CarvingMinWeight` | 0.5 | below this, the voxel resets to unobserved |
| `CarvingDistance` | 5 cm | the dead zone above the band before carving starts |
| `CarvingRate` | 2.0 | |

Fork change §6 in `OPENCHISEL-README.md` is the carving rebuild.

**None of this has a number attached that says "stable".** The stats log counts work (integrated,
meshed, awaiting remesh). It doesn't count change. This card creates the measurement that every
other reconstruction card is judged by, and that the navmesh (012) is gated on.

## What to do

**Metrics, per second, logged and written by 006's batch replay:**
- **Sign flips:** voxels whose SDF changed sign, which is the zero crossing moving. Report them
  in total, and restricted to chunks the camera **wasn't** looking at, which should be zero by
  construction.
- **Surface churn:** chunks remeshed whose triangles actually changed, against those remeshed
  with the same result.
- **Walkable churn:** the same, restricted to chunks with an upward-facing surface below head
  height, which is what the navmesh will see.
- **Carving pressure:** the number of voxels decayed by carving, and the number reset to
  unobserved.

**The test that matters.** Record (006) a scan of a static room, then **30 s of the phone held
still or slowly panning over the already-scanned area**. A settled reconstruction drives walkable
churn towards 0 in those 30 s. Plot the metrics over time for:
- today's config;
- carving off;
- several `MaxWeight` values;
- 007's functions;
- 008's dynamic truncation;
- 009's filters.

**Candidate mechanisms to try, not a verdict:**
- **Hysteresis on the surface.** A voxel's sign flips only after k consecutive contrary
  observations, or only when the new evidence's weight exceeds the stored weight by a margin.
- **Carving that respects confidence.** A voxel above a weight W carves only from samples
  well outside the band, and never from samples whose own band overlaps it.
- **A separate, stable layer for gameplay.** The render mesh stays live. Collision and the navmesh
  read a layer that updates a chunk only when its surface has changed by more than a tolerance
  (Hausdorff or height-map difference) and has been stable for N seconds. This is the natural home
  of 010's decoupling.
- **ARCore planes for the floor.** Plane detection is temporally filtered by ARCore and very
  stable. The walkable base can come from the plane, and only the obstacles from the TSDF.

## The tempting wrong fixes

- **Carving off.** Churn drops, and the room fills with permanent phantom geometry from every
  blurred frame and every passer-by. The metric must be read together with a look at the result.
- **`MaxWeight` unbounded.** It settles by becoming impossible to correct: a chair moved after
  the scan stays in the old place forever. That is the bug that `MaxWeight` was added to prevent.
- **Measuring stability by eye.** "Looks stable" is what ToySoldiers had. The number is the
  deliverable.

## Done when

- The metrics are in the stats log line and in the batch replay's output.
- The static-room test has been run on at least three configs, and the plots are attached here.
- **A stability threshold for 012 is written into this card.** For example: walkable churn below
  X chunks per minute after Y seconds of no new area. It is chosen from those plots.

## Files

```
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/Private/TsdfReconstruction.cpp   Remesh, FTsdfStats
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/Public/TsdfReconstruction.h      FTsdfConfig carving fields
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/openchisel/OPENCHISEL-README.md  §6 carving
UnrealWorld/Source/UnrealWorld/ReconstructionActor.cpp   LogStats
klingensmith2015chisel.pdf   §III-E
```
