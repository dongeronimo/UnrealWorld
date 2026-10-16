#pragma once
#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "ReconstructionPersistence.generated.h"
struct FTsdfSnapshot;

// Where reconstructions go when they're saved and where they come from when
// they're loaded. The one place in the game that knows there are files.
//
// A recorded room is a fixture: captured once on a phone, it loads on the
// desktop with no ARCore and no camera, so navmesh, materials and collision can
// be worked on in PIE, repeatably, with nobody walking a room.
//
// Lives on the game mode (AReconGameModeBase::Persistence), instanced, so each
// game mode blueprint configures its own: the AR one loads nothing and saves on
// Recon.Save, the fixture one has WorldToLoad picked from a dropdown.
//
// Files are Saved/<Folder>/<name>.tsdf on every platform. On a device that's
// the only writable place; on the desktop it's where Tools/recon.py pulls to.
//
// ## Format, version 1
//
// Little-endian, uncompressed, everything an FTsdfSnapshot holds:
//
//     uint32 magic 'TSDF', uint32 version
//     FTsdfConfig, field by field (see SerializeConfig)
//     int32 chunk count, then per chunk:
//         int32 x, y, z
//         float sdf[N], float weight[N]      N = ChunkVoxels^3, OpenChisel order
//         uint8 has colour
//         uint8 rgbw[N * 4]                  only if has colour
//
// The config is saved whole, not just what indexes the voxels: marching cubes
// and the mesh colours depend on it too, and loading it rather than the level's
// settings is what makes a loaded room mesh into the same triangles.
UCLASS(EditInlineNew, DefaultToInstanced, CollapseCategories)
class UReconstructionPersistence : public UObject {
    GENERATED_BODY()
public:
    // Under the project's Saved directory.
    UPROPERTY(EditAnywhere, Category = "Persistence")
    FString Folder = TEXT("Recon");

    // The world LoadSelected hands out. Empty means none: the reconstruction
    // runs live from ARCore. ?ReconWorld=<name> on the URL overrides it.
    UPROPERTY(EditAnywhere, Category = "Persistence", meta = (GetOptions = "GetWorldNames"))
    FString WorldToLoad;

    // Writes Saved/<Folder>/<Name>.tsdf, replacing any file of that name.
    // OutPath is absolute, as adb would want it.
    bool Save(const FTsdfSnapshot& Snapshot, const FString& Name, FString& OutPath) const;
    bool Load(const FString& Name, FTsdfSnapshot& Out) const;
    // Load(WorldToLoad). False, quietly, when WorldToLoad is empty.
    bool LoadSelected(FTsdfSnapshot& Out) const;

    // Names (no extension) of the worlds in the folder, sorted. The first entry
    // is empty, so "load nothing" can be picked in the editor too.
    UFUNCTION()
    TArray<FString> GetWorldNames() const;

    FString GetDirectory() const;

private:
    FString PathFor(const FString& Name) const;
};
