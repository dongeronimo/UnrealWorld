#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
// Complete type for TUniquePtr's destructor in generated code. Safe to include
// anywhere: it has no Eigen or OpenChisel in it by design.
#include "TsdfReconstruction.h"
#include "ReconstructionActor.generated.h"
struct FARFrameData;
class AReconChunkActor;
class UMaterialInterface;

// The reconstructed world. Keeps a TSDF and one AReconChunkActor per chunk with
// a surface, attached to this actor. The TSDF comes from one of two places,
// decided once at BeginPlay:
//
// - Loaded: the game mode's UReconstructionPersistence has a world selected.
//   This actor asks for it, builds the TSDF from the file's own config (not the
//   settings below) and freezes: no ARCore, no pawn following. The fixture.
// - Live: otherwise. Listens to UARSessionStarter::OnARFrame and fuses raw depth
//   and camera colour as they come.
//
// Saving is the persistence's job too; this actor only hands out a snapshot
// (CaptureSnapshot). See Recon.Save in ReconstructionCommands.cpp.
//
// This actor's transform is ARCore tracking space -> Unreal world: every chunk
// sits under it at its chunk origin, so moving this one actor moves the whole
// room. Today that's the player pawn's transform, copied on tick, because the AR
// camera is a child of the pawn and its relative transform is the tracking pose.
// Later this is where an ARCore anchor goes.
//
// Abstract: what gets placed in a level is a blueprint subclass, and that
// blueprint is where the assets (ChunkMaterial) and the settings are chosen.
// Nothing here looks an asset up by path.
UCLASS(Abstract, Blueprintable)
class AReconstructionActor : public AActor {
    GENERATED_BODY()
public:
    AReconstructionActor();
    virtual void Tick(float DeltaSeconds) override;

    // A copy of the whole field and the config it ran with. False before
    // BeginPlay. Costs a copy of every voxel: a debug command, not per frame.
    bool CaptureSnapshot(FTsdfSnapshot& Out) const;
    bool IsLoadedFromFile() const { return bLoadedFromFile; }

    // Unshaded is deliberate: an empty AR level has no lights.
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category = "Reconstruction")
    TObjectPtr<UMaterialInterface> ChunkMaterial;

    // The settings below are read once, at BeginPlay, and only when live: a
    // loaded world brings its own.
    UPROPERTY(EditAnywhere, Category = "Reconstruction", meta = (ClampMin = "0.005", ClampMax = "0.2"))
    float VoxelMetres = 0.04f;

    UPROPERTY(EditAnywhere, Category = "Reconstruction", meta = (ClampMin = "4", ClampMax = "32"))
    int32 ChunkVoxels = 16;

    UPROPERTY(EditAnywhere, Category = "Reconstruction", meta = (ClampMin = "0.01", ClampMax = "0.5"))
    float TruncationMetres = 0.06f;

    UPROPERTY(EditAnywhere, Category = "Reconstruction", meta = (ClampMin = "0.1", ClampMax = "10"))
    float NearPlaneMetres = 0.3f;

    UPROPERTY(EditAnywhere, Category = "Reconstruction", meta = (ClampMin = "0.5", ClampMax = "10"))
    float FarPlaneMetres = 3.0f;

    UPROPERTY(EditAnywhere, Category = "Reconstruction")
    bool bCarving = true;

    UPROPERTY(EditAnywhere, Category = "Reconstruction", meta = (ClampMin = "0", ClampMax = "255"))
    int32 ConfidenceThreshold = 32;

    // Fuse the camera image into the voxels and colour the mesh with it. The
    // vertex colour is gamma encoded RGB; alpha is how much colour evidence
    // stands behind it (0 = never seen in colour), for the material to fall
    // back on a flat colour.
    UPROPERTY(EditAnywhere, Category = "Reconstruction")
    bool bIntegrateColor = true;

    // Marching cubes per tick. A sweep dirties hundreds of chunks at once;
    // meshing them all in one frame is a dropped frame.
    UPROPERTY(EditAnywhere, Category = "Reconstruction", meta = (ClampMin = "1"))
    int32 RemeshBudgetPerTick = 8;

    // Copy the player pawn's transform onto this actor every tick. Live only:
    // a loaded world stays where the level put it.
    UPROPERTY(EditAnywhere, Category = "Reconstruction")
    bool bFollowPawnOrigin = true;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    bool TryLoadFromPersistence();
    void StartLive();
    void HandleFrame(const FARFrameData& Frame);
    void ApplyRemesh();
    void LogStats(float DeltaSeconds);

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<USceneComponent> Root;

    UPROPERTY(Transient)
    TMap<FIntVector, TObjectPtr<AReconChunkActor>> ChunkActors;

    TUniquePtr<FTsdfReconstruction> Tsdf;
    FDelegateHandle FrameHandle;
    int64 LastDepthTimestampNs = 0;
    bool bLoadedFromFile = false;

    // Once a second: what happened since the last log line.
    float SecondsSinceLog = 0;
    int32 FramesSeen = 0, FramesIntegrated = 0, FramesRepeatedDepth = 0, FramesNotTracking = 0;
    int32 ChunksMeshed = 0;
    double IntegrateMsTotal = 0;
};
