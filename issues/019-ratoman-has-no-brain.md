# 019 — Ratoman has no brain: nothing makes him chase, attack or walk anywhere

**Area:** ai + gameplay · **Status:** open · **Blocked by:** 018, 030, 039 · **Blocks:** 032, 034

## Context

*Filed 2026-10-23.*

Both sessions of milestone 1 (002) need a Ratoman who moves by himself:
- **Arena:** he detects Sophia, closes in, attacks in range, reacts to hits and dies (030).
- **Room:** he walks across the reconstructed room's navmesh (012, 034). There's no Sophia, so a
  "walk to a target point" behaviour is enough.

The same character, controller and behaviour serve both. The room just has no enemy to chase.

## What to do

- `ARatomanBrute : ACharacter` (C++, exists since 013 with the four face weights, which `ABP_RatomanBrute`
  reads in Update Animation; make it Abstract). Its mesh, ABP and tuning are set on
  `BP_RatomanBrute`, following the project's pattern of blueprint-set assets and no path lookups.
  The character carries its own AbilitySystemComponent (037, Minimal replication), and its
  Health is the attribute.
- `ARatomanAIController` with a small **State Tree** (5.7's recommended alternative to Behaviour
  Trees), or a Behaviour Tree if State Tree fights you:
  - `Idle`, then `Chase` (MoveTo the target on the navmesh), then `Attack` (in range:
    `TryActivateAbilitiesByTag(Ability.Ratoman.Claw)` and wait for the ability to end, 039);
  - **the AI reads GAS state instead of keeping its own.** `State.Stunned` or `State.Dead` on
    the ASC stops the tree. The hit react and death are 030's abilities, not AI states;
  - `Wander` / `GoTo(point)`, for the room session.
- Perception: sight on the player's pawn, or just "the player" for the arena's first version.
- His speed and acceleration feel heavy: slower than Sophia's run, so she can kite him.

## The tempting wrong fixes

- **Steering in Tick toward the player's location.** It works in an empty arena and walks into
  every wall, and it isn't what the room session is testing. Use the navmesh.
- **One controller class per session.** The room session's point is proving that *the same*
  character navigates a real room.
- **Group tactics now.** Waves of brutes that all chase is enough for this milestone. Surround and
  flank behaviours are a later card.

## Done when

- In the arena, five Ratomen chase Sophia, attack in range and die when killed, on a baked navmesh.
- In the fixture, on a navmesh from 012, a Ratoman walks to points clicked in the room.

## Files

```
UnrealWorld/Source/UnrealWorld/   the character and the controller (new)
UnrealWorld/Content/Chars/RatomanBrute/   BP_RatomanBrute, ABP_RatomanBrute
```
