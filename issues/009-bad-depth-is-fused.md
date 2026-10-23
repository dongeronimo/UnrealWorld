# 009 — Bad depth is fused: motion blur, grazing angles and flying pixels go in at full weight

**Area:** recon · **Status:** open · **Blocked by:** 006 · **Blocks:** 011

## Context

*Filed 2026-10-23.*

The only per-sample filters today are:
- zero depth;
- the near and far planes (0.3 and 3 m);
- the confidence threshold and curve (007).

Three kinds of bad sample pass all of them, and the "What's next" list in
`running_the_reconstruction.md` names two of them:

- **Motion blur.** When the phone turns fast, ARCore's depth-from-motion and the pose disagree.
  The whole frame lands slightly rotated, and with carving on it also carves the real surface.
  It is per frame, not per pixel, so the confidence map doesn't reliably catch it.
- **Grazing angles.** A surface seen nearly edge-on spreads one depth sample's error along the
  surface. σ grows with the angle (Nguyen's θ term, 008). Floors seen from a standing phone are
  exactly this: the walkable surface the navmesh needs is the one seen at the worst angle.
- **Flying pixels.** At depth discontinuities, such as a table edge against the floor behind
  it, samples land in the empty space between the two surfaces. They create floating crumbs that
  carving then fights.

## What to do

Each filter is a weight multiplier, not a rejection, where it can be. That's the same lesson as the
confidence threshold.

- **Motion.** Angular and linear speed from consecutive sensor poses (a pose is already in every
  frame). Above a threshold, skip the frame. Between a soft and a hard threshold, scale its weight
  down. Log how many frames were skipped, beside "repeated depth".
- **Grazing.**
  - A normal per sample, from the depth image's gradient (central differences on the back-projected
    points).
  - Weight × cos θ, or `1/σ²(z, θ)` once 008 has θ.
  - It is computed in the same pass that writes the weight image, so it costs one pass over a
    small image.
- **Edges.** Drop or downweight a sample whose neighbour's depth differs by more than k·z (start
  with k ≈ 0.05).
- Each filter has its own on/off switch, set through console variables or config like 007's, so
  replays can isolate it.

## The tempting wrong fixes

- **A hard rejection for each.** Every hard threshold so far has eaten the floor. Grazing
  rejection in particular deletes the floor first, because it's always at a grazing angle from a
  standing phone.
- **Smoothing the depth image (bilateral, median) before fusion.** A median across an edge
  invents mid-depth samples, which is the flying-pixel problem created on purpose. The TSDF
  already averages, and it does so along the right axis.
- **Turning carving off to stop blur from carving real surfaces.** It moves the problem: blurred
  samples then add phantom surfaces that nothing removes. Fix the samples.

## Done when

- The three filters exist, can be switched separately, and their counts are in the stats log line.
- On a replay with deliberate fast turns, 011's metrics are recorded with each filter off and on.

## Files

```
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/Private/TsdfReconstruction.cpp   the per-pixel pass
UnrealWorld/Source/UnrealWorld/ReconstructionActor.cpp   HandleFrame, the per-frame decisions, the log
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/openchisel/OPENCHISEL-README.md  §4 (why weights, not filters), §6 (carving)
```
