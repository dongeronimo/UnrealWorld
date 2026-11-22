#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Drow.generated.h"

class USkeletalMeshComponent;
class UStaticMeshComponent;

/// <summary>
/// The drow (gothic dark elf, still unnamed). Unlike Fearing she is modular: the mesh (Drow) is only her body and
/// face, and each garment, hair, the holster and the scabbard is its own skeletal mesh on the same skeleton
/// (gurps exportar_pacote_unreal.py --modular, import_drow.py). The outfits are alternatives over the same
/// region (jacket / shirt / gym top, pants / miniskirt / bikini, boots / tennis), so one merged mesh would need
/// one asset per combination.
///
/// Every piece follows the body by Leader Pose: it runs no animation of its own, and takes the body's bones and
/// its morph curves by name. So CR_Drow, the Post Process Anim Blueprint on the Drow mesh asset, drives the
/// CORR_* correctives of the jacket and the pants too (SkeletalMeshComponent.cpp, UpdateFollowerComponent).
///
/// Pieces are components named as in Blender; pick the outfit with each one's Visible flag. The pilot outfit
/// (drow handoff, step 5) is on by default. The skin under a piece still renders until the body masks
/// (step 9).
///
/// Props are Sophia's, refitted in Blender (armas_sophia.py, acessorios_cabeca.py): static meshes on sockets of
/// the Drow mesh, never children of a bone. The katana moves between katana_bainha and katana_mao by
/// UAnimNotify_AttachToSocket on the clips (notifies_drow.py), which finds it by the Katana tag.
/// </summary>
UCLASS()
class UNREALWORLD_API ADrow : public ACharacter
{
	GENERATED_BODY()

public:
	ADrow();

	virtual void OnConstruction(const FTransform& Transform) override;

	/// Every piece, in the order of PieceNames. Visible = worn.
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Outfit")
	TArray<TObjectPtr<USkeletalMeshComponent>> Pieces;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gear")
	TObjectPtr<UStaticMeshComponent> Katana;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gear")
	TObjectPtr<UStaticMeshComponent> Pistol;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gear")
	TObjectPtr<UStaticMeshComponent> Glasses;

	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Gear")
	TObjectPtr<UStaticMeshComponent> Headphone;
};
