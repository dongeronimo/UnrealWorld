#include "EnemyAIController.h"

AEnemyAIController::AEnemyAIController()
{
    PrimaryActorTick.bCanEverTick = true;
}

void AEnemyAIController::Tick(float Dt)
{
    Super::Tick(Dt);
}
