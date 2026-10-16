#pragma once

#include "CoreMinimal.h"
#include "ReconGameModeBase.h"
#include "ARGameMode.generated.h"
/// <summary>
/// The game mode on the device. Its blueprint sets the AR pawn, and its
/// Persistence is what Recon.Save writes through. WorldToLoad stays empty
/// there: the reconstruction runs live from ARCore.
/// </summary>
UCLASS()
class AARGameMode : public AReconGameModeBase {
	GENERATED_BODY()

public:
	AARGameMode();
};
