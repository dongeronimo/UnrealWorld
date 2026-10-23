# 006 — Only the fused field is saved, so no weighting function can be compared on the same data

**Area:** recon + tools · **Status:** open · **Blocks:** 007, 008, 009, 011

## Context

*Filed 2026-10-23.*

The fixture loads a `.tsdf`, which is the **result** of fusion. Weighting, truncation, carving and
the confidence curve are already baked into every voxel of it. Load it with a different function
and nothing changes, because the function has nothing left to act on.

Every question this milestone has to answer about stability (002) has the same shape: "is function A
better than function B on this room?". Asked live on the phone, that question can't be answered.
Every sweep is a different path, different motion blur and different depth, so the two functions
never see the same input. ToySoldiers tuned live and never found out which of its suspects was
guilty.

So: **record what ARCore gives, and replay it through `FTsdfReconstruction` on the desktop.**

## What to do

- **Record on the device.** `Recon.Record <name>` and `Recon.Record stop` write every frame the
  reconstruction **would integrate** (new depth timestamp, tracking). Each frame carries:
  - the depth (`uint16` mm) and its confidence (`uint8`);
  - the intrinsics and the raw sensor pose;
  - the timestamps;
  - optionally the YUV image, downsampled, because it's the largest part.

  Write it to `Saved/Recon/<name>.tsdfrec`, append-only, with a header and a version.
  `Tools/recon.py` gets a `pull-rec` beside `save`.
- **Replay on the desktop.** A fixture mode, `?ReconReplay=<name>`, or a `ReplayToLoad` beside
  `WorldToLoad` in `UReconstructionPersistence`. It feeds the frames to `FTsdfReconstruction::Integrate`
  in order, at a chosen speed or as fast as possible, with **this run's** `FTsdfConfig` and
  functions. It shows the result as the live mode does.
- **Deterministic.** The same recording with the same config twice gives byte-identical snapshots.
  That's what makes a difference between two functions mean something.
- **Batch.** A commandlet or `-ExecCmds` path that replays a recording under a config and writes the
  snapshot and the 011 metrics without a viewport, so a sweep over functions is a script.

## The tempting wrong fixes

- **Comparing two saved `.tsdf` files from two scans.** That compares two scans, not two
  functions.
- **Recording the camera view as video.** Depth and confidence are what is being tuned, and a
  video has neither.
- **Recording every camera frame.** Two thirds of the frames carry a repeated depth image (the log
  in Step 11). Record only the ones the actor would integrate, and record the skip counts so the
  statistics still add up.
- **Replaying through the actor's ARCore path with a fake `UARSessionStarter`.** The `FTsdfDepthFrame`
  boundary already exists, and it is plain pointers and numbers. Replay at that boundary, and
  nothing in AR needs faking.

## Done when

- A 60 s recording of a room is made on the Galaxy, pulled, and replayed in the fixture. It shows
  the same room the phone showed.
- Two replays with the same config produce identical snapshot bytes.
- The file size per minute, with and without colour, is recorded here.

## Files

```
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/Public/TsdfReconstruction.h   FTsdfDepthFrame, the boundary
UnrealWorld/Source/UnrealWorld/ReconstructionActor.cpp       HandleFrame: what is integrated and what is skipped
UnrealWorld/Source/UnrealWorld/ReconstructionPersistence.*   where the recordings live, the dropdown
UnrealWorld/Source/UnrealWorld/ReconstructionCommands.cpp    Recon.Save, Recon.List
UnrealWorld/Tools/recon.py                                   pulling from the device
```
