#include "Drow.h"

#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
	struct FPiece
	{
		const TCHAR* Name;   // the Blender object; the asset is /Game/Chars/Drow/Pieces/Drow_<Name>
		bool bPilot;         // worn by default: the step 5 pilot (jacket, pants, boots, braid) and what holds the props
	};

	const FPiece PieceList[] = {
		{TEXT("Jacket"), true}, {TEXT("Shirt"), false}, {TEXT("Gym_Top"), false},
		{TEXT("Cargo_Pants"), true}, {TEXT("Miniskirt"), false}, {TEXT("Bikini_Bottom"), false},
		{TEXT("Boots"), true}, {TEXT("Tennis"), false},
		{TEXT("Hair_Braid"), true}, {TEXT("Hair_Ponytail"), false}, {TEXT("Hair_High_Bum"), false},
		{TEXT("Choker"), false}, {TEXT("Holster"), true}, {TEXT("Katana_Sheat"), true},
	};

	UStaticMeshComponent* MakeProp(ACharacter* Owner, const TCHAR* Name, const TCHAR* Asset, FName Socket)
	{
		UStaticMeshComponent* Prop = Owner->CreateDefaultSubobject<UStaticMeshComponent>(Name);
		ConstructorHelpers::FObjectFinder<UStaticMesh> Mesh(Asset);
		Prop->SetStaticMesh(Mesh.Object);
		// Zero relative transform on the socket is the guide's Snap to Target.
		Prop->SetupAttachment(Owner->GetMesh(), Socket);
		Prop->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
		return Prop;
	}
}

ADrow::ADrow()
{
	PrimaryActorTick.bCanEverTick = false;

	// 1.843 m in the rest pose (Drow_export.log, aplicar_escala). The root bone is at her feet, so the mesh drops
	// by the half height to put them on the capsule's floor.
	const float HalfHeight = 92.f;
	GetCapsuleComponent()->InitCapsuleSize(35.f, HalfHeight);

	USkeletalMeshComponent* Body = GetMesh();
	// Single clip until she has an Anim Blueprint, as Fearing: Mesh > Animation > Anim to Play.
	Body->SetAnimationMode(EAnimationMode::AnimationSingleNode, false);
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> BodyAsset(TEXT("/Game/Chars/Drow/Drow.Drow"));
	Body->SetSkeletalMeshAsset(BodyAsset.Object);
	// Blender's -Y front arrives as Unreal +Y after the FBX Y flip; turn it onto the actor's +X.
	Body->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -HalfHeight), FRotator(0.f, -90.f, 0.f));

	for (const FPiece& P : PieceList)
	{
		USkeletalMeshComponent* Piece = CreateDefaultSubobject<USkeletalMeshComponent>(P.Name);
		const FString Path = FString::Printf(TEXT("/Game/Chars/Drow/Pieces/Drow_%s.Drow_%s"), P.Name, P.Name);
		ConstructorHelpers::FObjectFinder<USkeletalMesh> Asset(*Path);
		Piece->SetSkeletalMeshAsset(Asset.Object);
		Piece->SetupAttachment(Body);
		Piece->SetCollisionProfileName(UCollisionProfile::NoCollision_ProfileName);
		// Bounds from the body: a follower's own bounds sit at its rest pose and would cull it mid-clip.
		Piece->bUseBoundsFromLeaderPoseComponent = true;
		Piece->SetVisibility(P.bPilot);
		Pieces.Add(Piece);
	}

	Katana = MakeProp(this, TEXT("Katana"), TEXT("/Game/Chars/Drow/Props/Katana.Katana"), TEXT("katana_bainha"));
	Katana->ComponentTags.Add(TEXT("Katana"));
	Pistol = MakeProp(this, TEXT("Pistol"), TEXT("/Game/Chars/Drow/Props/Pistol.Pistol"), TEXT("pistola_coldre"));
	Glasses = MakeProp(this, TEXT("Glasses"), TEXT("/Game/Chars/Drow/Props/Glass_Rayban.Glass_Rayban"), TEXT("glass_rayban"));
	Headphone = MakeProp(this, TEXT("Headphone"), TEXT("/Game/Chars/Drow/Props/Kitty_Headphone.Kitty_Headphone"), TEXT("kitty_headphone"));
}

void ADrow::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	// Here and not in the constructor: the leader is a weak pointer, not a property, so it is neither saved nor
	// copied from the class defaults. OnConstruction runs for every instance, in the editor and when spawned.
	for (USkeletalMeshComponent* Piece : Pieces)
	{
		if (Piece)
		{
			Piece->SetLeaderPoseComponent(GetMesh());
		}
	}
}
