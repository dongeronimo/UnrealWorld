#pragma once
#include "AIController.h"
#include "Memory.h"
#include "Facts.h"
#include "EnemyStats.h"
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
    EnemyStats& GetStats() { return Stats; }
protected:
    Memory Mem;
    Facts CurrentFacts;
    EnemyStats Stats;
    TArray<const Action*> Plan;
    int32 CurrentStep = 0;
    virtual const TArray<Action>& GetActions() const;
};