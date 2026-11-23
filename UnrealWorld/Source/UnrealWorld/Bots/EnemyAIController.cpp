#include "EnemyAIController.h"

AEnemyAIController::AEnemyAIController()
{
    PrimaryActorTick.bCanEverTick = true;
}

void AEnemyAIController::Tick(float Dt)
{
    Super::Tick(Dt);
}

const TArray<Action>& AEnemyAIController::GetActions() const
{
    static const TArray<Action> Actions{};
    return Actions;
}