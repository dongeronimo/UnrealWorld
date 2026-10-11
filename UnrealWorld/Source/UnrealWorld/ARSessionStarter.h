#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "ARSessionStarter.generated.h"

class UARSessionConfig;

// UCLASS types can't live inside a C++ namespace: UnrealHeaderTool skips namespace blocks.
UCLASS()
class UARSessionStarter : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
private:
	bool Tick(float DeltaSeconds);

	// UPROPERTY so the garbage collector doesn't delete the config while the
	// session is still using it. Nothing else holds a reference to it.
	UPROPERTY()
	TObjectPtr<UARSessionConfig> SessionConfig;

	FTSTicker::FDelegateHandle TickerHandle;
	bool bSessionRequested = false;
};
