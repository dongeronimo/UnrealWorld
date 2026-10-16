#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ReconChunkActor.generated.h"
class URealtimeMeshComponent;
class URealtimeMeshSimple;
class UMaterialInterface;

// One chunk of the reconstruction. Spawned and owned by AReconstructionActor,
// attached to it, with its relative location at the chunk origin.
//
// Vertices are chunk local. A room is metres across and float32 loses precision
// as it moves away from zero; keeping each chunk's vertices near its own origin
// keeps the detail marching cubes produced, and the actor transform (doubles)
// puts it back in place.
//
// RealtimeMeshComponent rather than ProceduralMeshComponent: marching cubes
// changes topology on every remesh, and PMC's only path for that is throwing the
// section away and recreating it. RMC updates the section group in place.
UCLASS(NotPlaceable)
class AReconChunkActor : public AActor {
    GENERATED_BODY()
public:
    AReconChunkActor();

    // Unreal space, centimetres, relative to this actor. Colors is one per
    // vertex or empty; empty draws black with alpha 0 (no colour evidence).
    void SetGeometry(const TArray<FVector3f>& Positions, const TArray<FVector3f>& Normals,
        const TArray<FColor>& Colors, const TArray<uint32>& Triangles, UMaterialInterface* Material);
    void ClearGeometry();

private:
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<URealtimeMeshComponent> MeshComponent;

    UPROPERTY()
    TObjectPtr<URealtimeMeshSimple> Mesh;

    bool bHasSectionGroup = false;
};
