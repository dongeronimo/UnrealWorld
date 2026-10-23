# 031 — There's no arena: no greybox level, extraction point or win and lose

**Area:** gameplay + level · **Status:** open · **Blocked by:** 029 · **Blocks:** 032

## Context

*Filed 2026-10-23.*

The arena session of milestone 1 (002) is "a simple blocked dummy world where Sophia fights the
waves of enemies and goes to the extraction point" (user, 2026-10-23). It's greybox. The deliverable
is the loop, not the look.

## What to do

- `Arena.umap`:
  - greyboxed with the modeling tools or BSP into a level a minute or two across, with a start area,
    a few obstacles and corridors to fight around, and an extraction point at the far side;
  - a baked navmesh (`NavMeshBoundsVolume`), which is the easy navmesh that 019 is first proven on;
  - spawn points for 032, as placed actors.
- `AArenaGameMode` (Abstract C++, with `BP_ArenaGameMode` setting classes and tuning) and a session
  state:
  - `Fighting`: the waves run (032);
  - `ExtractionOpen`: after the last wave, or after N waves, the extraction point lights up;
  - `Won`: Sophia enters the extraction volume while it is open;
  - `Lost`: Sophia dies.
  - Won and Lost show a screen with retry and back to the front door (033).
- `AExtractionPoint`: a volume and a visible marker. Its state is set by the game mode.
- A HUD with Sophia's health, the wave number and an extraction indicator.

## The tempting wrong fixes

- **Building art for it.** Greybox is the point. A greybox that plays well is the spec for any
  later art pass.
- **Opening extraction from the start.** Then the loop is "run past everything". It opens when
  the waves allow it.
- **Hardcoding the waves in the level blueprint.** That belongs to 032's data. The level only
  places the spawn points.

## Done when

- On the phone: start, fight, reach extraction and win. Also start, die and lose. Retry and back
  both work.

## Files

```
UnrealWorld/Content/Levels/Arena.umap (new)
UnrealWorld/Source/UnrealWorld/   AArenaGameMode, AExtractionPoint (new)
```
