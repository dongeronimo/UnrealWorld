#include "RatomanBruteController.h"
#include "..\RatomanBrute.h"

ARatomanBruteController::ARatomanBruteController()
{
    //TODO RATOMAN: SETUP DOS STATS
    GetStats().MaxHP = 100;
    GetStats().ViewDistance = 10;
    GetStats().ViewHalfAngleDeg = 45;
    GetStats().ForgetTime = 5;
    GetStats().IsRanged = false;
    GetStats().RangedDamage = 0;
    GetStats().MeleeDamage = 20;
    GetStats().MeleeRange = 1;
    GetStats().MagazineSize = 0;
}

void ARatomanBruteController::Tick(float Dt)
{
    Super::Tick(Dt);
}

void ARatomanBruteController::OnPossess(APawn* InPawn)
{
    Super::OnPossess(InPawn);
    RatomanBrute = GetPawn<ARatomanBrute>();
    Mem.HP = GetStats().MaxHP;
}

const TArray<Action>& ARatomanBruteController::GetActions() const
{
    static const TArray<Action> Actions = {
      { TEXT("Procurar"),
        {{ EFact::PlayerPosKnown, true }},
        {{ EFact::PlayerVisible,  true }} },

      { TEXT("Aproximar"),
        {{ EFact::PlayerVisible, true }},
        {{ EFact::InMeleeRange,  true }} },

      { TEXT("Golpear"),
        {{ EFact::InMeleeRange, true }},
        {{ EFact::PlayerDead,   true }} },
    };
    return Actions;
}
