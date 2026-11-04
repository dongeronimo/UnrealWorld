#include "SpaceAmazon.h"

#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"
DEFINE_LOG_CATEGORY(SpaceAmazonLog);
const FName ASpaceAmazon::KatanaTag(TEXT("Katana"));

ASpaceAmazon::ASpaceAmazon()
{
	PrimaryActorTick.bCanEverTick = false;

	// 1.799 m standing in the rest pose (SpaceAmazon_export.log, aplicar_escala). The root bone is at
	// her feet, so the mesh drops by the half height to put them on the capsule's floor.
	const float HalfHeight = 90.f;
	GetCapsuleComponent()->InitCapsuleSize(35.f, HalfHeight);

	USkeletalMeshComponent* Body = GetMesh();
	// TODO: Remove this shit when adding ABP
	// Single clip until she has an Anim Blueprint: pick it per instance under Mesh > Animation >
	// Anim to Play. Set before the mesh asset, so the setter only records the mode.
	Body->SetAnimationMode(EAnimationMode::AnimationSingleNode, false);
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> BodyAsset(TEXT("/Game/Chars/SpaceAmazon/SpaceAmazon.SpaceAmazon"));
	Body->SetSkeletalMeshAsset(BodyAsset.Object);
	// Blender's -Y front arrives as Unreal +Y after the FBX Y flip; turn it onto the actor's +X.
	Body->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -HalfHeight), FRotator(0.f, -90.f, 0.f));


	Katana = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Katana"));
	// The mesh is chosen in the Blueprint (select the inherited Katana > Static Mesh).
	// Zero relative transform on the socket is the guide's Snap to Target; she starts sheathed.
	Katana->SetupAttachment(Body, TEXT("katana_bainha"));
	Katana->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
	Katana->ComponentTags.Add(KatanaTag);
}
