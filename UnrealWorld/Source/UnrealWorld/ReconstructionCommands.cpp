// Recon.Save and Recon.List: the console side of UReconstructionPersistence.
//
// Console commands rather than Blueprint nodes or a button, because Unreal on
// Android registers a broadcast receiver for console commands, so they reach a
// running build over adb with no rebuild and nobody touching the screen:
//
//     adb shell "am broadcast -a android.intent.action.RUN -e cmd 'Recon.Save kitchen'"
//
// Tools/recon.py does exactly that, waits for the file and pulls it into this
// project's Saved/Recon. They work the same from the PIE console.
//
// The glue is here so neither side has to know the other: the actor hands out a
// snapshot, the game mode's persistence writes it, and this finds both.
#include "ReconstructionActor.h"
#include "ReconGameModeBase.h"
#include "ReconstructionPersistence.h"
#include "TsdfReconstruction.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "Misc/DateTime.h"

DEFINE_LOG_CATEGORY_STATIC(LogReconCommands, Log, All);

namespace {
    // The world being played. A command from an adb broadcast is run with
    // whatever world the engine has at hand, so fall back to looking for one.
    UWorld* FindGameWorld(UWorld* Given) {
        if (Given && Given->IsGameWorld())
            return Given;
        if (GEngine)
            for (const FWorldContext& Context : GEngine->GetWorldContexts())
                if (Context.World() && Context.World()->IsGameWorld())
                    return Context.World();
        return nullptr;
    }

    UReconstructionPersistence* FindPersistence(UWorld* World) {
        const AReconGameModeBase* GameMode = World ? World->GetAuthGameMode<AReconGameModeBase>() : nullptr;
        if (!GameMode || !GameMode->GetPersistence()) {
            UE_LOG(LogReconCommands, Error, TEXT("RECON the game mode isn't an AReconGameModeBase, so there is no persistence to use"));
            return nullptr;
        }
        return GameMode->GetPersistence();
    }
}

static FAutoConsoleCommandWithWorldAndArgs GReconSave(
    TEXT("Recon.Save"),
    TEXT("Recon.Save [name]: write the current reconstruction to Saved/Recon/<name>.tsdf (default: a timestamp)."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateStatic([](const TArray<FString>& Args, UWorld* InWorld) {
        UWorld* World = FindGameWorld(InWorld);
        UReconstructionPersistence* Persistence = FindPersistence(World);
        if (!Persistence)
            return;
        TActorIterator<AReconstructionActor> It(World);
        FTsdfSnapshot Snapshot;
        if (!It || !It->CaptureSnapshot(Snapshot)) {
            UE_LOG(LogReconCommands, Error, TEXT("RECON there's no running AReconstructionActor in %s"), *World->GetMapName());
            return;
        }
        const FString Name = Args.Num() > 0 ? Args[0] : FDateTime::Now().ToString(TEXT("%Y%m%d-%H%M%S"));
        FString Path;
        Persistence->Save(Snapshot, Name, Path);
    }));

static FAutoConsoleCommandWithWorldAndArgs GReconList(
    TEXT("Recon.List"),
    TEXT("Recon.List: the saved reconstructions this game mode's persistence can load."),
    FConsoleCommandWithWorldAndArgsDelegate::CreateStatic([](const TArray<FString>&, UWorld* InWorld) {
        UReconstructionPersistence* Persistence = FindPersistence(FindGameWorld(InWorld));
        if (!Persistence)
            return;
        TArray<FString> Names = Persistence->GetWorldNames();
        Names.Remove(FString());
        UE_LOG(LogReconCommands, Log, TEXT("RECON %d saved in %s%s%s"), Names.Num(), *Persistence->GetDirectory(),
            Names.Num() > 0 ? TEXT(": ") : TEXT(""), *FString::Join(Names, TEXT(", ")));
    }));
