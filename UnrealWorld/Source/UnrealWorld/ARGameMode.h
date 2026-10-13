#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "ARGameMode.generated.h"
/// <summary>
/// For now it's just an "empty" Game Mode to allow me to 
/// set the specific Pawn that i want to use (A pawn derived
/// from AARPawn).
/// </summary>
UCLASS()
class AARGameMode : public AGameModeBase {
	GENERATED_BODY()

public:
	AARGameMode();
};