#pragma once
#include "CoreMinimal.h"
#include "ARSessionConfig.h"
#include "ReconstructionSessionConfig.generated.h"
/// <summary>
/// Holds the configs for our needs: raw depth and confidence map
/// </summary>
UCLASS()
class UReconstructionSessionConfig : public UARSessionConfig {
    GENERATED_BODY()
public:
    UReconstructionSessionConfig();
};