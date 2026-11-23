
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "Drow.generated.h"

class USkeletalMeshComponent;
class UStaticMeshComponent;
/// <summary>
/// What is her weapon state? 
/// </summary>
UENUM(BlueprintType)
enum class EDrowWeaponState : uint8 {
	/// <summary>
	/// She's unarmed
	/// </summary>
	Unarmed,
	/// <summary>
	/// She is doing a weapon transition.
	/// </summary>
	ChangingWeapon,
	/// <summary>
	/// She is with the katana unsheated and pistol in the holster
	/// </summary>
	Katana,
	/// <summary>
	/// She is with the pistol in hands and katana sheated.
	/// </summary>
	Pistol,
	/// <summary>
	/// She's reloading the pistol.
	/// </summary>
	ReloadingPistol,
	Count
};

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
/// Pieces are components named as in Blender; pick the outfit with each one's Visible flag (or SetPieceWorn in
/// game). The pilot outfit (drow handoff, step 5) is on by default.
///
/// Body masks (drow handoff, step 9): the skin under a worn piece is not drawn, so it cannot poke through. The mask
/// textures (gurps generate_outfit_masks.py, one slot per piece) are read on UV 1 by M_Drow_Masked, whose World
/// Position Offset returns NaN for a hidden vertex of a worn slot: the GPU drops every triangle touching it, in the
/// shadow pass too. The Shirt and the Gym_Top are masked the same way under the Jacket. UpdateBodyMasks turns the
/// visible pieces into the Wear parameters; it runs on construction, so the Visible flags drive it in the editor.
///
/// Props are Sophia's, refitted in Blender (armas_sophia.py, acessorios_cabeca.py): static meshes on sockets of
/// the Drow mesh, never children of a bone. The katana moves between katana_bainha and katana_mao by
/// UAnimNotify_AttachToSocket on the clips (notifies_drow.py), which finds it by the Katana tag.
/// ---------------------------------------------------------------------------------------
/// Setting up game properties:
/// - HP and Bullet properties are managed via the Update* function family (ex.: UpdateHP). They take THE DELTAS. The 
///   idea is that I set the values in the blueprint's construction script, so that I don't recompile every time i have 
///   to do a balance change.
/// </summary>
UCLASS()
class UNREALWORLD_API ADrow : public ACharacter
{
	GENERATED_BODY()

public:
	ADrow();

	virtual void OnConstruction(const FTransform& Transform) override;

	/// Puts a piece (a component name, e.g. Jacket) on or off, and updates the body masks.
	UFUNCTION(BlueprintCallable, Category = "Outfit")
	void SetPieceWorn(FName Piece, bool bWorn);

	/// Wear/Wear2 on every M_Drow_Masked material from the visible pieces. Call it after changing a Visible flag
	/// by hand; SetPieceWorn calls it.
	UFUNCTION(BlueprintCallable, Category = "Outfit")
	void UpdateBodyMasks();

	/// The piece component with this name, or null.
	UFUNCTION(BlueprintPure, Category = "Outfit")
	USkeletalMeshComponent* FindPiece(FName Piece) const;

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

	UFUNCTION(BlueprintCallable)
	void UpdateHP(float change);

	UFUNCTION(BlueprintCallable)
	void UpdateTotalAmmo(float change);

	UFUNCTION(BlueprintCallable)
	void UpdateMagazineCapacity(float change);

	UFUNCTION(BlueprintCallable)
	void ResetMagazine();

	UFUNCTION(BlueprintCallable)
	void UpdateBulletDamage(float change);

	UFUNCTION(BlueprintCallable)
	void UpdateKatanaDamage(float change);
protected:
	/// <summary>
	/// Current weapon
	/// </summary>
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "State")
	EDrowWeaponState CurrentWeaponState = EDrowWeaponState::Unarmed;
	/// <summary>
	/// Previous weapon. We need that because we need to manage transitions.
	/// </summary>
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "State")
	EDrowWeaponState PreviousWeaponState = EDrowWeaponState::Unarmed;
	/// <summary>
	/// HP da drow
	/// </summary>
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "State")
	float HP;
	/// <summary>
	/// How many bullets left in the magazine?
	/// </summary>
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "State")
	int CurrentAmmoInMagazine;
	/// <summary>
	/// How many bullets can the mag hold?
	/// </summary>
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "State")
	int MagazineCapacity;
	/// <summary>
	/// The total amount of ammo she has. Every time she reloads, TotalAmmo = TotalAmmo - MagazineCapacity.
	/// </summary>
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "State")
	int TotalAmmo;
	/// <summary>
	/// How much damage the katana does?
	/// </summary>
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "State")
	float KatanaDamage;
	/// <summary>
	/// How much damage the bullet do.
	/// </summary>
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "State")
	float BulletDamage;
};
