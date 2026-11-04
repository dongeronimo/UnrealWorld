#include "AnimNotify_AttachToSocket.h"

#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

void UAnimNotify_AttachToSocket::Notify(USkeletalMeshComponent* MeshComp, UAnimSequenceBase* Animation,
	const FAnimNotifyEventReference& EventReference)
{
	Super::Notify(MeshComp, Animation, EventReference);
	AActor* Owner = MeshComp ? MeshComp->GetOwner() : nullptr;
	if (!Owner)
	{
		return;
	}
	USceneComponent* Prop = Owner->FindComponentByTag<USceneComponent>(ComponentTag);
	if (!Prop)
	{
		// The animation editors' preview actor carries no props; only a game world is a real miss.
		if (MeshComp->GetWorld() && MeshComp->GetWorld()->IsGameWorld())
		{
			UE_LOG(LogTemp, Warning, TEXT("AttachToSocket: %s has no component tagged %s"),
				*Owner->GetName(), *ComponentTag.ToString());
		}
		return;
	}
	// The guide's rules: snap location and rotation onto the socket, keep the prop's world scale.
	const FAttachmentTransformRules Rules(EAttachmentRule::SnapToTarget, EAttachmentRule::SnapToTarget,
		EAttachmentRule::KeepWorld, false);
	Prop->AttachToComponent(MeshComp, Rules, Socket);
}

FString UAnimNotify_AttachToSocket::GetNotifyName_Implementation() const
{
	return FString::Printf(TEXT("%s -> %s"), *ComponentTag.ToString(), *Socket.ToString());
}
