#include "ReconstructionActor.h"
#include "ReconChunkActor.h"
#include "ARSessionStarter.h"
#include "ARFrameData.h"
#include "TsdfReconstruction.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/WorldSettings.h"
#include "Materials/MaterialInterface.h"

DEFINE_LOG_CATEGORY_STATIC(LogReconstruction, Log, All);

namespace {
    // ARCore (right-handed, metres, +Y up, -Z forward) to Unreal (left-handed,
    // centimetres, +Z up, +X forward). The same basis change as
    // MakeBlueprintPose in ARSessionStarter.cpp, and the only place the
    // reconstruction's geometry crosses it.
    //
    // It has determinant -1, so it mirrors and triangle winding flips. Unreal
    // also treats the opposite winding as front-facing compared to OpenChisel's
    // right-handed convention, and the two flips cancel: indices are copied
    // unchanged (ToySoldiers settled this on device by drawing both windings).
    FVector3f ToUnreal(const FVector3f& V, float WorldToMeters) {
        return FVector3f(-V.Z, V.X, V.Y) * WorldToMeters;
    }
    FVector3f ToUnrealDirection(const FVector3f& V) {
        return FVector3f(-V.Z, V.X, V.Y);
    }
}

AReconstructionActor::AReconstructionActor() {
    // Tick does the remeshing; frames arrive through OnARFrame before actors tick.
    PrimaryActorTick.bCanEverTick = true;
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    RootComponent = Root;
    Root->SetMobility(EComponentMobility::Movable);
}

void AReconstructionActor::BeginPlay() {
    Super::BeginPlay();
    FTsdfConfig Config;
    Config.VoxelMetres = VoxelMetres;
    Config.ChunkVoxels = ChunkVoxels;
    Config.TruncationMetres = TruncationMetres;
    Config.NearPlane = NearPlaneMetres;
    Config.FarPlane = FarPlaneMetres;
    Config.bCarving = bCarving;
    Config.ConfidenceThreshold = static_cast<uint8>(FMath::Clamp(ConfidenceThreshold, 0, 255));
    Tsdf = MakeUnique<FTsdfReconstruction>(Config);
    UE_LOG(LogReconstruction, Log, TEXT("RECON ready: %d^3 voxels of %.3f m (%.2f m chunks), truncation %.3f m, depth [%.2f, %.2f] m, carving %s, confidence >= %d"),
        ChunkVoxels, VoxelMetres, ChunkVoxels * VoxelMetres, TruncationMetres, NearPlaneMetres, FarPlaneMetres,
        bCarving ? TEXT("on") : TEXT("off"), ConfidenceThreshold);
    if (!ChunkMaterial)
        UE_LOG(LogReconstruction, Warning, TEXT("RECON has no ChunkMaterial set on %s, chunks will draw with the default material"), *GetClass()->GetName());

    if (UARSessionStarter* Starter = GetGameInstance()->GetSubsystem<UARSessionStarter>())
        FrameHandle = Starter->OnARFrame.AddUObject(this, &AReconstructionActor::HandleFrame);
}

void AReconstructionActor::EndPlay(const EEndPlayReason::Type EndPlayReason) {
    // The subsystem outlives the actor, so it has to forget us explicitly.
    if (UGameInstance* GameInstance = GetGameInstance())
        if (UARSessionStarter* Starter = GameInstance->GetSubsystem<UARSessionStarter>())
            Starter->OnARFrame.Remove(FrameHandle);
    FrameHandle.Reset();
    for (const TPair<FIntVector, TObjectPtr<AReconChunkActor>>& Pair : ChunkActors)
        if (Pair.Value)
            Pair.Value->Destroy();
    ChunkActors.Reset();
    Tsdf.Reset();
    Super::EndPlay(EndPlayReason);
}

void AReconstructionActor::HandleFrame(const FARFrameData& Frame) {
    ++FramesSeen;
    if (!Tsdf || !Frame.DepthMm)
        return;
    // A pose from a frame that isn't tracking would fuse depth in the wrong place.
    if (!Frame.bTracking) {
        ++FramesNotTracking;
        return;
    }
    // Depth updates slower than the camera. The same depth image on two camera
    // frames is one observation, and fusing it twice would carve twice.
    if (Frame.DepthTimestampNs == LastDepthTimestampNs) {
        ++FramesRepeatedDepth;
        return;
    }
    LastDepthTimestampNs = Frame.DepthTimestampNs;

    FTsdfDepthFrame Depth;
    Depth.DepthMm = Frame.DepthMm;
    Depth.Width = Frame.DepthWidth;
    Depth.Height = Frame.DepthHeight;
    Depth.RowStrideBytes = Frame.DepthRowStrideBytes;
    Depth.Confidence = Frame.Confidence;
    Depth.ConfidenceRowStrideBytes = Frame.ConfidenceRowStrideBytes;
    Depth.Fx = Frame.DepthFx;
    Depth.Fy = Frame.DepthFy;
    Depth.Cx = Frame.DepthCx;
    Depth.Cy = Frame.DepthCy;
    FMemory::Memcpy(Depth.SensorPose, Frame.SensorPose, sizeof(Depth.SensorPose));
    if (Tsdf->Integrate(Depth)) {
        ++FramesIntegrated;
        IntegrateMsTotal += Tsdf->GetLastStats().IntegrateMs;
    }
}

