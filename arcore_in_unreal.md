
## The plan

Unreal's GoogleARCore plugin owns the ARCore session and we never create our own (unlike my previous experiments in vulkan+native android). UE's plugin does tracking, drives the camera and packages the app correctly. What it does not do is hand out raw depth, the confidence map, or a usable camera feed. So we reach underneath it, take the plugin's own ArSession* and ArFrame*, and call the ARCore C API on them directly. That gives us everything OpenChisel needs without forking the plugin or the engine.

I don't want to fork the engine or the plugin because my disk is small and I'm not confortable with Unreal source + compiled code taking 100s of gigabytes in my tiny SSDs.

## Step 1 -  Project Scaffold

Before anything I need an Unreal project that compiles for arm64, package, install and open on the phone. That's the first step where I go against the conventional wisdom. I won't use the Handheld AR template, except as a config donor, I'll use the empty c++ project. The reason is that the handheld ar template has too much clutter:
  - Passthrough: the plugin's camera material shows constant green on UE 5.7 and in my device. UPassthroughSubsystem will replace it.
  - Plane visualisers and touch-to-place: UReconSessionConfig will turn plane detection off since I'll use depth+TSDF to reconstruct space and my anchor is placed at the camera position rather than on a tapped plane.
  - Pawn and session config: ARPawn and UReconSessionConfig replace them because I need SceneDepth on and autofocus off. The template's defaults don't do that and autofocus ruin the TSDF.
  - Map: the reconstruction needs an empty level. Any geometry in the map gets drawn over the camera feed.
  - It doesn't even run. The template is missing HIGH_SAMPLING_RATE_SENSORS so it hits AR_ERROR_FATAL. Starting from it wouldn't have given me a working baseline.

I won't even consider other templates like Top Down and Third Person: at best they can be BP and class donors for character controllers, but that's for the distant future. So: Blank, C++, Target Platform Mobile, Quality Preset Scalable. C++ because i'm going to call the ARCore NDK and need a module for it anyway.

So two projects: my actual project (UnrealWorld) and a disposable Handheld AR Project that is just a config donor. 
![Image description](./images/handheld_ar_project_template.png)
![Image description](./images/blank_template.png)

It's important that the actual project is c++ and not blueprint project because we'll need a lot of c++ since all the TSDF code and arcore code is raw c++.

Now that I have the two projects I diff D:\UnrealWorld\UnrealWorld\Config\DefaultEngine.ini and D:\UnrealWorld\Handheld\Config\DefaultEngine.ini .Some changes don't matter, like EditorStartupMap, GameDefaultMap. Others do, like the block AndroidRuntimeSettings.

We also need to open UnrealWorld's DefaultGame.ini to add  
```
bStartInAR=True
bSupportAR=True
```
to ```/Script/EngineSettings.GeneralProjectSettings```. And finally we add ```"TargetPlatforms": [ "Android" ],``` to our .uproject. Then we generate the new visual studio project and compile it.

I also need to clean up a lot of things that the Mobile/Scalable template brought in: raytrace, nanite, virtual shadow maps, etc... I don't want to use them and I don't even know whether they run in android... So off with them:
```
r.DynamicGlobalIlluminationMethod=0
r.ReflectionMethod=0
r.Lumen.HardwareRayTracing=False
r.Shadow.Virtual.Enable=0
r.RayTracing=False
r.RayTracing.RayTracingProxies.ProjectEnabled=False
r.PathTracing=False
r.GenerateMeshDistanceFields=False
r.Nanite.ProjectEnabled=False
r.Substrate=False
r.HeterogeneousVolumes=False
```

And then I set android project properties, similar to that Player Settings screen in Unity:
```
[/Script/AndroidRuntimeSettings.AndroidRuntimeSettings]
PackageName=dev.dongeronimo.unrealworld
ApplicationDisplayName=Unreal World
Orientation=Portrait
bBuildForES31=False
bSupportsVulkan=True
MinSDKVersion=26
TargetSDKVersion=34
```
I decided that I don't want to deal with orientation changes between Portrait and Landscape, that I want Vulkan support and also the MinSDKVersion for a recent sdk that is guaranteed to have all that I need (iirc it's also guaranteed that it has vulkan 1.2).

```bBuildForES31=False``` drops the OpenGL ES path, which halves the cooked shaders from UE 5.6 the ARCore session reportedly doesn't come up under OpenGL at all (AR_ERROR_MISSING_GL_CONTEXT).

### System Prerequisites

- Unreal's Android support files, inside the engine install.
- Android Studio, which brings the Android SDK and its sdkmanager.
- The right NDK version, plus two environment variables pointing at it.
- A JDK, version 17 or newer.

These are system-wide requirements, set them up once for a project and we don't set them again.

#### 1. Unreal's Android support files
![Image description](./images/ue_engine_android.png)

We must make sure that we installed android support files.

#### 2. Android Studio

If we don't have it we must install. I'm using Narwal Feature Drop. Is it the best or the most correct version? I don't know, maybe I should use a LTS version. But that's what I have installed and that's what I will use.

#### 3. The right NDK

The engine ships a script that installs the exact Android packages it wants:
```
D:\UE5.7\UE_5.7\Engine\Extras\Android\SetupAndroid.bat
```


