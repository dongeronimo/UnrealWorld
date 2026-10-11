
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

### Appendix: how do i found the Sampling Rate issue
- I have a native (as in Java + Cpp + Vulkan) arcore app that do space reconstruction, basically an early prototype of what I'm doing in Unreal.
- It creates it's own arcore session and works fine, while the Unreal version in the same device fails.
- By grepping the manifest it became clear what was missing. 
- Without the previous work in the hand-made AR renderer i'd never find the difference and the project in Unreal would die. That's why AR in Unreal Engine is the Gom Jabbar.

### Getting ARCore to actually run
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