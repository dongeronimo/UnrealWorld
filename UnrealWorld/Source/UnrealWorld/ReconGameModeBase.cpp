#include "ReconGameModeBase.h"
#include "ReconstructionPersistence.h"
#include "Kismet/GameplayStatics.h"

AReconGameModeBase::AReconGameModeBase() {
    Persistence = CreateDefaultSubobject<UReconstructionPersistence>(TEXT("Persistence"));
}

void AReconGameModeBase::InitGame(const FString& MapName, const FString& Options, FString& ErrorMessage) {
    Super::InitGame(MapName, Options, ErrorMessage);
    if (Persistence && UGameplayStatics::HasOption(Options, TEXT("ReconWorld")))
        Persistence->WorldToLoad = UGameplayStatics::ParseOption(Options, TEXT("ReconWorld"));
}
