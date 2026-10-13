#pragma once
#include "CoreMinimal.h"
#include "ARFramePose.generated.h"
// What Blueprints get: no pointers, Unreal space, for logging and display.
USTRUCT(BlueprintType)
struct FARFramePose
{
    GENERATED_BODY()

    UPROPERTY(BlueprintReadOnly) int64 TimestampNs = 0;
    UPROPERTY(BlueprintReadOnly) bool bTracking = false;
    UPROPERTY(BlueprintReadOnly) bool bHasDepth = false;
    UPROPERTY(BlueprintReadOnly) bool bHasImage = false;
    UPROPERTY(BlueprintReadOnly) FVector Location = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly) FRotator Rotation = FRotator::ZeroRotator;
};