# 033 — The app has no front door: it opens straight into one level

**Area:** gameplay + ui · **Status:** open · **Blocked by:** 042 · **Blocks:** 002's "two sessions in one app"

## Context

*Filed 2026-10-23.*

Today the app opens on whatever the default map is (`AR_Blank`, with `ARGameMode`). Milestone 1 ends
with two sessions in one app: the arena (031) and the room (034). They are to be united in a later
milestone (002). Until then, a menu picks one.

## What to do

- `FrontDoor.umap` as the game default map, with a UMG menu: **Arena**, **Room**, and a **Fixture**
  entry in development builds only (a saved world or replay picker, through
  `UReconstructionPersistence`).
- Each entry opens its level with its game mode (`?game=`). The arena uses no ARCore. The room starts
  the AR session.
- **Leaving a session returns to the front door.** AR has to shut down cleanly: `UARSessionStarter`
  stops the session, and a second entry into Room starts a fresh one.

## The tempting wrong fixes

- **One level, with sessions as sublevels toggled on and off.** The sessions share nothing this
  milestone, and the AR session's lifetime is the best reason to keep them as separate maps.
- **Starting ARCore at app launch.** The arena doesn't need the camera, and the permission prompt
  belongs to the session that uses it.

## Done when

- On the phone: front door → arena → back → room → back → arena, with no crash, and with the camera
  off whenever the arena is running.

## Files

```
UnrealWorld/Config/DefaultEngine.ini   GameDefaultMap
UnrealWorld/Source/UnrealWorld/ARSessionStarter.*, ARGameMode.*, FixtureGameMode.*
```
