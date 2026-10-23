#pragma once
#include "CoreMinimal.h"
#include "ReconGameModeBase.h"
#include "FixtureGameMode.generated.h"

// The desktop game mode: a recorded room instead of ARCore. Set it as the
// GameMode Override of a fixture level that has a BP_ReconstructionActor in it,
// pick the room in Persistence -> WorldToLoad, and Play.
//
// The pawn is AFixturePawn: it flies (WASD, mouse to look, E/Q up and down) and
// collides with nothing, because the point is looking at the room from anywhere,
// outside included.
//
// Not abstract, so it also runs straight from the command line:
//     UnrealEditor.exe UnrealWorld.uproject /Game/Levels/Fixture?game=/Script/UnrealWorld.FixtureGameMode?ReconWorld=room1 -game
UCLASS()
class AFixtureGameMode : public AReconGameModeBase {
    GENERATED_BODY()
public:
    AFixtureGameMode();
};
