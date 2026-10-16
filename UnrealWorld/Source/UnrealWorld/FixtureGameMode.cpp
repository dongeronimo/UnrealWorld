#include "FixtureGameMode.h"
#include "GameFramework/DefaultPawn.h"

AFixtureGameMode::AFixtureGameMode() {
    DefaultPawnClass = ADefaultPawn::StaticClass();
}
