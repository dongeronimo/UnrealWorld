#include "RatomanBruteController.h"
#include "..\RatomanBrute.h"

ARatomanBruteController::ARatomanBruteController()
{
}

void ARatomanBruteController::Tick(float Dt)
{
    Super::Tick(Dt);
}

void ARatomanBruteController::OnPossess(APawn* InPawn)
{
    Super::OnPossess(InPawn);
    RatomanBrute = GetPawn<ARatomanBrute>();
}
