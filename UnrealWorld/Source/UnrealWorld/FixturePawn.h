#pragma once
#include "CoreMinimal.h"
#include "GameFramework/DefaultPawn.h"
#include "FixturePawn.generated.h"

// The camera for looking at a recorded room. Spawned only by AFixtureGameMode;
// on the device the pawn is AARPawn, whose camera belongs to ARCore.
//
// ADefaultPawn already flies (WASD, mouse to look, E/Q up and down) with no input
// assets to author. What it gets wrong here is collision: its sphere carries the
// Pawn profile, so once the chunks collide the camera would stand on the floor it
// came to look at and couldn't get out of a closed room to see the far wall from
// behind. So nothing on this pawn collides.
UCLASS()
class AFixturePawn : public ADefaultPawn {
    GENERATED_BODY()
public:
    AFixturePawn(const FObjectInitializer& ObjectInitializer);
};
