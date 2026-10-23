# 005 — The room dies when Android backgrounds or kills the app

**Area:** ar + recon · **Status:** open · **Blocked by:** 004 · **Blocks:** a room session longer than one sitting

## Context

*Filed 2026-10-23.*

The reconstruction lives in `AReconstructionActor` and dies with the level, which is by design
(Step 1 of `running_the_reconstruction.md`). The condition attached to that design was: "That's fine
as long as the field (and the anchor) get saved when the Android activity lifecycle would kill our
data (task switch, locking the phone)." That part isn't done. Today the only save is `Recon.Save`,
typed by hand.

There are two different events, and they need different answers:

1. **Backgrounded** (task switch, locked screen). The process usually survives and ARCore pauses.
   On resume, the session continues **in the same tracking space** if ARCore relocalizes, and the
   anchor (004) comes back. The field in memory is still valid. The risk is that Android kills the
   process while it's in the background.
2. **Killed** (low memory while in the background, or swiped away). The process is gone. A new
   ARCore session starts with **a new tracking space** that has no relation to the old one. A saved
   field reloads in the wrong place.

## What to do

- **On background**, hooked to `FCoreDelegates::ApplicationWillEnterBackgroundDelegate` or
  `ApplicationWillDeactivateDelegate`, the game thread, before Android may freeze it:
  - write the snapshot through `UReconstructionPersistence::Save` to a fixed autosave name;
  - write the anchor's pose next to it;
  - stop integrating.
- **On resume:**
  - If the process survived, keep the field in memory and wait for tracking and the anchor to
    come back.
  - If the process restarted and an autosave exists, load it, but **mark it unregistered**: shown
    as a ghost, not integrated into, until it is realigned. Realigning it to the new tracking space
    is its own problem, and this card doesn't solve it (see Known: 036).
- Measure how long the save takes on the device for a room of 50–200 chunks. Android gives
  background transitions a few seconds at most.

## The tempting wrong fixes

- **Saving every N seconds "just in case".** It costs a full voxel copy on the game thread
  (`CaptureSnapshot` is documented as "a debug command, not per frame"). The lifecycle delegates
  exist so the save happens exactly when it's needed.
- **Integrating into a reloaded field before it is realigned.** New depth lands in a new
  tracking space on top of the old one, and the room doubles. It looks like terrible depth, and
  it isn't.
- **Assuming ARCore keeps tracking space across a restart.** It doesn't. Only Cloud Anchors or
  our own relocalization bring a space back.

## Done when

- Lock the phone mid-scan and unlock it: the room is still there, registered, and the scan
  continues.
- Kill the app mid-scan and reopen it: the autosave loads and is shown as unregistered, nothing
  is integrated into it, and the log says why.
- The save time on the device is recorded here.

## Files

```
UnrealWorld/Source/UnrealWorld/ReconstructionPersistence.h/.cpp   Save, Load, the format
UnrealWorld/Source/UnrealWorld/ReconstructionActor.h/.cpp         CaptureSnapshot, live vs loaded
UnrealWorld/Source/UnrealWorld/ARSessionStarter.cpp               pause/resume of the session
```