Close Android Studio and run that script. It uses `sdkmanager` to install
platform `android-34`, build-tools `35.0.1`, CMake `3.22.1` and NDK
`27.2.12479018` (that's r27c). It then sets two **user** environment variables,
`NDKROOT` and `NDK_ROOT`, to that NDK's folder. You can read the same list in
`Engine\Config\Android\Android_SDK.json`.

Once the script finishes, **close and reopen the Epic Games Launcher**, and
anything else you start Unreal from. A program only reads environment variables
when it starts, and the editor inherits them from whatever launched it. Chapter
11 explains why this one bit us.

The script is the easy route. The trap is an NDK you already had. Unreal 5.7
accepts NDK **r27c through r28c** only.

Wrong NDK gives and error like 

> Platform Android is not a valid platform to build. Check that the SDK is
> installed properly and that you have the necessary platform support files
> (DataDrivenPlatformInfo.ini, SDK.json, etc).

Both of those files are fine. The real sentence is in the UBT log under
`%APPDATA%\Unreal Engine\AutomationTool\Logs\`:

```
Unable to find valid SDK(s) for Android:
  Found Sdk Version=r27, MinRequired=r27c, MaxRequired=r28c.
```

Don't trust `AndroidToolChain.cs`. The version comparisons in there are feature
gates, much looser than the range actually enforced.

To verify the actual NDK in NDKROOT use
```powershell
[Environment]::GetEnvironmentVariable('NDKROOT','User')
```

### Testing the build:

```powershell
$env:NDKROOT = "C:\Users\lucia\AppData\Local\Android\Sdk\ndk\28.2.13676358"
$env:NDK_ROOT = $env:NDKROOT
& "D:\UE5.7\UE_5.7\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun `
  -project="D:\UnrealWorld\UnrealWorld\UnrealWorld.uproject" -noP4 -platform=Android `
  -cookflavor=ASTC -clientconfig=Development -build -cook -stage -package `
  -archive -archivedirectory="D:\UnrealWorld\Archive" -utf8output
```

First build will take a long time from cooking things.


### Enablin the plugin

I add the plugin to the `.uproject`, Android only, and change nothing else:

```json
	"Plugins": [
		{
			"Name": "ModelingToolsEditorMode",
			"Enabled": true,
			"TargetAllowList": [
				"Editor"
			]
		}, 
		{
			"Name": "GoogleARCore",
			"Enabled": true,
			"SupportedTargetPlatforms": [
				"Android"
			]
		}
	]
```

That single block does a surprising amount of packaging work: The
generated manifest (D:\UnrealWorld\UnrealWorld\Intermediate\Android\arm64\AndroidManifest.xml) gains:

```xml
<meta-data android:name="com.google.ar.core" android:value="required" />
<meta-data android:name="com.google.ar.core.min_apk_version" android:value="250210000" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-feature android:name="android.hardware.camera.ar" android:required="true" />
<activity android:name="com.google.ar.core.InstallActivity" ... />
<queries><package android:name="com.google.ar.core" /></queries>
```

plus `libarcore_sdk_c.so` in the APK and `com.google.ar:core:1.48.0` in the
Gradle dependencies. `value="required"` makes this an *AR Required* app, so the
Play Store will only show it to ARCore devices. At the moment I don't know how to change AR to be optional, only to make it mandatory.

A reminder: as it is, nothing starts by itself. Even though camera permissions are declared they aren't asked for yet, so camera permission is just declared, not granted yet. If we just try to get the camera we'll be blocked by the permission system. 

### Sampling Rate fix

At least in my device (a Smsung Galaxy S25) I am forced to set sampling rate to high: ```android.permission.HIGH_SAMPLING_RATE_SENSORS```. If I don't do that I'll have a AR_ERROR_FATAL whose cause is
```
E native : ARCoreError: third_party/arcore/ar/infrastructure/android_data_source.cc:1073
E native : Failed to register sensor to queue 0
```

Reason: ARCore reads the inertial sensors at well over 200 Hz. Since Android 12, an app
targeting API 31 or higher has to declare `HIGH_SAMPLING_RATE_SENSORS` to sample
anything that fast. The plugin's APL file injects the camera permission, the AR
feature, the meta-data and the install activity. It doesn't inject this one.

In Config/DefaultEngine.ini do something like this:
```
[/Script/AndroidRuntimeSettings.AndroidRuntimeSettings]
PackageName=dev.dongeronimo.unrealworld
ApplicationDisplayName=Unreal World
Orientation=Portrait
bBuildForES31=False
bSupportsVulkan=True
MinSDKVersion=26
TargetSDKVersion=34
+ExtraPermissions=android.permission.HIGH_SAMPLING_RATE_SENSORS <----- THIS IS THE GOTCHA!
```
This is one of the many reasons why I have to configure everything from the ground up instead of using the existing template: **Epic's own Handheld AR template don't deal with that permission also.** Every
ARCore project on this engine starts broken, and has since Android 12. That
explains a whole genre of forum thread, dozens of pages long, about sessions that
won't start and black passthrough, where people reinstall SDKs and switch RHIs.
Nowhere between `AR_ERROR_FATAL` and `Failed to register sensor to queue 0` does
the word "permission" appear.

#### A Note on project settings:
- ```Project->Packaging->Use Pak File``` and ```Use Io Store``` = false. It'll save us some grief later, making deployment faster.

--- 
When we run the code for the 1st time it asks for permission:
![Image description](./images/Screenshot_20261010_210146.png)

Once we accept it we get:
```
2026-10-10 21:04:42.270 28083-28723 UE                      dev.dongeronimo.unrealworld          D  [2026.10.11-00.04.42:270][ 95]LogARStart: AR status=1 ARCore Session is running.
2026-10-10 21:04:43.300 28083-28723 UE                      dev.dongeronimo.unrealworld          D  [2026.10.11-00.04.43:300][126]LogARStart: AR status=1 ARCore Session is running.
2026-10-10 21:04:44.329 28083-28723 UE                      dev.dongeronimo.unrealworld          D  [2026.10.11-00.04.44:329][157]LogARStart: AR status=1 ARCore Session is running.
```

Showing that our AR session is running

It even has an "End of Evangelion" effect with the interaction of the default terrain with the AR Camera:
![Image description](./images/Screenshot_20261010_210620.png)

See that while we got our camera feed for the 1st time it's broken, since the colour is wrong.

If we hadn't fixed the sampling rate configuration we'd get 

> Fatal error occurred when starting ARCore Session. Stopping and restarting
> ARCore Session may fix the issue.

And would get in the rabbit hole of not being able to pinpoint the error with the information given by the error messages.

#### Appendix: how do i found the Sampling Rate issue
- I have a native (as in Java + Cpp + Vulkan) arcore app that do space reconstruction, basically an early prototype of what I'm doing in Unreal.
- It creates it's own arcore session and works fine, while the Unreal version in the same device fails.
- By grepping the manifest it became clear what was missing. 
- Without the previous work in the hand-made AR renderer i'd never find the difference and the project in Unreal would die. That's why AR in Unreal Engine is the Gom Jabbar.

## Step 2 - Getting ARCore to actually run

I don't have to write permission code for AR things: ```UARBlueprintLibrary::StartARSession``` does that. It:

1) Verifies if ARCore is installed
2) Asks for camera permission, checking android.permission.CAMERA. If it hasn't been granted, the plugin shows the system dialog itself. If the user says no, the status becomes PermissionNotGranted and the plugin stops trying.
3) The AR Session. Once both of those pass, the plugin creates the ArSession, applies your config and calls ArSession_resume.
4) The loop. From then on, every game frame, the plugin calls ArSession_update and keeps the newest ArFrame.

The capture loop is also managed by the plugin. Each frame will have the current data and I have but to reach for it.

Next step: add AugmentedReality dependence to UnrealWorld.Build.cs:

```csharp
PrivateDependencyModuleNames.AddRange(new string[] { "AugmentedReality" });
```

Then a UGameInstanceSubsystem, because subsystems are automatically initialized by the engine, one per GameInstance, can hold UObjects (we'll need to hold textujres), Initialize/Denitialize match the app's lifecycle and survive beyond levels. They are also easy to get in code and easy to get in BPs. Finally they run in all machines and ShouldCreateSubsystem helps us avoid errors due attempts to create the subsystem where it isn't supported (ex, the Editor, Headless Servers).

### AR Session Starter

This is the code for a Subsystem that initializes ARCore:
```cpp
#pragma once
#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "ARSessionStarter.generated.h"
class UARSessionConfig;
UCLASS()
class UARSessionStarter : public UGameInstanceSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
private:
	bool Tick(float DeltaSeconds);
	// UPROPERTY so the garbage collector doesn't delete the config while the
	// session is still using it. Nothing else holds a reference to it.
	UPROPERTY()
	TObjectPtr<UARSessionConfig> SessionConfig;
	FTSTicker::FDelegateHandle TickerHandle;
	bool bSessionRequested = false;
};
```

```cpp
#include "ARSessionStarter.h"
#include "ARBlueprintLibrary.h"
#include "ARSessionConfig.h"
DEFINE_LOG_CATEGORY_STATIC(LogARStart, Log, All);
void UARSessionStarter::Initialize(FSubsystemCollectionBase& Collection) {
    Super::Initialize(Collection);
    TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateUObject(this, &UARSessionStarter::Tick), 1.0f);
}
void UARSessionStarter::Deinitialize() {
    FTSTicker::GetCoreTicker().RemoveTicker(TickerHandle);
    Super::Deinitialize();
}
bool UARSessionStarter::Tick(float DeltaSeconds) {
    if (!bSessionRequested) {
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
```
- Why Subsystem: it starts with the client and dies with the client, runs in all clients and servers (we'll have to deal with that later, server don't have AR)
- Why the ticker: to give us a place to initialize the session. Mind that session initialization is asynchronous: StartARSession records the request but it takes some time to actually finish it:
```
  tick 1:  StartARSession(config)  → plugin sets bStartSessionRequested = true, returns
  frame N:      plugin checks ARCore is installed
  frame N+k:    plugin shows the camera dialog, waits for the user
  frame N+m:    plugin creates and resumes the ArSession  → status becomes Running
  every frame after: plugin calls ArSession_update
```
--- 

### The green image

It can't be fixed. The plugin's own camera overlay goes green because of how the plugin hands the camera texture to Unreal's Vulkan renderer. That code is inside the engine, and I'd need an engine built from source to even debug it. So getting the RGB feed right means switching the plugin's overlay off and drawing the feed myself from ARCore's CPU image even if that means a texture copy because the alternative is this ugly green tinted image. That's why this is the Gom Jabber of ARCore in unreal engine.

### The back door: the plugin's own session and frame

The plugin acquires depth, but only `ArFrame_acquireDepthImage16Bits`, which is
the *smoothed* stream. It exposes no raw depth and no confidence map in its public API and I need them do use OpenChisel. I also need this backdoor to fix the green camera issue.


`FGoogleARCoreDevice` lives in the plugin's `Private` folder and has no
`GOOGLEARCOREBASE_API` export macro. In `GoogleARCoreDevice.cpp`, around lines
653 and 661:

```cpp
void* FGoogleARCoreDevice::GetARSessionRawPointer()
{
#if PLATFORM_ANDROID
	return reinterpret_cast<void*>(ARCoreSession->GetHandle());
#endif
	return nullptr;
}

void* FGoogleARCoreDevice::GetGameThreadARFrameRawPointer()
{
#if PLATFORM_ANDROID
	return reinterpret_cast<void*>(ARCoreSession->GetLatestFrameRawPointer());
#endif
	return nullptr;
}
```

Those return the real `ArSession*` and the current `ArFrame*`. For some reason these functions weren't documented. Maybe they are considered internal and can change at any time? I don't know. But I do know that at Unreal Engine 5.7, they are there even though they aren't documented. With those two pointers, everything else is the plain ARCore C API and we could do 
```cpp
auto* Device  = FGoogleARCoreDevice::GetInstance();
auto* Session = reinterpret_cast<ArSession*>(Device->GetARSessionRawPointer());
auto* Frame   = reinterpret_cast<ArFrame*>(Device->GetGameThreadARFrameRawPointer());
```
and get what we need.

### Reaching them from our module

In `Source/UnrealWorld/UnrealWorld.Build.cs`:

```csharp
if (Target.Platform == UnrealTargetPlatform.Android)
{
    PrivateDependencyModuleNames.AddRange(new string[] {
        "GoogleARCoreBase",
        "GoogleARCoreSDK",       // supplies arcore_c_api.h
        "GoogleARCoreRendering", // GoogleARCoreDevice.h includes a header from it
    });

    PrivateIncludePaths.Add(Path.Combine(EngineDirectory,
        "Plugins", "Runtime", "AR", "Google", "GoogleARCore",
        "Source", "GoogleARCoreBase", "Private"));
}
```

and in the `.cpp` files that use it:

```cpp
#if PLATFORM_ANDROID
#include "GoogleARCoreDevice.h"
#include "arcore_c_api.h"
#endif
```

This actually works because the android target is monolithic, all modules end up in one big .so and the _API macros expands to nothing and the symbols that were never exported are still resolved within that one big ass binary.

In the editor this call will fail to link. That won't blow as linker error because both accessors are already wrapped with  `#if PLATFORM_ANDROID` and return nullptr if not android.

The real problem, as I mentioned above, is that is engine-private with no deprecation contract. It's there in Unreal 5.7, there's no guarantee whatsoever that it'll be there and behave the same way in other versions.

The real solution would be to bite the bullet and build the engine from source fixing these problems but, as I said, I lack disk space for that.

--- 
#### Possible Alternative: have yet to be tried

While writing this up I checked the engine for a less fragile way in, and there
seems to be one. `FARSupportInterface`, in the engine's `AugmentedReality` module,
has *exported* methods with the same names:

```cpp
// Engine/Source/Runtime/AugmentedReality/Public/ARSupportInterface.h:119
UE_API void* GetARSessionRawPointer();
UE_API void* GetGameThreadARFrameRawPointer();
```

They forward to `IARSystemSupport`, which the GoogleARCore tracking system
implements by calling the same two private accessors. You'd reach it through
`GEngine->XRSystem->GetARCompositionComponent()`. **This has never been built
or run in this project.** If it behaves the way the source suggests, it would
replace the private include path and work in the editor as well. It's worth an
afternoon the next time an engine upgrade breaks the private route.

---

I have, at the moment a series of problems: My pawn don't care about the camera, we have a world full of useless things.

#### The world:

I deleted the default world: it had too many things that i don't need. Then i created the AR_Blank world, empty and set it as `GameDefaultMap`. Then I added to DefaultGame.ini:
```ini
[/Script/UnrealEd.ProjectPackagingSettings]
UsePakFile=False
bUseIoStore=False
+MapsToCook=(FilePath="/Game/Levels/AR_Blank")
```
Mind the + and mind the path to the file. `MapsToCook` isn't redundant. The cook follows references, and a map whose contents all arrive at runtime references nothing so it risks being dropped and causing all kinds of baffling bugs.

An Empty Level has no `PlayerStart`, so the pawn spawns at the origin. For AR that is correct: the origin is where the session started.

#### The pawn and the camera

`AGameModeBase` spawns `ADefaultPawn`, which has no `UCameraComponent`.  Without one, the player
camera manager uses the pawn's location plus eye height, and XR tracking is never applied anywhere along that path. So I need to create an AR Pawn and an AR Game Mode:

The pawn:
```cpp
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "ARPawn.generated.h"
class UCameraComponent;
class USceneComponent;

// The player's pawn. It is clear that the pawn that
// the player possess is the one that represents his
// position in the AR world.
UCLASS()
class AARPawn : public APawn {
    GENERATED_BODY()
public:
    AARPawn();
private:
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, meta = (AllowPrivateAccess = "true"))
    TObjectPtr<UCameraComponent> Camera;
    /// <summary>
    /// The AR Tracking origin. The pawn's transform says where the
    /// phone's tracking space sits in the Unreal world.
    /// </summary>
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<USceneComponent> Root;

};
```

```cpp
#include "ARPawn.h"
#include "Camera/CameraComponent.h"

AARPawn::AARPawn(){
    PrimaryActorTick.bCanEverTick = false;
    // A plain scene comp with no visuals, it's just a transform.
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    RootComponent = Root;
    // The AR-Driven camera, attached to Root - phone pose is now
    // an offset from origin instead of overwritting the pawn's own
    // transform.
    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("AR Camera"));
    Camera->SetupAttachment(Root);
    //The reason this class exists, this is what makes the
    //camera be where the phone is
    Camera->bLockToHmd = true;
    //The AR session sets the view from the real sensor. 
    //The controller must not overwrite the sensor.
    Camera->bUsePawnControlRotation = false;
}
```
The game mode:
```cpp
#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "ARGameMode.generated.h"
/// <summary>
/// For now it's just an "empty" Game Mode to allow me to 
/// set the specific Pawn that i want to use (A pawn derived
/// from AARPawn).
/// </summary>
UCLASS()
class AARGameMode : public AGameModeBase {
	GENERATED_BODY()

public:
	AARGameMode();
};
```
```cpp
// ARGameMode.cpp
#include "ARGameMode.h"
#include "ARPawn.h"
AARGameMode::AARGameMode(){
//Do nothing for now.
}
```
Finally we must add a player start actor at (0,0,0).

Next step is to create a blueprint from ARPawn (BP_ARPawn) and add some logging capabilities to the blueprint:
![Image description](./images/bp_arpawn_print_camera_position_and_rotation.png)

And them a blueprint from ARGameMode (BP_ARGameMode) and set BP_ARPawn as it's default pawn. Finally we either set BP_ARGameMode as the default game mode or set it as the game mode override of AR_Blank level, doesn't matter which way, the result is to get the game mode to use our AR-Capable pawn.

With all that, if we run in the device and move/rotate it around the world we'll see the output in logcat every second:
```
2026-10-11 16:34:42.462 20301-20725 UE                      dev.dongeronimo.unrealworld          D  [2026.10.11-19.34.42:462][947]LogBlueprintUserMessages: [BP_ARPawn_C_2147482419] [CamCheck] t=32.006 loc=X=-6.389 Y=-0.192 Z=3.924 rot=P=-17.765 Y=33.32 R=-0.331
2026-10-11 16:34:43.487 20301-20725 UE                      dev.dongeronimo.unrealworld          D  [2026.10.11-19.34.43:487][978]LogBlueprintUserMessages: [BP_ARPawn_C_2147482419] [CamCheck] t=33.03 loc=X=-0.897 Y=-8.617 Z=3.165 rot=P=-10.082 Y=-24.457 R=3.57
2026-10-11 16:34:44.463 20301-20725 UE                      dev.dongeronimo.unrealworld          D  [2026.10.11-19.34.44:463][  7]LogBlueprintUserMessages: [BP_ARPawn_C_2147482419] [CamCheck] t=34.002 loc=X=-6.578 Y=-13.491 Z=6.667 rot=P=0.264 Y=-63.518 R=-6.128
```
proving that our pawn is walking around the world.

### Session Config

Now that we proved that arcore is working and that our camera is following the phone's position and orientation (position from where and orientation from what? That's for later when we anchor the space) we can change the session config so that arcore gives us what we need: the raw depth plus the confidence map.

- Reconstruction Session Config

The header:
```cpp
#pragma once
#include "CoreMinimal.h"
#include "ARSessionConfig.h"
#include "ReconstructionSessionConfig.generated.h"
/// <summary>
/// Holds the configs for our needs: raw depth and confidence map
/// </summary>
UCLASS()
class UReconstructionSessionConfig : public UARSessionConfig {
    GENERATED_BODY()
public:
    UReconstructionSessionConfig();
};
```
The cpp
```cpp
#include "ReconstructionSessionConfig.h"

UReconstructionSessionConfig::UReconstructionSessionConfig() {
    EnabledSessionTrackingFeature = EARSessionTrackingFeature::SceneDepth;
    bEnableAutoFocus = false;
    bHorizontalPlaneDetection = false;
    bVerticalPlaneDetection = false;
    LightEstimationMode = EARLightEstimationMode::AmbientLightEstimate;
    bEnableAutomaticCameraOverlay = false;
}
```

It derives from `UARSessionConfig` and we set the configutation that we need: depth, no autofocus, no plane detection (for now, maybe we'll activate it in the future), lighting from the real world as ambient light in the scene and the removal of the automatic overlay (that ugly green image with the camera feed).

Then in ARSessionStarter we change `::Tick` to:
```cpp
bool UARSessionStarter::Tick(float DeltaSeconds) {
    if (!bSessionRequested) {
        // we use the session config we defined instead of the one that we created ad-hoc here.
        SessionConfig = NewObject<UReconstructionSessionConfig>();

        UARBlueprintLibrary::StartARSession(SessionConfig);
        bSessionRequested = true;
        return true;
    }

    const FARSessionStatus Status = UARBlueprintLibrary::GetARSessionStatus();
    UE_LOG(LogARStart, Log, TEXT("AR status=%d %s"),
        static_cast<int32>(Status.Status), *Status.AdditionalInfo);
    return true; // stay registered
}
```

The result is that we no longer see the default ugly image and we now can build our own image and the hooks for the depth and confidence texture. 

## Step 3 - Providing the data

We have a session, the camara is following the phone's gyro and accelerometers (they give us the rotation and position), so now it's the time to get the correct feed, working around UE's broken AR camera feed in UE 5.7 and the buffers that OpenChisel depends on to do it's thing.

#### Ticking every frame
In `UARSessionStarter::Initialize` we set up a ticker:
```
    TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateUObject(this, &UARSessionStarter::Tick), 1.0f);
```
And then that ticker tries to start ARCore (see `UARSessionStarter::Tick`).
This ticker ticks every 1 second. We need to tick every frame. So we change the time parameter from 1.0 to 0:
```
    TickerHandle = FTSTicker::GetCoreTicker().AddTicker(
        FTickerDelegate::CreateUObject(this, &UARSessionStarter::Tick), 0.0f);
```
now it ticks every frame. Remember that this does not affect the log, it's ticking is controlled by a timer in the blueprint.

  ```text
  GEngine->Tick
   └─ UGameEngine::Tick
       ├─ UWorld::Tick                                  GameEngine.cpp:1880
       │   ├─ XRSystem->OnStartGameFrame                LevelTick.cpp:1514   ← new ArFrame
       │   ├─ FWorldDelegates::OnWorldPreActorTick      LevelTick.cpp:1646
       │   ├─ actors / Blueprints (tick groups)         LevelTick.cpp:1721…
       │   ├─ FTickableGameObject::TickObjects          LevelTick.cpp:1792
       │   └─ FWorldDelegates::OnWorldPostActorTick     LevelTick.cpp:1877
       └─ RedrawViewports                               GameEngine.cpp:2006  ← this frame is sent to the renderer
  FTSTicker::GetCoreTicker().Tick                       LaunchEngineLoop.cpp:6072  ← where my Tick is
  ```
  - My tick sees the current frame. ARCore updated it earlier in the same engine frame.
  - But actors and Blueprints have already ticked. If a Blueprint pulls data from the starter in its own Tick, it gets last frame's data. That's unacceptable for camera feed, but tolerable for the reconstruction.

  To solve that problem I use `FWorldDelegates::OnWorldPreActorTick`. I add to the .h:
  ```cpp
  private:
    ...
	void OnPreActorTick(UWorld* World, 
		ELevelTick TickType, float DeltaSeconds);
	...
    FDelegateHandle PreActorTickHandle;
  ```
  and to the cpp
```cpp
void UARSessionStarter::Initialize(FSubsystemCollectionBase& Collection)
{
    ...
    PreActorTickHandle = FWorldDelegates::OnWorldPreActorTick.AddUObject(
        this, &UARSessionStarter::OnPreActorTick);
}

void UARSessionStarter::Deinitialize()
{
    ...
    FWorldDelegates::OnWorldPreActorTick.Remove(PreActorTickHandle);
    Super::Deinitialize();
}
void UARSessionStarter::OnPreActorTick(UWorld* World, ELevelTick TickType, float DeltaSeconds)
{
    if (World->GetGameInstance() != GetGameInstance()) return;
    //TODO: get the camera feed
}
```
To do so i'll do massive changes to ARSessionStarter: define the structs that hold AR data, callbacks for them, capture the data, broadcast it... instead of going step-by-step i'd rather put the whole code here and explain its parts later.

- The new version of the header:
```cpp
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "Containers/Ticker.h"
#include "ARFrameData.h"
#include "ARFramePose.h"
#include "ARSessionStarter.generated.h"
class UARSessionConfig;
DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnNewARFrame);

DECLARE_MULTICAST_DELEGATE_OneParam(FOnARFrame, const FARFrameData&);

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnARFramePose, const FARFramePose&, Pose);

UCLASS()
class UARSessionStarter : public UGameInstanceSubsystem {
	GENERATED_BODY()
public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
	// C++ consumers. Fires once per camera frame, after arcore update and before
	// any actor ticks or the frame's rendered,
	FOnARFrame OnARFrame;
	// Fires at the same stage that OnARFrame fires, but only carries pose information
	UPROPERTY(BlueprintAssignable)
	FOnARFramePose OnARFramePose;
private:
	void OnPreActorTick(UWorld* World, ELevelTick TickType, float DeltaSeconds);
	void ReadAndBroadcastFrame(UWorld* World);
	// UPROPERTY so the garbage collector doesn't delete the config while the
	// session is still using it. Nothing else holds a reference to it.
	UPROPERTY()
	TObjectPtr<UARSessionConfig> SessionConfig;

	FDelegateHandle PreActorTickHandle;
	bool bSessionRequested = false;
	int64 LastFrameTimestampNs = 0;
};

```
- the new (huge) cpp:
```cpp
#include "ARSessionStarter.h"
#include "ReconstructionSessionConfig.h"
#include "ARBlueprintLibrary.h"
#include "Engine/World.h"
#include "GameFramework/WorldSettings.h"

#if PLATFORM_ANDROID
#include "GoogleARCoreDevice.h"
#include "arcore_c_api.h"
#endif

// The depth map is the colour image centre-cropped to the depth
// aspect, then scale. The principal point moves before it scales.
// BTW: This is for modern samsumg phones that use math+ai to generate
// depth from RGB images + pose, I suspect that if the device had
// an actual depth sensor that would be quite different
void DeriveDepthIntrinsics(FARFrameData& D) {

    const float SrcW = D.IntrinsicsWidth;
    const float SrcH = D.IntrinsicsHeight;
    if (D.DepthHeight == 0)
        return;
    const float DepthAspect = float(D.DepthWidth) / float(D.DepthHeight);

    float CropW = SrcW, CropH = SrcH;
    if (DepthAspect > SrcW / SrcH) CropH = SrcW / DepthAspect; // depth wider: lose rows
    else                           CropW = SrcH * DepthAspect; // depth taller: lose columns
    const float CropLeft = (SrcW - CropW) * 0.5f;
    const float CropTop = (SrcH - CropH) * 0.5f;
    const float ScaleX = D.DepthWidth / CropW;
    const float ScaleY = D.DepthHeight / CropH; // must equal ScaleX

    D.DepthFx = D.ImageFx * ScaleX;
    D.DepthFy = D.ImageFy * ScaleY;
    D.DepthCx = (D.ImageCx - CropLeft) * ScaleX;
    D.DepthCy = (D.ImageCy - CropTop) * ScaleY;
}

// ARCore (right-handed, metres, +Y up, -Z forward) to Unreal (left-handed,
// centimetres, +X forward, +Z up). The same basis change the plugin uses.
FARFramePose MakeBlueprintPose(const FARFrameData& D, float WorldToMeters) {
    FARFramePose P;
    P.TimestampNs = D.TimestampNs;
    P.bTracking = D.bTracking;
    P.bHasDepth = D.DepthMm != nullptr;
    P.bHasImage = D.Y != nullptr;
    const float* R = D.SensorPose;
    P.Location = FVector(-R[6], R[4], R[5]) * WorldToMeters;
    P.Rotation = FQuat(R[2], -R[0], -R[1], R[3]).Rotator();
    return P;
}

void UARSessionStarter::Initialize(FSubsystemCollectionBase& Collection) {
    Super::Initialize(Collection);
    // this tick is before the actors
    PreActorTickHandle = FWorldDelegates::OnWorldPreActorTick.AddUObject(
        this, &UARSessionStarter::OnPreActorTick);
}

void UARSessionStarter::Deinitialize() {
    FWorldDelegates::OnWorldPreActorTick.Remove(PreActorTickHandle);
    Super::Deinitialize();
}

void UARSessionStarter::OnPreActorTick(UWorld* World, ELevelTick TickType, float DeltaSeconds) {
    if (World->GetGameInstance() != GetGameInstance()) 
        return;
    if (!bSessionRequested) {
        SessionConfig = NewObject<UReconstructionSessionConfig>(this);
        UARBlueprintLibrary::StartARSession(SessionConfig);
        bSessionRequested = true;
        return;
    }
    // Starting is asynchronous (install check, permission dialog, resume).
    // Before Running, the raw pointers are null anyway.
    if (UARBlueprintLibrary::GetARSessionStatus().Status != EARSessionStatus::Running) {
        return;
    }
    ReadAndBroadcastFrame(World);
}
#if PLATFORM_ANDROID
static bool GetFrameAndSession(ArSession** Session, ArFrame** Frame) {
    // Get the session and frame, if we fail to get it, exit.
    *Session = nullptr;
    *Frame = nullptr;
    FGoogleARCoreDevice* Device = FGoogleARCoreDevice::GetInstance();
    if (!Device) {
        return false;
    }
    *Session = static_cast<ArSession*>(Device->GetARSessionRawPointer());
    *Frame = static_cast<ArFrame*>(Device->GetGameThreadARFrameRawPointer());
    return *Session && *Frame;
}

static bool GetTimestamp(const ArSession* Session, const ArFrame* Frame, 
    const int64_t LastFrameTs, int64_t& TimestampNs) {
    TimestampNs = 0;
    ArFrame_getTimestamp(Session, Frame, &TimestampNs);
    // if the timestapm is the same as the last frame timestamp it's the same frame and there's no 
    if (TimestampNs == LastFrameTs)
    {
        return false;
    }
    return true;
}


#endif
void UARSessionStarter::ReadAndBroadcastFrame(UWorld* World) {
#if PLATFORM_ANDROID //We only do something if we are in android.
    // Get the session and frame, if we fail to get it, exit.
    ArSession* Session = nullptr;
    ArFrame* Frame = nullptr;
    if (!GetFrameAndSession(&Session, &Frame))
        return;
    // Unreal can tick faster than the camera: same timestamp, same image.
    int64_t TimestampNs = 0;
    if (!GetTimestamp(Session, Frame, this->LastFrameTimestampNs, TimestampNs)) {
        return;
    }
    this->LastFrameTimestampNs = TimestampNs;
    FARFrameData Data;
    Data.TimestampNs = TimestampNs;
    // Get the ref to the AR camera.
    ArCamera* Camera = nullptr;
    ArFrame_acquireCamera(Session, Frame, &Camera);
    // Are we tracking?
    ArTrackingState Tracking = AR_TRACKING_STATE_STOPPED;
    ArCamera_getTrackingState(Session, Camera, &Tracking);
    Data.bTracking = Tracking == AR_TRACKING_STATE_TRACKING;
    // Get the pose
    ArPose* Pose = nullptr;
    ArPose_create(Session, nullptr, &Pose);
    ArCamera_getPose(Session, Camera, Pose); // sensor pose, NOT getDisplayOrientedPose
    ArPose_getPoseRaw(Session, Pose, Data.SensorPose);
    ArPose_destroy(Pose);
    // then the intrinsics
    ArCameraIntrinsics* Intrinsics = nullptr;
    ArCameraIntrinsics_create(Session, &Intrinsics);
    ArCamera_getImageIntrinsics(Session, Camera, Intrinsics);
    ArCameraIntrinsics_getFocalLength(Session, Intrinsics, &Data.ImageFx, &Data.ImageFy);
    ArCameraIntrinsics_getPrincipalPoint(Session, Intrinsics, &Data.ImageCx, &Data.ImageCy);
    ArCameraIntrinsics_getImageDimensions(Session, Intrinsics, &Data.IntrinsicsWidth, &Data.IntrinsicsHeight);
    ArCameraIntrinsics_destroy(Intrinsics);
    // then the raw depth and it's confidence
    ArImage* DepthImage = nullptr;
    ArImage* ConfidenceImage = nullptr;
    if (ArFrame_acquireRawDepthImage16Bits(Session, Frame, &DepthImage) == AR_SUCCESS) {
        const uint8_t* Bytes = nullptr;
        int32_t Length = 0;
        ArImage_getWidth(Session, DepthImage, &Data.DepthWidth);
        ArImage_getHeight(Session, DepthImage, &Data.DepthHeight);
        ArImage_getPlaneRowStride(Session, DepthImage, 0, &Data.DepthRowStrideBytes);
        ArImage_getPlaneData(Session, DepthImage, 0, &Bytes, &Length);
        Data.DepthMm = reinterpret_cast<const uint16*>(Bytes);
        DeriveDepthIntrinsics(Data);

        if (ArFrame_acquireRawDepthConfidenceImage(Session, Frame, &ConfidenceImage) == AR_SUCCESS)
        {
            ArImage_getPlaneRowStride(Session, ConfidenceImage, 0, &Data.ConfidenceRowStrideBytes);
            ArImage_getPlaneData(Session, ConfidenceImage, 0, &Bytes, &Length);
            Data.Confidence = Bytes;
        }
    }
    else {
        DepthImage = nullptr; // NOT_YET_AVAILABLE is the normal case, not an error
    }
    // --- Camera image (YUV) ---
    ArImage* ColorImage = nullptr;
    if (ArFrame_acquireCameraImage(Session, Frame, &ColorImage) == AR_SUCCESS) {
        int32_t UvPixelStride = 0;
        ArImage_getPlanePixelStride(Session, ColorImage, 1, &UvPixelStride);
        // Interleaved chroma or nothing: reading planar as interleaved is half green.
        if (UvPixelStride == 2)
        {
            const uint8_t* U = nullptr;
            const uint8_t* V = nullptr;
            int32_t Length = 0;
            ArImage_getWidth(Session, ColorImage, &Data.ImageWidth);
            ArImage_getHeight(Session, ColorImage, &Data.ImageHeight);
            ArImage_getPlaneData(Session, ColorImage, 0, &Data.Y, &Length);
            ArImage_getPlaneRowStride(Session, ColorImage, 0, &Data.YRowStride);
            ArImage_getPlaneData(Session, ColorImage, 1, &U, &Length);
            ArImage_getPlaneData(Session, ColorImage, 2, &V, &Length);
            ArImage_getPlaneRowStride(Session, ColorImage, 1, &Data.UVRowStride);
            // U and V are two windows on one interleaved block; whichever
            // starts first decides NV12 vs NV21.
            Data.bVFirst = V < U;
            Data.UV = Data.bVFirst ? V : U;
        }
    }
    else {
        ColorImage = nullptr; // also normal for the first frames after a resume
    }
    const float ViewPoints[6] = { 0, 0, 1, 0, 0, 1 };
    ArFrame_transformCoordinates2d(Session, Frame,
        AR_COORDINATES_2D_VIEW_NORMALIZED, 3, ViewPoints,
        AR_COORDINATES_2D_IMAGE_NORMALIZED, Data.ViewToImage);
    
    //Do the broadcasts here
    OnARFrame.Broadcast(Data);
    OnARFramePose.Broadcast(MakeBlueprintPose(Data, World->GetWorldSettings()->WorldToMeters));
    //cleanup
    if (ColorImage)      ArImage_release(ColorImage);
    if (ConfidenceImage) ArImage_release(ConfidenceImage);
    if (DepthImage)      ArImage_release(DepthImage);
    ArCamera_release(Camera);
    
#endif
}
```

This is huge and there were many changes happening at the same time:
- We no longer have the tick after all actors but only the tick BEFORE the actors that make sure that AR data is there for them.
- ReadAndBroadcastFrame is the meat of the class: it:
  - Gets the native ar session and see if the we actually have a new ar data. That matters because Tick may run faster then the camera and in that case the current AR data will have the same timestamp that the previous had and is the same frame and we don't need to do anything.
  - We get a lot of data: tracking, pose, depth buffer, color buffer, confidence map... some of this data is optional and may not be present (depth, color and confidence buffers).
  - Finally we broadcast the data to the listeners.

About ARImage and it's data: Notice that it dies in the cleanup step, that runs AFTER the broadcasts. So if the objects that listen to the broadcast want to keep persisten copies they will have to memcpy them themselves. 

### Correct camera feed

### Data for the TSDF 

## Step 4 - Final touches

We already have all that we need to start implementing the TSDF based space reconstruction or use AR Planes if we so desire, this section here is just final touches and cosmetics

### Switching between RGB and depth feeds

### Turning logs on/off

