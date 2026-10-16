#include "ReconChunkActor.h"
#include "RealtimeMeshComponent.h"
#include "RealtimeMeshSimple.h"
#include "Interface/Core/RealtimeMeshBuilder.h"
#include "Materials/MaterialInterface.h"

namespace {
    const FRealtimeMeshSectionGroupKey& ChunkGroupKey() {
        static const FRealtimeMeshSectionGroupKey Key = FRealtimeMeshSectionGroupKey::Create(0, FName("Chunk"));
        return Key;
    }

    // Marching cubes gives normals but no tangents. Nothing samples a normal map
    // here, so any vector perpendicular to the normal will do.
    FVector3f PerpendicularTo(const FVector3f& Normal) {
        const FVector3f Axis = FMath::Abs(Normal.Z) < 0.9f ? FVector3f(0, 0, 1) : FVector3f(1, 0, 0);
        return FVector3f::CrossProduct(Normal, Axis).GetSafeNormal();
    }
}

AReconChunkActor::AReconChunkActor() {
    PrimaryActorTick.bCanEverTick = false;
    MeshComponent = CreateDefaultSubobject<URealtimeMeshComponent>(TEXT("ChunkMesh"));
    RootComponent = MeshComponent;
    MeshComponent->SetMobility(EComponentMobility::Movable);
    // Drawing only, for now. Collision (and navigation) comes later, per chunk.
    MeshComponent->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    // An empty level has no lights and the material is unshaded.
    MeshComponent->SetCastShadow(false);
}

void AReconChunkActor::SetGeometry(const TArray<FVector3f>& Positions, const TArray<FVector3f>& Normals,
    const TArray<FColor>& Colors, const TArray<uint32>& Triangles, UMaterialInterface* Material) {
    if (Positions.Num() == 0 || Triangles.Num() < 3) {
        ClearGeometry();
        return;
    }
    if (!Mesh) {
        Mesh = MeshComponent->InitializeRealtimeMesh<URealtimeMeshSimple>();
        if (!Mesh)
            return;
        Mesh->SetupMaterialSlot(0, "Chunk", Material);
    }

    RealtimeMesh::FRealtimeMeshStreamSet StreamSet;
    {
        RealtimeMesh::TRealtimeMeshBuilderLocal<uint32> Builder(StreamSet);
        Builder.EnableTangents();
        Builder.EnableColors();
        Builder.EnablePolyGroups();
        // Always a colour stream, so the section's layout never changes
        // between updates whether or not this mesh has colours.
        const bool bHasColors = Colors.Num() == Positions.Num();
        for (int32 V = 0; V < Positions.Num(); ++V)
            Builder.AddVertex(Positions[V])
                .SetNormalAndTangent(Normals[V], PerpendicularTo(Normals[V]))
                .SetColor(bHasColors ? Colors[V] : FColor(0, 0, 0, 0));
        for (int32 T = 0; T + 2 < Triangles.Num(); T += 3)
            Builder.AddTriangle(Triangles[T], Triangles[T + 1], Triangles[T + 2], /*PolyGroup=*/0);
    }

    if (bHasSectionGroup) {
        Mesh->UpdateSectionGroup(ChunkGroupKey(), MoveTemp(StreamSet));
    } else {
        Mesh->CreateSectionGroup(ChunkGroupKey(), MoveTemp(StreamSet));
        bHasSectionGroup = true;
    }
}

void AReconChunkActor::ClearGeometry() {
    if (Mesh && bHasSectionGroup) {
        Mesh->RemoveSectionGroup(ChunkGroupKey());
        bHasSectionGroup = false;
    }
}
