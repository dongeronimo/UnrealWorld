#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "ARFrameData.h"
#include "ARFramePose.h"
#include "ARSessionStarter.generated.h"
class UARSessionConfig;
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnNewARFrame);

DECLARE_MULTICAST_DELEGATE_OneParam(FOnARFrame, const FARFrameData&);

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnARFramePose, const FARFramePose&, Pose);

// UCLASS types can't live inside a C++ namespace: UnrealHeaderTool skips namespace blocks.
UCLASS()
class UARSessionStarter : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	// C++ consumers. Fires once per camera frame, after arcore update and before
	// any actor ticks or the frame's rendered,
	FOnARFrame OnARFrame;
	// Fires at the same stage that OnARFrame fires, but only carries pose information
	UPROPERTY(BlueprintAssignable)
	FOnARFramePose OnARFramePose;
private:
	void OnPreActorTick(UWorld* World, ELevelTick TickType, float DeltaSeconds);
	void ReadAndBroadcastFrame(UWorld* World);

	// UPROPERTY so the garbage collector doesn't delete the config while the
	// session is still using it. Nothing else holds a reference to it.
	UPROPERTY()
	TObjectPtr<UARSessionConfig> SessionConfig;

	FDelegateHandle PreActorTickHandle;
	bool bSessionRequested = false;
	int64 LastFrameTimestampNs = 0;

};
