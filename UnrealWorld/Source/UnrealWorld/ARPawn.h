#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "ARPawn.generated.h"
class UCameraComponent;
class USceneComponent;

// The player's pawn. It is clear that the pawn that
// the player possess is the one that represents his
// position in the AR world.
UCLASS()
class AARPawn : public APawn {
    GENERATED_BODY()
public:
    AARPawn();
private:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, meta = (AllowPrivateAccess = "true"))
    TObjectPtr<UCameraComponent> Camera;
    /// <summary>
    /// The AR Tracking origin. The pawn's transform says where the
    /// phone's tracking space sits in the Unreal world.
    /// </summary>
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<USceneComponent> Root;

};