void AReconstructionActor::Tick(float DeltaSeconds) {
    Super::Tick(DeltaSeconds);
    if (bFollowPawnOrigin)
        if (APlayerController* PC = GetWorld()->GetFirstPlayerController())
            if (APawn* Pawn = PC->GetPawn())
                SetActorTransform(FTransform(Pawn->GetActorRotation(), Pawn->GetActorLocation()));
    ApplyRemesh();
    LogStats(DeltaSeconds);
}

void AReconstructionActor::ApplyRemesh() {
    if (!Tsdf)
        return;
    TArray<FIntVector> Changed, Removed;
    Tsdf->Remesh(RemeshBudgetPerTick, Changed, Removed);
    ChunksMeshed += Changed.Num();
    const float WorldToMeters = GetWorld()->GetWorldSettings()->WorldToMeters;

    // Hidden, not destroyed: a chunk that empties is usually one the sensor
    // hasn't seen enough of yet, and it comes back.
    for (const FIntVector& Key : Removed)
        if (TObjectPtr<AReconChunkActor>* Found = ChunkActors.Find(Key))
            if (*Found)
                (*Found)->ClearGeometry();

    FTsdfChunkMesh Mesh;
    TArray<FVector3f> Positions, Normals;
    for (const FIntVector& Key : Changed) {
        if (!Tsdf->GetChunkMesh(Key, Mesh))
            continue;
        AReconChunkActor* Chunk = nullptr;
        if (TObjectPtr<AReconChunkActor>* Found = ChunkActors.Find(Key))
            Chunk = *Found;
        if (!Chunk) {
            FActorSpawnParameters Params;
            Params.Owner = this;
            Params.SpawnCollisionHandlingOverride = ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
            Chunk = GetWorld()->SpawnActor<AReconChunkActor>(AReconChunkActor::StaticClass(), FTransform::Identity, Params);
            if (!Chunk)
                continue;
            // Relative: the chunk's own transform is its origin in tracking
            // space and nothing else; this actor carries tracking -> world.
            Chunk->AttachToActor(this, FAttachmentTransformRules::KeepRelativeTransform);
            Chunk->SetActorRelativeLocation(FVector(ToUnreal(Tsdf->GetChunkOrigin(Key), WorldToMeters)));
            ChunkActors.Add(Key, Chunk);
        }
        const int32 VertexCount = Mesh.Positions.Num();
        Positions.SetNumUninitialized(VertexCount, EAllowShrinking::No);
        Normals.SetNumUninitialized(VertexCount, EAllowShrinking::No);
        for (int32 V = 0; V < VertexCount; ++V) {
            Positions[V] = ToUnreal(Mesh.Positions[V], WorldToMeters);
            Normals[V] = ToUnrealDirection(Mesh.Normals[V]);
        }
        Chunk->SetGeometry(Positions, Normals, Mesh.Indices, ChunkMaterial);
    }
}

void AReconstructionActor::LogStats(float DeltaSeconds) {
    SecondsSinceLog += DeltaSeconds;
    if (SecondsSinceLog < 1.0f || !Tsdf)
        return;
    const FTsdfStats& Stats = Tsdf->GetLastStats();
    UE_LOG(LogReconstruction, Log,
        TEXT("RECON %.1fs: %d frames, %d integrated (%.1f ms mean), %d repeated depth, %d not tracking | last: %d samples fused, %d chunks touched, %d discarded | %d chunks, %d actors, %d meshed, %d awaiting remesh"),
        SecondsSinceLog, FramesSeen, FramesIntegrated, FramesIntegrated > 0 ? IntegrateMsTotal / FramesIntegrated : 0.0,
        FramesRepeatedDepth, FramesNotTracking, Stats.FusedSamples, Stats.ChunksTouched, Stats.ChunksDiscarded,
        Stats.ChunkCount, ChunkActors.Num(), ChunksMeshed, Tsdf->GetPendingRemeshCount());
    SecondsSinceLog = 0;
    FramesSeen = FramesIntegrated = FramesRepeatedDepth = FramesNotTracking = ChunksMeshed = 0;
    IntegrateMsTotal = 0;
}
