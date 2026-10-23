# 038 — Sophia's moves aren't abilities: shooting, the katana combo, draw and sheathe, and dodge

**Area:** gameplay + anim · **Status:** open · **Blocked by:** 037, 027, 028, 030 · **Blocks:** 029

## Context

*Filed 2026-10-24.*

The animation cards give Sophia her clips: the ready pose, aim offset and fire additive (027), and
the draw, sheathe and Grruzam combos (028). GAS (037) is how those clips become *actions* that have
state, can be interrupted, and will replicate later. Each action is one ability:

| ability | tags | what it does |
|---|---|---|
| `GA_FirePistol` | `Ability.Fire`. Blocked by `State.Dead`, `State.Stunned` | traces the camera to an aim point, then the muzzle socket to it. Sends the hit as **TargetData**, calls 030's `ApplyHit`, triggers `GameplayCue.Fire.Muzzle`, and plays the fire additive. Cooldown via `GE_Cooldown_Fire` |
| `GA_KatanaCombo` | `Ability.Melee.Combo`. Requires `State.Katana.Drawn`. Adds `State.Attacking` | `PlayMontageAndWait` on the combo montage. `WaitGameplayEvent(Event.Melee.HitWindow.Open/Close)` opens and closes a sweep along the blade, each target hit once per swing. Input pressed inside `Event.Melee.ComboWindow` jumps to the next section |
| `GA_DrawKatana` / `GA_SheatheKatana` | `Ability.Katana.Draw` / `.Sheathe` | play `katana_intro` / `katana_embainhar` as upper-body montages. The socket swap notify (028, frames 5 and 30) also adds or removes `State.Katana.Drawn` via a gameplay event |
| `GA_Dodge` | `Ability.Dodge`. Adds `State.Invulnerable` briefly | a root-motion dodge montage. Cancels `State.Attacking` |

**Anim notifies send gameplay events; they don't run gameplay.** 028's `HitWindowStart` and
`HitWindowEnd` become `AnimNotify_SendGameplayEvent` with the `Event.Melee.HitWindow.*` tags. The
ability listening decides what they mean. The same goes for 027's `Fire` notify, which becomes
`Event.Fire.Muzzle`.

## What to do

- Implement the four abilities: C++ bases for the logic, and blueprint subclasses for the montages,
  damage numbers and cues. Grant them through `AS_Sophia` (037's `UAbilitySet`).
- Bind them through 037's input map. 029's touch buttons and the keyboard both go there.
- **Targeting is built as TargetData, even single-player.** That's GAS's slot for "the client says
  what it hit and the server confirms". Built that way now, it is what the shot becomes later at no
  extra cost.
- **The katana sweep:** each frame inside the window, a capsule sweep from the blade's previous
  position to its current one, with a per-activation set of actors already hit.

## The tempting wrong fixes

- **The katana's drawn state as a `bool` on the character.** Then the AnimBP, the abilities and the
  HUD read three different things, and none of them replicate. `State.Katana.Drawn` is a tag, so
  the AnimBP reads it through `ASC->HasMatchingGameplayTag` or a tag-to-property map.
- **Combo chaining in the AnimBP or the character's Tick.** The combo belongs in the ability. Its
  window is an event, and its state ends when the ability ends.
- **The pistol ability spawning muzzle flash particles directly.** Use a gameplay cue, so the
  other player sees it too, later.

## Watch for

- **Root-motion montages in multiplayer** (the dodge, lunging cuts) are predicted by GAS and
  CharacterMovement together, and are the most famous source of rubber-banding. Not now, but keep
  root motion to the montages that need it.

## Done when

- On the phone, from touch: she draws, runs a 3-hit combo where every hit logs once, sheathes,
  shoots with the cooldown respected, and dodges through an attack with the invulnerability window
  working.
- `showdebug abilitysystem` shows the tags coming and going. It works in a 2-player listen-server
  PIE.

## Files

```
issues/027, 028 (the clips and their notifies), 030 (ApplyHit), 037 (GAS)
UnrealWorld/Source/UnrealWorld/   the abilities (new)
```
