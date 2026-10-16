#pragma once
// The game-facing side of the TSDF. Everything OpenChisel and Eigen stays in the
// .cpp, behind FImpl: this header must never include <open_chisel/...> or name an
// Eigen type, or every module that includes it starts compiling Eigen with its
// own flags (see adding_open_chisel.md, Step 4).
//
// Space: everything here is in ARCore's tracking space. Right-handed, metres,
// +Y up. Converting to Unreal is the caller's job, so it happens in one place.

#include "CoreMinimal.h"

struct FTsdfConfig
{
    // A chunk is ChunkVoxels^3 voxels, so 16 at 4 cm is a 64 cm cube.
    int32 ChunkVoxels = 16;
    float VoxelMetres = 0.04f;

    // Half-width of the band around each depth sample where the SDF is written.
    float TruncationMetres = 0.06f;

    // Ceiling on a voxel's accumulated weight. Unbounded means a voxel seen
    // hundreds of times can never be corrected by new evidence.
    float MaxWeight = 200.0f;

    // Free space between the camera and a surface erodes what's there.
    bool bCarving = true;
    float CarvingDistance = 0.05f; // metres, dead zone above the integration band
    float CarvingDecay = 0.85f;    // weight multiplier per carving observation
    float CarvingMinWeight = 0.5f; // below this the voxel resets to unobserved
    float CarvingRate = 2.0f;

    // Confidence 0..255. Below the threshold a sample is dropped; above it the
    // weight goes from WeightFloor to 1 along t^Exponent.
    uint8 ConfidenceThreshold = 32;
    float ConfidenceWeightFloor = 0.05f;
    float ConfidenceWeightExponent = 2.0f;

    // Metres. Depth outside this range is treated as no estimate.
    float NearPlane = 0.3f;
    float FarPlane = 3.0f;
};

// One raw depth image and what's needed to fuse it. The pointers are ARCore's own
// image memory, straight from FARFrameData, so they're only valid during the
// OnARFrame broadcast. Integrate copies what it needs and keeps nothing; calling
// it from another thread means copying the images first.
struct FTsdfDepthFrame
{
    const uint16* DepthMm = nullptr; // 0 = no estimate
    int32 Width = 0, Height = 0, RowStrideBytes = 0;
    const uint8* Confidence = nullptr; // optional
    int32 ConfidenceRowStrideBytes = 0;
    float Fx = 0, Fy = 0, Cx = 0, Cy = 0;
    float SensorPose[7] = {}; // qx qy qz qw tx ty tz, ARCore's raw sensor pose
};

// A chunk's surface, with positions relative to the chunk origin so the floats
// keep their precision however far the chunk is from the tracking origin.
struct FTsdfChunkMesh
{
    TArray<FVector3f> Positions;
    TArray<FVector3f> Normals;
    TArray<uint32> Indices;
};

struct FTsdfStats
{
    double IntegrateMs = 0;
    int32 FusedSamples = 0;
    int32 ChunksTouched = 0;
    int32 ChunksDiscarded = 0;
    int32 ChunkCount = 0;
};

class RECONSTRUCTION_API FTsdfReconstruction
{
public:
    explicit FTsdfReconstruction(const FTsdfConfig& Config);
    ~FTsdfReconstruction();
    FTsdfReconstruction(const FTsdfReconstruction&) = delete;
    FTsdfReconstruction& operator=(const FTsdfReconstruction&) = delete;

    // Fuses one depth image. Returns false if nothing in it survived the filters.
    bool Integrate(const FTsdfDepthFrame& Frame);

    // Runs marching cubes on up to MaxChunks dirty chunks. OutChanged gets the
    // chunks that now have a surface, OutRemoved those that had one and lost it.
    void Remesh(int32 MaxChunks, TArray<FIntVector>& OutChanged, TArray<FIntVector>& OutRemoved);

    bool GetChunkMesh(const FIntVector& Key, FTsdfChunkMesh& Out) const;
    FVector3f GetChunkOrigin(const FIntVector& Key) const;

    int32 GetPendingRemeshCount() const;
    const FTsdfStats& GetLastStats() const;
    const FTsdfConfig& GetConfig() const;

private:
    struct FImpl;
    TUniquePtr<FImpl> Impl;
};
