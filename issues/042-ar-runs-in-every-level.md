# 042 — AR runs in every level: the AR pawn spams camera info and ARCore starts outside the room

**Area:** ar + gameplay · **Status:** open · **Blocks:** 033 (the arena must run with the camera off)

## Context

*Filed 2026-10-25.*

Playing `RatomanBrute_Test.umap` in the editor fills the log with one line a second:

```
LogBlueprintUserMessages: [BP_ARPawn_C_0] [CamCheck] t=9.028 loc=X=-35.589 Y=146.933 Z=145.875 rot=P=-0 Y=-91 R=0
```

The "AR subsystem" doesn't print this. Three separate things add up to it:

1. **The project's global default game mode is the AR one.** `Config/DefaultEngine.ini` has
   `GlobalDefaultGameMode=/Game/BP_ARGameMode.BP_ARGameMode_C`. Any level without a GameMode
   Override in its World Settings becomes an AR session with `BP_ARPawn` as the player.
   `RatomanBrute_Test.umap` has no override. `AR_Blank`, `Arena` and `Fixture` each set their own.
2. **`BP_ARPawn` has a debug timer** (Set Timer → Print String `[CamCheck] t={0} loc={1} rot={2}`),
   left over from checking that the camera follows the phone. It prints on every platform, on
   screen and in the log.
3. **`UARSessionStarter` starts ARCore in every world.** It's a GameInstance subsystem. Its
   `OnPreActorTick` calls `UARBlueprintLibrary::StartARSession` in the first tick of *any* world,
   whatever the game mode or platform. On Windows nothing answers and it just waits for a status
   that never comes. On the phone it would open the camera and ask for permission in the arena too.
   033 says "the arena uses no ARCore" but doesn't say what stops it.

## What to do

- **Default game mode:** make `GlobalDefaultGameMode` a plain one: `GameModeBase`, or
  `BP_ArenaGameMode` if test levels should get a Third Person pawn. Then AR happens only in levels
  that ask for it. `AR_Blank` already sets `BP_ARGameMode` explicitly, so check it still does.
- **`[CamCheck]`:** delete the timer from `BP_ARPawn`. If it's still useful on the phone, gate it behind
  a `bLogCameraPose` bool (default off) instead of a platform check.
- **Starting the session:** the starter only starts ARCore when the world asks for it, and never
  off Android:
  - the request comes from the AR game mode (`AARGameMode`, e.g. its `BeginPlay` calls a
    `RequestSession()` on the starter), not from "a world ticked". This matches the project's
    pattern of explicit references over global magic;
  - `#if PLATFORM_ANDROID` around the `StartARSession` call, or `ShouldCreateSubsystem` returning
    false off Android. `ARCameraFeed` and `ReconstructionActor` already handle a null starter;
  - the Fixture keeps working on Windows: it replays saved data and needs no session.

## The tempting wrong fixes

- **Wrapping the Print String in "is Android".** The log goes quiet in the editor, but the Ratoman
  test level still runs as an AR session with an AR pawn, and the arena still starts the camera on the
  phone.
- **Only adding a GameMode Override to `RatomanBrute_Test`.** It fixes this one level. The next test
  level hits the same thing.
- **Only disabling the subsystem off Android.** It's quiet in the editor, but on the phone ARCore
  still starts in the arena, which is the case that matters for 033.

## Done when

- In PIE, `RatomanBrute_Test` and any new empty level print no `[CamCheck]` lines and don't spawn
  `BP_ARPawn`.
- `AR_Blank` on the phone still starts the session, tracks and reconstructs as before.
- `Fixture` still replays in the editor.
- No `StartARSession` call happens in a world whose game mode isn't the AR one. Check it with a log
  line or a breakpoint.

## Files

```
UnrealWorld/Config/DefaultEngine.ini                      GlobalDefaultGameMode
UnrealWorld/Content/AR/BP_ARPawn                          the [CamCheck] timer
UnrealWorld/Source/UnrealWorld/ARSessionStarter.*         starts the session in OnPreActorTick
UnrealWorld/Source/UnrealWorld/ARGameMode.*               who should request the session
UnrealWorld/Content/Levels/RatomanBrute_Test.umap         where it was seen
```
