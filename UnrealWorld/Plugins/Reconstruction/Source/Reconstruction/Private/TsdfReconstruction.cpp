#include "TsdfReconstruction.h"
#include "HAL/PlatformTime.h"

THIRD_PARTY_INCLUDES_START
#include <open_chisel/Chisel.h>
#include <open_chisel/ProjectionIntegrator.h>
#include <open_chisel/camera/DepthImage.h>
#include <open_chisel/camera/PinholeCamera.h>
#include <open_chisel/truncation/Truncator.h>
#include <open_chisel/weighting/Weighter.h>
THIRD_PARTY_INCLUDES_END

#include <algorithm>
#include <cmath>
#include <deque>
#include <limits>
#include <memory>
#include <mutex>
#include <unordered_map>

namespace
{
    chisel::ChunkID ToChunkId(const FIntVector& Key) { return chisel::ChunkID(Key.X, Key.Y, Key.Z); }
    FIntVector ToKey(const chisel::ChunkID& Id) { return FIntVector(Id.x(), Id.y(), Id.z()); }

    // ARCore's sensor pose as the camera-to-world extrinsic OpenChisel wants.
    // The pose is OpenGL convention (+Y up, looking down -Z); the integrator is
    // computer vision convention (+Y down, +Z forward, depth read off .z()). So
    // the rotation is composed with a flip of Y and Z.
    chisel::Transform ToExtrinsic(const float Pose[7])
    {
        const Eigen::Quaternionf Rotation(Pose[3], Pose[0], Pose[1], Pose[2]); // w first
        chisel::Transform T = chisel::Transform::Identity();
        T.linear() = Rotation.toRotationMatrix() * Eigen::DiagonalMatrix<float, 3>(1.0f, -1.0f, -1.0f);
        T.translation() = Eigen::Vector3f(Pose[4], Pose[5], Pose[6]);
        return T;
    }
}

struct FTsdfReconstruction::FImpl
{
    FTsdfConfig Config;
    std::unique_ptr<chisel::Chisel> Chisel;
    chisel::ProjectionIntegrator Integrator;
    chisel::PinholeCamera Camera;

    // chisel::DepthImage owns its buffer (delete[] in the destructor), so it
    // can't point at ARCore's memory. Allocated once and written into.
    std::shared_ptr<chisel::DepthImage<float>> Depth;
    // Per-pixel integration weights from the confidence map, same layout as Depth.
    std::shared_ptr<chisel::DepthImage<float>> Weights;

    std::mutex MeshMutex;

    // The current remesh cycle. Refilled from Chisel's dirty set only when empty:
    // draining the dirty set from begin() every frame starves whatever hashes
    // into the later buckets, and those chunks never get meshed.
    std::deque<chisel::ChunkID> RemeshQueue;

    // Chunks whose last mesh was non-empty, so losing a surface can be reported.
    std::unordered_map<chisel::ChunkID, bool, chisel::ChunkHasher> Live;

    FTsdfStats Stats;

    FVector3f OriginOf(const chisel::ChunkID& Id) const
    {
        const float Edge = Config.ChunkVoxels * Config.VoxelMetres;
        return FVector3f(Id.x() * Edge, Id.y() * Edge, Id.z() * Edge);
    }
};

FTsdfReconstruction::FTsdfReconstruction(const FTsdfConfig& Config)
    : Impl(MakeUnique<FImpl>())
{
    FImpl& I = *Impl;
    I.Config = Config;
    const Eigen::Vector3i ChunkSize(Config.ChunkVoxels, Config.ChunkVoxels, Config.ChunkVoxels);
    // No colour yet: geometry first. Fixed at construction, chunks allocate
    // their colour arrays (or don't) when they're created.
    I.Chisel = std::make_unique<chisel::Chisel>(ChunkSize, Config.VoxelMetres, false);

    I.Integrator.SetCentroids(I.Chisel->GetChunkManager().GetCentroids());
    I.Integrator.SetTruncator(chisel::Truncator::Constant(Config.TruncationMetres));
    I.Integrator.SetWeighter(chisel::Weighter(1.0f));
    I.Integrator.SetRangeWeighting(false);
    I.Integrator.SetCarvingEnabled(Config.bCarving);
    I.Integrator.SetCarvingDist(Config.CarvingDistance);
    I.Integrator.SetCarvingDecay(Config.CarvingDecay, Config.CarvingMinWeight, Config.CarvingRate);
    I.Integrator.SetMaxWeight(Config.MaxWeight);

    I.Camera.SetNearPlane(Config.NearPlane);
    I.Camera.SetFarPlane(Config.FarPlane);
}

