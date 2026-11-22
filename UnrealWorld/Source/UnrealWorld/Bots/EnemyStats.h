#pragma once

// Configuração do tipo. Não muda em jogo (em teoria). Cada inimigo vai ter sua propria struct. Por ex,
// o Brute não tem ranged, mas tem melee forte. O creting (a ser feito) só tem ranged. Não sei onde essas
// structs vão ficar ainda, possivelmente nas classes dos inimigos (brute, cretin, etc..)
struct EnemyStats
{
    float MaxHP;

    // Visão
    float ViewDistance;
    float ViewHalfAngleDeg;
    float ForgetTime; // seg até esquecer

    // Ataque
    bool  IsRanged;
    float RangedDamage;
    float MeleeDamage;
    float MeleeRange;
    int   MagazineSize;
};