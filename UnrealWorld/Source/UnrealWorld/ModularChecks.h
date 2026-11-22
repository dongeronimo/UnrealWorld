#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "ModularChecks.generated.h"

class UAnimSequence;
class USkeletalMesh;

/// <summary>
/// Headless checks of a modular character, from editor Python (check_drow_correctives.py). The question no clip test
/// answers: does a piece in Leader Pose get the correctives the leader's Post Process Anim Blueprint computes? The
/// parity test reads the curves on the leader only, and the editor shows it only to someone who knows where to look.
/// </summary>
UCLASS()
class UNREALWORLD_API UModularChecks : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/// Poses Leader at Time of Anim in a preview scene (single node, not playing: the details panel's Initial
	/// Position with Playing off), its Post Process Anim Blueprint on or off, with Follower in Leader Pose. One line
	/// per curve: the leader's curve value, the leader's morph target weight and the follower's morph target weight
	/// of that name (-1 if the mesh has no such morph target). Editor only.
	UFUNCTION(BlueprintCallable, Category = "Editor|Checks")
	static FString FollowerMorphReport(USkeletalMesh* Leader, USkeletalMesh* Follower, UAnimSequence* Anim, float Time,
		bool bPostProcess, const TArray<FName>& Curves);
};
