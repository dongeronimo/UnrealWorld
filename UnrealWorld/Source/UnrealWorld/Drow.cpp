#include "Drow.h"

#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialInterface.h"
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

	// The mask slots in channel order: Wear = R, G, B, A of masks_rgba.png, Wear2 = masks_rgba_2.png (gurps
	// outfits/drow.json "masks"; generate_outfit_masks.py writes the channels in that order).
	const TCHAR* const MaskSlots[8] = {
		TEXT("Jacket"), TEXT("Shirt"), TEXT("Gym_Top"), TEXT("Cargo_Pants"),
		TEXT("Miniskirt"), TEXT("Bikini_Bottom"), TEXT("Boots"), TEXT("Tennis"),
	};
	const FName MaskedMaterial(TEXT("M_Drow_Masked"));

	// Every section whose material is M_Drow_Masked (import_drow.py: the body's skin, the shirt, the gym top) gets a
	// dynamic instance with these. Found by the parent, not by slot index or name: a reimport may add slots.
	void SetMaskWear(USkeletalMeshComponent* Mesh, const FLinearColor& Wear, const FLinearColor& Wear2)
	{
		if (!Mesh)
		{
			return;
		}
		for (int32 i = 0; i < Mesh->GetNumMaterials(); ++i)
		{
			UMaterialInterface* M = Mesh->GetMaterial(i);
			if (!M || !M->GetBaseMaterial() || M->GetBaseMaterial()->GetFName() != MaskedMaterial)
			{
				continue;
			}
			// Reuses the dynamic instance already on the slot, so construction does not pile them up.
			if (UMaterialInstanceDynamic* MID = Mesh->CreateDynamicMaterialInstance(i))
			{
				MID->SetVectorParameterValue(TEXT("Wear"), Wear);
				MID->SetVectorParameterValue(TEXT("Wear2"), Wear2);
			}
		}
	}

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
	UpdateBodyMasks();
}

USkeletalMeshComponent* ADrow::FindPiece(FName Piece) const
{
	for (USkeletalMeshComponent* P : Pieces)
	{
		if (P && P->GetFName() == Piece)
		{
			return P;
		}
	}
	return nullptr;
}

void ADrow::UpdateHP(float change)
{
	this->HP = this->HP + change;
}

void ADrow::UpdateTotalAmmo(float change)
{
	this->TotalAmmo = this->TotalAmmo + change;
}

void ADrow::UpdateMagazineCapacity(float change)
{
	this->MagazineCapacity = this->MagazineCapacity + change;
}

void ADrow::ResetMagazine()
{
	if (this->MagazineCapacity == 0) {
		UE_LOG(LogTemp, Error, TEXT("ADrow::ResetMagazine: MagazineCapacity should not be zero"));
	}
	this->CurrentAmmoInMagazine = this->MagazineCapacity;
}

void ADrow::UpdateBulletDamage(float change)
{
	this->BulletDamage = this->BulletDamage + change;
}

void ADrow::UpdateKatanaDamage(float change)
{
	this->KatanaDamage = this->KatanaDamage + change;
}

void ADrow::SetPieceWorn(FName Piece, bool bWorn)
{
	if (USkeletalMeshComponent* P = FindPiece(Piece))
	{
		P->SetVisibility(bWorn);
		UpdateBodyMasks();
	}
}

void ADrow::UpdateBodyMasks()
{
	float W[8];
	for (int32 i = 0; i < 8; ++i)
	{
		const USkeletalMeshComponent* P = FindPiece(MaskSlots[i]);
		W[i] = P && P->GetVisibleFlag() ? 1.f : 0.f;
	}
	SetMaskWear(GetMesh(), FLinearColor(W[0], W[1], W[2], W[3]), FLinearColor(W[4], W[5], W[6], W[7]));
	// The shirt's and the gym top's own masks have one slot, the jacket over them (R of their masks_rgba.png).
	const FLinearColor UnderJacket(W[0], 0.f, 0.f, 0.f);
	SetMaskWear(FindPiece(TEXT("Shirt")), UnderJacket, FLinearColor::Transparent);
	SetMaskWear(FindPiece(TEXT("Gym_Top")), UnderJacket, FLinearColor::Transparent);
}
