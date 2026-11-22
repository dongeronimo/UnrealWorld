#include "Memory.h"
#include "Facts.h"
#include "EnemyStats.h"

Facts Memory::GenerateFacts(const EnemyStats& Stats,
    const FVector& MyPos,
    float Now) const
{
    Facts F;

    // Sobre o player
    const bool bSeenEver = PlayerLastSeenTime >= 0.f;
    const float SinceSeen = Now - PlayerLastSeenTime;

    F.Set(EFact::PlayerVisible, PlayerInSight);
    F.Set(EFact::PlayerPosKnown, bSeenEver &&
        SinceSeen < Stats.ForgetTime);
    const float Dist =
        FVector::Dist(MyPos, PlayerLastKnownPos);
    F.Set(EFact::InMeleeRange, PlayerInSight &&
        Dist <= Stats.MeleeRange);

    // Sobre mim
    F.Set(EFact::WeaponLoaded, Stats.IsRanged &&
        AmmoInMagazine > 0);
    F.Set(EFact::HasAmmo, Stats.IsRanged);
    F.Set(EFact::IsHurt, HP < Stats.MaxHP * 0.5f);

    // Sem fonte de dados ainda:
    // InCover    -> quando houver cobertura
    // PlayerDead -> evento de morte do player
    return F;
}
