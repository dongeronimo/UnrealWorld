#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "ReconGameModeBase.generated.h"
class UReconstructionPersistence;

// A game mode with a reconstruction in it. Owns the UReconstructionPersistence
// that AReconstructionActor asks for a world at BeginPlay and Recon.Save writes
// through. Two of these exist: AARGameMode on the device, AFixtureGameMode on
// the desktop.
UCLASS(Abstract)
class AReconGameModeBase : public AGameModeBase {
    GENERATED_BODY()
public:
    AReconGameModeBase();

    // ?ReconWorld=<name> on the URL picks the world to load without touching
    // the blueprint, for command-line and headless runs.
    virtual void InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) override;

    UReconstructionPersistence* GetPersistence() const { return Persistence; }

protected:
    UPROPERTY(EditDefaultsOnly, Instanced, Category = "Reconstruction")
    TObjectPtr<UReconstructionPersistence> Persistence;
};
