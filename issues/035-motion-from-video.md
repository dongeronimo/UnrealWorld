# 035 — Sophia's organic moves have no source: the video-to-motion pipeline isn't written

**Area:** tools + anim · **Status:** known (not scheduled)

## Context

*Filed 2026-10-23.*

Phases 2 and 3 of `Sophia_Animation_Plan.md`:
- a commercial-licence-only pipeline from video to her skeleton: MediaPipe or RTMPose for 2D
  keypoints, then `pontos_2d.py`, `ajustar_pose.py`, `limpar_movimento.py` and `armas.py`;
- one performance each for melee, sheathe, reload and hit react.

Milestone 1 doesn't need it:
- the katana combos come from the Grruzam clips (028);
- hit reacts come from Lyra or GAS;
- the stance and shot are target-based (027).

The plan's rule stays: **no non-commercial tool or model anywhere in the pipeline**. That rules out
OpenPose and everything built on SMPL.

## Done when

As phase 2 of the plan: one recorded clip on her in Unreal, with the feet locked and the muzzle on
target.

## Files

```
Sophia_Animation_Plan.md   §3, §6
```