FTsdfReconstruction::~FTsdfReconstruction() = default;

bool FTsdfReconstruction::Integrate(const FTsdfDepthFrame& Frame)
{
    FImpl& I = *Impl;
    const FTsdfConfig& C = I.Config;
    if (!Frame.DepthMm || Frame.Width <= 0 || Frame.Height <= 0 || Frame.Fx <= 0 || Frame.Fy <= 0)
        return false;

    if (!I.Depth || I.Depth->GetWidth() != Frame.Width || I.Depth->GetHeight() != Frame.Height)
    {
        I.Depth = std::make_shared<chisel::DepthImage<float>>(Frame.Width, Frame.Height);
        I.Weights = std::make_shared<chisel::DepthImage<float>>(Frame.Width, Frame.Height);
        I.Integrator.SetWeights(I.Weights);
    }

    // Millimetres to metres, and 0 (no estimate) to NaN: the integrator's only
    // guard is isnan, and a 0 would read as a surface at the lens and carve a
    // hole wherever ARCore wasn't sure.
    constexpr float NaN = std::numeric_limits<float>::quiet_NaN();
    // No confidence map means "no opinion", not "no confidence": fuse at weight 1.
    const bool bUseConfidence = Frame.Confidence && Frame.ConfidenceRowStrideBytes > 0 && C.ConfidenceThreshold > 0;
    const float Floor = FMath::Clamp(C.ConfidenceWeightFloor, 0.0f, 1.0f);
    const float Base = C.ConfidenceThreshold;
    const float Span = FMath::Max(255.0f - Base, 1.0f);
    const bool bSquared = C.ConfidenceWeightExponent == 2.0f;

    float* DepthOut = I.Depth->GetMutableData();
    float* WeightOut = I.Weights->GetMutableData();
    const uint8* DepthBase = reinterpret_cast<const uint8*>(Frame.DepthMm);
    int32 Fused = 0;
    for (int32 Row = 0; Row < Frame.Height; ++Row)
    {
        const uint16* Src = reinterpret_cast<const uint16*>(DepthBase + Row * Frame.RowStrideBytes);
        const uint8* Conf = bUseConfidence ? Frame.Confidence + Row * Frame.ConfidenceRowStrideBytes : nullptr;
        float* D = DepthOut + Row * Frame.Width;
        float* W = WeightOut + Row * Frame.Width;
        for (int32 Col = 0; Col < Frame.Width; ++Col)
        {
            W[Col] = 0.0f;
            D[Col] = NaN;
            const uint16 Mm = Src[Col];
            if (Mm == 0)
                continue;
            // Gate before the range check: the wildest readings are the ones
            // ARCore trusts least, and they mustn't stretch the ray walk.
            if (Conf && Conf[Col] < C.ConfidenceThreshold)
                continue;
            const float Metres = Mm * 0.001f;
            if (Metres < C.NearPlane || Metres > C.FarPlane)
                continue;
            float Weight = 1.0f;
            if (Conf)
            {
                const float T = (Conf[Col] - Base) / Span;
                const float Shaped = bSquared ? T * T : std::pow(T, C.ConfidenceWeightExponent);
                Weight = Floor + (1.0f - Floor) * Shaped;
            }
            D[Col] = Metres;
            W[Col] = Weight;
            ++Fused;
        }
    }
    I.Stats.FusedSamples = Fused;
    // An all-NaN image would cost a full scan in IntegrateDepthScan for nothing.
    if (Fused == 0)
        return false;

    // Re-read every frame: intrinsics are allowed to change.
    chisel::Intrinsics K;
    K.SetFx(Frame.Fx);
    K.SetFy(Frame.Fy);
    K.SetCx(Frame.Cx);
    K.SetCy(Frame.Cy);
    I.Camera.SetIntrinsics(K);
    I.Camera.SetWidth(Frame.Width);
    I.Camera.SetHeight(Frame.Height);

    const double Start = FPlatformTime::Seconds();
    I.Chisel->IntegrateDepthScan<float>(I.Integrator, I.Depth, ToExtrinsic(Frame.SensorPose), I.Camera);
    I.Stats.IntegrateMs = (FPlatformTime::Seconds() - Start) * 1000.0;
    I.Stats.ChunksTouched = static_cast<int32>(I.Chisel->GetLastChunksTouched());
    I.Stats.ChunksDiscarded = static_cast<int32>(I.Chisel->GetLastChunksDiscarded());
    I.Stats.ChunkCount = static_cast<int32>(I.Chisel->GetChunkManager().GetChunks().size());
    return true;
}

