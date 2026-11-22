#pragma once

#include "CoreMinimal.h"

struct Facts;
struct EnemyStats;
/*
* Se Facts carrega afirmativas sobre o mundo (estados), Memory carrega os dados do mundo, do ponto
* de vista do bot: onde o player está, quanta munição eu tenho, etc...
*/
class Memory
{
public:
    //sobre o bot
    float HP = 100;
    int AmmoInMagazine = 0;
    //sobre a inimiga
    bool PlayerInSight = false;
    float PlayerLastSeenTime = -1;
    FVector PlayerLastKnownPos = FVector::ZeroVector;
    
    Facts GenerateFacts(const EnemyStats& Stats,
        const FVector& MyPos,
        float Now) const;
};