#pragma once
#include "EnemyAIController.h"
#include "RatomanBruteController.generated.h"
class ARatomanBrute;
/// <summary>
/// Controller do ratoman brute TO BE DONE
/// </summary>
UCLASS()
class ARatomanBruteController : public AEnemyAIController
{
    GENERATED_BODY()
public:
    ARatomanBruteController();
    virtual void Tick(float Dt) override;

    UPROPERTY(BlueprintReadOnly)
    TObjectPtr<ARatomanBrute> RatomanBrute;
protected:
    virtual void OnPossess(APawn* InPawn) override;
    virtual const TArray<Action>& GetActions() const override;
};