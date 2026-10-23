# 007 — One weighting function is hardcoded: the confidence curve and the weight along the ray can't be switched

**Area:** recon · **Status:** open · **Blocked by:** 006 (to compare; switching itself doesn't need it) · **Blocks:** 008, 011

## Context

*Filed 2026-10-23.*

Two different weights reach a voxel, and today each is fixed:

**A. Per sample, from ARCore's confidence.** This is in `TsdfReconstruction.cpp`, around the
`SetWeights` image.
- Below `ConfidenceThreshold` (32) the sample is dropped.
- Above it: `w = Floor + (1 − Floor) · tᵉ`, with `t = (conf − threshold) / span`, `Floor = 0.05`
  and `e = 2`.

The point of a curve rather than a threshold is recorded in fork change §4 of
`OPENCHISEL-README.md`. At Google's recommended threshold of 128, 79% of the samples were rejected
and a tiled floor came back as islands.

**B. Per voxel, along the ray, as a function of the signed distance to the hit, `u ∈ [−τ, τ]`.**
The paper (Klingensmith et al. 2015, §III-B, `klingensmith2015chisel.pdf` in the root) says this
directly. The weighting function α(u) can be computed from the sensor's hit probability, "but in
favor of better performance, linear, exponential, and constant approximations of α can be used. We
use the constant approximation α(u) = 1/(2τ). This results in poorer surface reconstruction quality
in areas of high noise."
- The fork's `chisel::Weighter` is exactly that constant: `weight / (2τ)`.
- Its comment notes that `surfaceDist` "is accepted and ignored … the hook for a signed weighting
  profile", left unused so that turning it on is a change to that function and nothing else.

The user wants to **switch between functions** on both axes, and compare them (on 006's
replays).

## What to do

**A, the confidence curve, as a 256-entry table.** Confidence is a `uint8`, so a 256-float table
represents *any* function of it exactly, and the inner loop becomes one array read in place of the
`pow`.

The shapes build the table:

| name | w(t), t ∈ [0,1] above the threshold |
|---|---|
| `step` | 1, which is a plain threshold, the baseline |
| `linear` | Floor + (1 − Floor)·t |
| `power` | Floor + (1 − Floor)·tᵉ, today's |
| `exp` | Floor + (1 − Floor)·(e^{kt} − 1)/(e^k − 1) |
| `table` | 256 values loaded from a file, the "custom function based on the actual confidence". Its natural source is 008's measured σ per confidence bin |

**B, the profile along the ray, α(u).** Use the paper's family, normalised by τ:

| name | α(u) |
|---|---|
| `constant` | 1/(2τ), today's and the paper's |
| `linear` | falls linearly from the near edge of the band to the far edge (trust space seen through more than space guessed behind) |
| `exp` | the exponential falloff behind the surface, as in KinectFusion-style weighting |
| `hitprob` | from the noise model, built in 008 |

Evaluate it as a small table over u/τ, so it costs the same as the constant.

**Switching.**
- Both functions are fields of `FTsdfConfig`, exposed as `UPROPERTY` on `AReconstructionActor`.
- Console variables (`recon.Weight.Confidence`, `recon.Weight.Profile`) rebuild the tables
  between frames, live, on the phone or in a replay.
- They go into the snapshot's config, which means a new persistence format version (2). Version 1
  files load with today's defaults.

## The tempting wrong fixes

- **A virtual or `std::function` weighting policy.** Fork change §2 exists because a virtual call
  in the per-voxel loop blocked inlining and vectorisation, millions of times a second. Tables keep
  the switch outside the loop.
- **A `switch` on the function inside the per-voxel loop.** The same problem, smaller. Choose
  the table once per frame.
- **Tuning by raising the threshold.** Measured already: it deletes the floor.
- **Judging a function by how one live scan looks.** Same data or no verdict (006).

## Done when

- Every function in both tables can be selected at runtime, and the log line says which ones are
  active.
- The integration time on the device is within 5% of today's 5–8 ms with any function selected.
- One recording replayed under at least `power × constant` (today), `linear × linear` and
  `table × exp` produces three snapshots and their 011 metrics, recorded here.

## Files

```
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/Private/TsdfReconstruction.cpp   the confidence curve
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/Public/TsdfReconstruction.h      FTsdfConfig
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/openchisel/include/open_chisel/weighting/Weighter.h
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/openchisel/include/open_chisel/ProjectionIntegrator.h
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/openchisel/OPENCHISEL-README.md  §2, §4, §6
UnrealWorld/Source/UnrealWorld/ReconstructionPersistence.h   the format and its version
klingensmith2015chisel.pdf   §III-B
```