void FTsdfReconstruction::Remesh(int32 MaxChunks, TArray<FIntVector>& OutChanged, TArray<FIntVector>& OutRemoved)
{
    FImpl& I = *Impl;
    OutChanged.Reset();
    OutRemoved.Reset();
    if (MaxChunks <= 0)
        return;

    chisel::ChunkSet& Pending = I.Chisel->GetMutableMeshesToUpdate();
    chisel::ChunkManager& Chunks = I.Chisel->GetMutableChunkManager();
    if (I.RemeshQueue.empty() && !Pending.empty())
    {
        for (const auto& Entry : Pending)
            I.RemeshQueue.push_back(Entry.first);
        Pending.clear();
    }

    int32 Done = 0;
    while (!I.RemeshQueue.empty() && Done < MaxChunks)
    {
        const chisel::ChunkID Id = I.RemeshQueue.front();
        I.RemeshQueue.pop_front();
        // Integration dirties a 3x3x3 neighbourhood, which reaches chunks that
        // were never allocated.
        if (!Chunks.HasChunk(Id))
            continue;
        Chunks.RecomputeMesh(Id, I.MeshMutex);
        ++Done;

        const chisel::MeshMap& Meshes = Chunks.GetAllMeshes();
        const auto Found = Meshes.find(Id);
        const bool bHasSurface = Found != Meshes.end() && Found->second && !Found->second->vertices.empty();
        if (bHasSurface)
        {
            I.Live[Id] = true;
            OutChanged.Add(ToKey(Id));
        }
        else if (I.Live.erase(Id) > 0)
        {
            OutRemoved.Add(ToKey(Id));
        }
    }
}

bool FTsdfReconstruction::GetChunkMesh(const FIntVector& Key, FTsdfChunkMesh& Out) const
{
    const FImpl& I = *Impl;
    const chisel::ChunkID Id = ToChunkId(Key);
    const chisel::MeshMap& Meshes = I.Chisel->GetChunkManager().GetAllMeshes();
    const auto Found = Meshes.find(Id);
    if (Found == Meshes.end() || !Found->second)
        return false;
    const chisel::Mesh& Mesh = *Found->second;
    // Upstream asserts this and NDEBUG removes the assert; reading past the
    // end of normals would be a silent out-of-bounds read.
    if (Mesh.normals.size() != Mesh.vertices.size())
        return false;

    const FVector3f Origin = I.OriginOf(Id);
    const int32 VertexCount = static_cast<int32>(Mesh.vertices.size());
    Out.Positions.SetNumUninitialized(VertexCount);
    Out.Normals.SetNumUninitialized(VertexCount);
    for (int32 V = 0; V < VertexCount; ++V)
    {
        const chisel::Vec3& P = Mesh.vertices[V];
        const chisel::Vec3& N = Mesh.normals[V];
        Out.Positions[V] = FVector3f(P.x(), P.y(), P.z()) - Origin;
        Out.Normals[V] = FVector3f(N.x(), N.y(), N.z());
    }
    const int32 IndexCount = static_cast<int32>(Mesh.indices.size());
    Out.Indices.SetNumUninitialized(IndexCount);
    for (int32 Idx = 0; Idx < IndexCount; ++Idx)
        Out.Indices[Idx] = static_cast<uint32>(Mesh.indices[Idx]);
    return true;
}

FVector3f FTsdfReconstruction::GetChunkOrigin(const FIntVector& Key) const
{
    return Impl->OriginOf(ToChunkId(Key));
}

int32 FTsdfReconstruction::GetPendingRemeshCount() const
{
    return static_cast<int32>(Impl->RemeshQueue.size() + Impl->Chisel->GetMeshesToUpdate().size());
}

const FTsdfStats& FTsdfReconstruction::GetLastStats() const { return Impl->Stats; }
const FTsdfConfig& FTsdfReconstruction::GetConfig() const { return Impl->Config; }
