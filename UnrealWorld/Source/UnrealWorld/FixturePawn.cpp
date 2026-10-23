#include "FixturePawn.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/FloatingPawnMovement.h"

AFixturePawn::AFixturePawn(const FObjectInitializer& ObjectInitializer) : Super(ObjectInitializer) {
    // The component is what a sweep or trace finds; the actor flag is what
    // anything iterating components respects. Both off, so there's no path by
    // which this pawn is in the physics scene. UFloatingPawnMovement still
    // sweeps, finds nothing, and slides through.
    if (USphereComponent* Sphere = GetCollisionComponent()) {
        Sphere->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Sphere->SetGenerateOverlapEvents(false);
    }
    if (UStaticMeshComponent* Mesh = GetMeshComponent()) {
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Mesh->SetHiddenInGame(true);
    }
    SetActorEnableCollision(false);
    // ADefaultPawn's 1200 cm/s crosses a room in under a second.
    if (UFloatingPawnMovement* Movement = Cast<UFloatingPawnMovement>(GetMovementComponent()))
        Movement->MaxSpeed = 300.0f;
}
