# 030 — Nothing can be hurt: no damage effects, hit reactions or death

**Area:** gameplay · **Status:** open · **Blocked by:** 037, 017, 023 (bodies to hit) · **Blocks:** 019, 032, 038, 039

## Context

*Filed 2026-10-23. Rewritten 2026-10-24 for GAS (037).*

The arena loop (002) is: fight waves, die or extract. That needs damage, reactions and death for
Sophia and the Ratomen alike. All fight interactions go through GAS (037, a user decision). This card
is the shared half: **how a hit becomes damage, and what happens to whoever takes it**. Each weapon's
own ability (the shot, the katana combo, the claw) is in 038 and 039, and each ends by handing this
card's machinery a hit result.

## What to do

- **`GE_Damage`:** an instant GameplayEffect with a `UDamageExecution`
  (`UGameplayEffectExecutionCalculation`).
  - The magnitude comes from **SetByCaller** (`SetByCaller.Damage`), set by the weapon ability.
  - It is modified by the target's tags. `State.Invulnerable` makes it 0. Damage types and
    headshots go here too: the hit result's bone name is in the effect context.
  - It writes the `Damage` meta attribute. `UCombatAttributeSet::PostGameplayEffectExecute` turns
    that into Health loss.
- **One entry point.** `UCombatStatics::ApplyHit(Source ASC, Target, const FHitResult&, Damage)` builds
  the effect context with the hit result and applies `GE_Damage`, **on authority only**. Every
  weapon ability calls it.
- **Hit reaction.**
  - Health dropping, without dying, sends `Event.Hit.Received` to the target.
  - `GA_HitReact`, triggered by that event, plays the hit react montage (018 for Ratoman; Lyra or
    GAS clips for Sophia, 029).
  - It applies `GE_Stagger` (a short `State.Stunned` and a `MoveSpeedMultiplier` drop), and it
    cancels abilities tagged `State.Attacking` according to the ability's interruptibility.
- **Death.** Health at 0 triggers `GA_Death`:
  - it adds `State.Dead`, which blocks every other ability through `ActivationBlockedTags`;
  - it ragdolls (017, 023) or plays the death clip;
  - it notifies the game mode (031 and 032 count kills).
- **Invulnerability after a hit.** Sophia gets `GE_HitIFrames`, a short `State.Invulnerable`, so a
  group of brutes can't chain-kill her in one frame.
- **Feedback** goes through **GameplayCues** (`GameplayCue.Hit.Flesh`): blood and a sound on hit.
  They replicate as cues later, and nobody spawns particles by hand.
- The face curves (013's Pain, 025's wince) are set by `GA_HitReact`.

## The tempting wrong fixes

- **Overlap events on the weapon's collision.** These fire whenever the sheathed blade touches
  anything and miss fast swings. Detecting hits is the weapon ability's job, with sweeps inside
  gameplay-event windows (038, 039). This card only receives hit results.
- **`AActor::TakeDamage`, as well as GAS.** That's two damage paths, and the second one skips
  tags, cues and replication. Pick GAS, and only GAS.
- **Changing Health directly in the ability** (`SetNumericAttributeBase`). It bypasses execution,
  tags and prediction. Damage is an effect.
- **Applying the effect on the client because single player has no client.** See 037. The listen
  server test catches it.

## Done when

- Sophia kills a Ratoman with the pistol and with the katana. A Ratoman kills Sophia.
- Every hit logs who, what, how much and the bone hit.
- Hit reacts interrupt attacks, dead characters activate nothing, and the cues play.
- The same works in PIE as a listen server with 2 players.

## Files

```
UnrealWorld/Source/UnrealWorld/   UDamageExecution, UCombatStatics, GA_HitReact, GA_Death (new); UCombatAttributeSet (037)
issues/037 (GAS), 038, 039 (the weapons), 017, 023 (the bodies)
```
