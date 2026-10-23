# 008 — No noise model for the Galaxy's depth: no dynamic truncation, and no weight from the hit probability

**Area:** recon + tools · **Status:** open · **Blocked by:** 006, 007 · **Blocks:** 011

## Context

*Filed 2026-10-23.*

The Chisel paper (`klingensmith2015chisel.pdf`, §III-A, B and D) rests three things on a **parametric
noise model of the sensor**, `z ~ N(d, σ_d)`, trained with the method of Nguyen et al. [32]. It
then mentions two of them only in passing:

1. **The weight from the hit probability.** "It is possible [32] to directly compute the
   weighting function α from the hit probability (2) of the sensor". The paper didn't, for speed,
   and says that the constant it used gives poorer reconstruction where the noise is high. The
   Galaxy S22 and S25 are exactly that kind of sensor.
2. **Dynamic truncation.** `T(z) = β·σ_z`: the band around a sample is as wide as β standard
   deviations of the noise at that depth, instead of a fixed 6 cm.
   - The fork already supports it. `Truncator` is `τ(d) = |a·d² + b·d + c|·s`, and
     `QuadraticTruncator` was folded into it (fork change §2).
   - Today the code calls `Truncator::Constant(Config.TruncationMetres)`.
   - The coupling matters: `Weighter` divides by 2τ, so a wider band at distance also means a
     smaller weight. One knob, not two (`Weighter.h`).
3. **The carving region**, which starts at `τ + ε`, also follows τ.

Nobody has measured σ for these phones. ARCore also gives a **confidence** per sample, so the model
worth fitting is **σ(z, confidence)**, not σ(z) alone. That is the "custom function based on the
actual confidence" in 007's `table`: a measured σ per confidence bin becomes the weight, in the
inverse-variance form `w ∝ 1/σ²`. Inverse variance is what the weighted running average needs in
order to be the least-squares estimate (Curless and Levoy, as cited in §III-B).

## What to do

- **Capture.** Point the phone at a flat, textured wall at several distances (0.3 to 3 m, the
  reconstruction's range) and at a few angles. Use 006's recorder. Do the same for a blank wall,
  which is the case the confidence map is pessimistic about.
- **Fit.**
  - A tool (`Tools/noise_model.py`) fits a plane to each capture with RANSAC.
  - It takes the residual's standard deviation per depth bin and per confidence bin, and fits:
    - `σ(z) = a·z² + b·z + c`, the Truncator's own form;
    - a σ-by-confidence table.
  - It writes both to a small JSON committed in `Content/ReconWorlds/` or next to the tool.
  - The angle dependence (Nguyen's θ term) gets recorded even if it isn't used yet. 009 wants it.
- **Use.**
  - The truncation becomes `Truncator(a, b, c, β)`, with β as a config field (start at 2–3).
  - 007's `hitprob` profile is the Gaussian `N(u; 0, σ_z)`, normalised over the band.
  - 007's `table` confidence curve becomes `1/σ²(conf)`, normalised.
- **Compare on replays** (006): constant τ against dynamic τ, and constant against `hitprob`,
  with 011's metrics.

## The tempting wrong fixes

- **Taking σ from a paper or a different phone.** The Tango, Kinect and iPhone numbers say
  nothing about Samsung's depth pipeline, which is ARCore's depth-from-motion with or without a
  ToF sensor, depending on the model. Measure it on the device that will run it.
- **Fitting σ on the blank wall only, or the textured one only.** The confidence map exists
  because the two differ. Fit both, or the table has one point.
- **A very large β, to stop holes.** A wide band smears surfaces and, through 2τ, weakens every
  sample. Holes are 009's and 007's problem.

## Done when

- `σ(z)` and σ-by-confidence are measured on the Galaxy and committed, with the plot of residuals
  against depth.
- Dynamic truncation and the `hitprob` profile can be selected through 007's switches.
- A replay comparison of constant against dynamic τ is recorded here, with numbers.

## Files

```
klingensmith2015chisel.pdf   §III-A (the noise model), §III-B (α), §III-D (dynamic truncation), §III-E (carving)
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/openchisel/include/open_chisel/truncation/Truncator.h
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/openchisel/include/open_chisel/weighting/Weighter.h
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/Private/TsdfReconstruction.cpp   SetTruncator, SetWeighter
UnrealWorld/Tools/                                                                         the fit
```

Reference: C. V. Nguyen, S. Izadi, D. Lovell, "Modeling Kinect Sensor Noise for Improved 3D
Reconstruction and Tracking", 3DIMPVT 2012. This is the paper's [32].
