#pragma once

enum class EFact : uint8
{
    PlayerVisible,
    PlayerPosKnown,
    PlayerDead,
    InCover,
    InMeleeRange,
    WeaponLoaded,
    HasAmmo,
    IsHurt,
    Count // sempre o último
};


/* 
Facts são estados que o bot pode afirmar sobre si mesmo e sobre a inimiga. facts tem que sempre
ESTADOS. Decisões e processos ficam outros lugares.

O Planner consumirá os Facts pq ele precisa de algo pequeno pra buscar rápido. 
*/
struct Facts
{
    bool Values[(int)EFact::Count] = {};

    bool Get(EFact F) const
    {
        return Values[(int)F];
    }

    void Set(EFact F, bool V)
    {
        Values[(int)F] = V;
    }
};

struct Condition
{
    EFact Fact;
    bool Value;
};

struct Action
{
    FName Name;
    TArray<Condition> Pre;
    TArray<Condition> Effects;
    float Cost = 1.f;
};