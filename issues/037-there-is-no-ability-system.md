# 037 — There's no ability system: GAS isn't enabled, and nothing owns combat state

**Area:** gameplay · **Status:** open · **Blocks:** 030, 038, 039, and through them 019, 029, 032

## Context

*Filed 2026-10-24.*

UnrealWorld is a **third-person action game**: blades, guns, some parkour. The hope is
**multiplayer, with two people in the same room**, each controlling a character (user, 2026-10-24).
Multiplayer isn't in milestone 1 (002). But every fight interaction built this milestone is a state
or action that will have to be synced later:
- health;
- a katana drawn or sheathed;
- a combo window open;
- a stun;
- a shot fired;
- a hit landed.

**Decision (user, 2026-10-24): all fight interactions go through the Gameplay Ability System.** The
reasoning is the user's day-job experience: GAS already solves state and action sync, with
replicated attributes, replicated tags, predicted ability activation, and gameplay cues for the
effects everyone should see.

**ToySoldiers rejected GAS, and that verdict doesn't carry over.** Its GDD (§"GAS foi avaliado e
descartado", `D:\ToySoldiers\docs\GDD.md`) rejected it because:
- the architecture was deterministic peer-to-peer lockstep, and GAS's client-server replication
  competes with lockstep;
- GURPS resolution is a procedure, not an ability graph.

Neither is true here. That GDD also warns that "using GAS single-player and swapping later is the
worst of both". Here that's an argument *for* starting now: nothing will be swapped. The one
objection that survives is **transport**, and it belongs to 041.

## What to do

- **Enable the `GameplayAbilities` plugin.** Add `GameplayAbilities`, `GameplayTags` and
  `GameplayTasks` to `UnrealWorld.Build.cs`.
- **Where the AbilitySystemComponent lives,** following Lyra's pattern:
  - **Sophia (the player):** the ASC is on `APlayerState`, with the character as its avatar. It
    survives a respawn, which matters on the arena's retry and later with two players. Replication
    mode **Mixed**.
  - **Ratomen (AI):** the ASC is on the character. Replication mode **Minimal**.
  - Both characters implement `IAbilitySystemInterface`.
- **`UCombatAttributeSet`:**
  - `Health` and `MaxHealth`;
  - `Damage`, a meta attribute that is never replicated and is turned into Health loss in
    `PostGameplayEffectExecute`;
  - `MoveSpeedMultiplier`, so slows and stagger are effects.
  - Stamina is left out until a card needs it.
- **Tags** in `Config/DefaultGameplayTags.ini` (or a tag table asset), one hierarchy:
  - `Ability.*`: `Ability.Fire`, `Ability.Melee.Combo`, `Ability.Katana.Draw`, `Ability.Dodge`,
    `Ability.Ratoman.Claw`, …
  - `State.*`: `State.Dead`, `State.Stunned`, `State.Katana.Drawn`, `State.Invulnerable`,
    `State.Attacking`
  - `Event.*`: gameplay events sent from anim notifies, such as `Event.Melee.HitWindow.Open`,
    `Event.Melee.HitWindow.Close`, `Event.Fire.Muzzle`, `Event.Hit.Received`
  - `GameplayCue.*`: `GameplayCue.Hit.Flesh`, `GameplayCue.Fire.Muzzle`, …
  - `Damage.*` and `SetByCaller.*`, for damage magnitudes
- **Input → ability.** Enhanced Input actions map to ability tags through a small data asset
  (`UInputAbilityMap`), the way Lyra's InputConfig does. A pressed action activates the ability
  granted with that input tag. 029's touch buttons use the same path.
- **Granting.** A `UAbilitySet` data asset holds the abilities, the startup effects (attribute
  init) and their tags. Each `BP_` character references its own set, following the project's
  pattern of blueprint-set assets and no path lookups.
- **Debugging:** `showdebug abilitysystem` works in PIE and on the device.

## The tempting wrong fixes

- **Using GAS for movement or parkour.** GAS gates movement: a `State.Stunned` tag blocks it, and a
  vault is an ability that starts a movement mode. But the movement and its prediction belong to
  `UCharacterMovementComponent` (or Mover). Abilities that set velocities by hand desync the
  moment there are two machines (040).
- **Health as a plain `float` on the character "because single player".** Then 030's damage, the
  HUD and death each read a different source. The attribute is the source.
- **Applying effects on the client because PIE has no client.** Every damage effect is applied
  where `HasAuthority()` is true. It costs nothing in single player and is the difference between
  "multiplayer later" and "rewrite later".
- **Adopting Lyra wholesale.** Lyra's experience, game-feature and modular-gameplay layers are a
  framework of their own. Copy its *patterns*: the ASC on PlayerState, the input-tag mapping and
  ability sets. Don't migrate its code.

## Watch for

- **A cheap multiplayer smoke test.** PIE can run as a *listen server with 2 players*. Once this
  card's abilities exist, play that way occasionally. A thing that works single-player and breaks
  there was built on the client. That's not multiplayer work; it's catching mistakes while they
  are still cheap.
- **The ASC on PlayerState means `InitAbilityActorInfo` is called twice:** on the server in
  `PossessedBy`, and on the client in `OnRep_PlayerState`. Forgetting the client side is the classic
  "abilities don't fire on the client" bug.

## Done when

- The plugin is enabled. Sophia's ASC is on her PlayerState and the Ratoman's on his character. The
  attribute set initialises from an effect. `showdebug abilitysystem` shows both.
- A test ability activated from an input action logs its activation and adds and removes a
  `State.*` tag.
- The same test works in PIE as a listen server with 2 players.

## Files

```
UnrealWorld/UnrealWorld.uproject                     the plugin
UnrealWorld/Source/UnrealWorld/UnrealWorld.Build.cs  module dependencies
UnrealWorld/Config/DefaultGameplayTags.ini           the tag hierarchy
UnrealWorld/Source/UnrealWorld/                      UCombatAttributeSet, UAbilitySet, UInputAbilityMap, the PlayerState (new)
D:\ToySoldiers\docs\GDD.md                           why ToySoldiers said no, and why that doesn't apply here
```
