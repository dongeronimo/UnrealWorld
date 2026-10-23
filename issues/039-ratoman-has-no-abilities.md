# 039 — Ratoman's attacks aren't abilities: the claw and the roar

**Area:** gameplay + ai · **Status:** open · **Blocked by:** 037, 018, 030 · **Blocks:** 019

## Context

*Filed 2026-10-24.*

The brute's actions go through GAS like Sophia's (037, 038). His AI (019) **activates abilities by
tag** and doesn't play montages itself. That way the same tags, blocks and cancels apply to him and
to her, and a stunned Ratoman can't attack, for the same reason a stunned Sophia can't.

| ability | tags | what it does |
|---|---|---|
| `GA_RatomanClaw` | `Ability.Ratoman.Claw`. Blocked by `State.Dead`, `State.Stunned`. Adds `State.Attacking` | one of 018's swings, picked at random or by distance. `WaitGameplayEvent(Event.Melee.HitWindow.*)` sweeps the claw and calls 030's `ApplyHit` |
| `GA_RatomanRoar` | `Ability.Ratoman.Roar` | the aggro roar on first sight, with 013's Scream curve. Cosmetic, and also a tell before the first attack |

## What to do

- Implement both. Grant them through `AS_Ratoman`, with `GE_RatomanInit` for his attributes (more
  Health than Sophia's pistol takes in one shot, so the katana matters).
- 018's swing notifies become `AnimNotify_SendGameplayEvent`, the same as 028's.
- **The cooldown and recovery after a swing** are effects (`GE_Cooldown_Claw`). The opening Sophia
  exploits is a window where `State.Attacking` is gone and the cooldown is still running.
- 019's State Tree tasks call `TryActivateAbilitiesByTag(Ability.Ratoman.Claw)` and wait for the
  ability to end.

## The tempting wrong fixes

- **The AI playing the attack montage directly.** Then the damage window, interruption by a hit
  react and the `State.Dead` block all have to be redone in the AI, and they drift from Sophia's.
- **Hitting from distance checks in the AI** ("in range, so damage"). Hits come from sweeps
  inside the window. Range is only the AI's reason to try.

## Done when

- A Ratoman in range swings, hits Sophia only inside the window, can be interrupted by her hit
  (030's hit react), and roars on first sight. It works in a 2-player listen-server PIE.

## Files

```
issues/018 (clips), 019 (the AI that activates these), 030 (ApplyHit), 037 (GAS)
```
