#include "FixtureGameMode.h"
#include "FixturePawn.h"
#include "GameFramework/PlayerController.h"

AFixtureGameMode::AFixtureGameMode() {
    DefaultPawnClass = AFixturePawn::StaticClass();
    // A plain controller: the pawn brings its own fly bindings.
    PlayerControllerClass = APlayerController::StaticClass();
}
