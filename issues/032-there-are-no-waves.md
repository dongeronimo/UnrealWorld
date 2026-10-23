# 032 — There are no waves: nothing spawns enemies

**Area:** gameplay · **Status:** open · **Blocked by:** 019, 030, 031

## Context

*Filed 2026-10-23.*

The arena is waves of Ratomen. There's one enemy type this milestone. Waves differ by count, by
which spawn points they use, and by timing.

## What to do

- `UWaveSet` (a data asset): an ordered list of waves. Each wave has a count, the spawn-point tags
  to use, the spawn interval, and an optional delay before it starts. The arena's `BP_ArenaGameMode`
  references one.
- `AEnemySpawnPoint`: a placed actor with tags.
- The game mode runs the waves. The next wave starts when the current one is dead, or after a
  timeout. After the last one, extraction opens (031).
- Spawned Ratomen reset their physics chains to rest (016), are granted `AS_Ratoman` with its
  init effect (037, 039), and are given Sophia as their target (019). The wave counts a death when
  030's `GA_Death` reports it, not by polling Health.
- Spawning happens on authority. It costs nothing now and is correct when there's a second
  player (041).
- **Measure on the phone:** the frame time with the largest wave alive. That number caps the wave
  size, not taste.
- Wave start and end, alive count and frame time are logged.

## The tempting wrong fixes

- **Spawning all of a wave in one frame.** That's a hitch per wave. Space the spawns by the interval.
- **Pooling actors from the start.** Measure first. Ten characters spawning over a few seconds may
  be fine.

## Done when

- Three waves of increasing size run and complete, and extraction opens after the third. The
  largest wave's frame time on the Galaxy is recorded here.

## Files

```
UnrealWorld/Source/UnrealWorld/   UWaveSet, AEnemySpawnPoint (new), AArenaGameMode
```
