#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "AnimNotify_AttachToSocket.generated.h"

/// <summary>
/// Moves a prop the owning actor carries onto a socket of the mesh playing the clip: the katana from
/// scabbard to hand on the draw, and back on the sheathe.
///
/// A notify class instead of a Skeleton Notify handled in an Anim Blueprint's Event Graph: the clip
/// carries the whole instruction (which prop, which socket), so it works under any Anim Blueprint or
/// none, and there is no graph to keep in step with the clips.
///
/// The prop is found by component tag, so any character with weapons on sockets can use it.
/// </summary>
UCLASS(meta = (DisplayName = "Attach To Socket"))
class UNREALWORLD_API UAnimNotify_AttachToSocket : public UAnimNotify
{
	GENERATED_BODY()

public:
	/// Tag of the component to move. "Katana" is the tag ASpaceAmazon gives hers.
	UPROPERTY(EditAnywhere, Category = "Attach")
	FName ComponentTag = TEXT("Katana");

	/// Socket on the mesh playing the clip, e.g. katana_mao or katana_bainha.
	UPROPERTY(EditAnywhere, Category = "Attach")
	FName Socket;

	virtual void Notify(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation,
		const FAnimNotifyEventReference& EventReference) override;
	virtual FString GetNotifyName_Implementation() const override;
};
