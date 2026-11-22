#pragma once
#include "AIController.h"
#include "EnemyAIController.generated.h"

/// <summary>
/// Controller dos inimigos TO BE DONE
/// </summary>
UCLASS()
class AEnemyAIController : public AAIController
{
    GENERATED_BODY()
public:
    AEnemyAIController();
    virtual void Tick(float Dt) override;

protected:

};