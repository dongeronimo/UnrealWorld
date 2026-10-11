#include "ARSessionStarter.h"

#include "ARBlueprintLibrary.h"
#include "ARSessionConfig.h"

DEFINE_LOG_CATEGORY_STATIC(LogARStart, Log, All);

void UARSessionStarter::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateUObject(this, &UARSessionStarter::Tick), 1.0f);
}

void UARSessionStarter::Deinitialize()
{
    FTSTicker::GetCoreTicker().RemoveTicker(TickerHandle);
    Super::Deinitialize();
}

bool UARSessionStarter::Tick(float DeltaSeconds)
{
    if (!bSessionRequested)
    {
        SessionConfig = NewObject<UARSessionConfig>();
        // SceneDepth makes the plugin turn on ARCore's depth mode. Without it
        // there is no depth to read later, raw or otherwise.
        SessionConfig->SetSessionTrackingFeatureToEnable(EARSessionTrackingFeature::SceneDepth);

        UARBlueprintLibrary::StartARSession(SessionConfig);
        bSessionRequested = true;
        return true;
    }

    const FARSessionStatus Status = UARBlueprintLibrary::GetARSessionStatus();
    UE_LOG(LogARStart, Log, TEXT("AR status=%d %s"),
        static_cast<int32>(Status.Status), *Status.AdditionalInfo);
    return true; // stay registered
}
