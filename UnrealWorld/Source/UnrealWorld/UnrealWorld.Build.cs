// Copyright Epic Games, Inc. All Rights Reserved.

using System.IO;
using UnrealBuildTool;

public class UnrealWorld : ModuleRules
{
	public UnrealWorld(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
	
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", 
            "InputCore", "EnhancedInput" });

		PrivateDependencyModuleNames.AddRange(new string[] {
            "AugmentedReality",   // UARBlueprintLibrary, UARSessionConfig (chapter 3)
            "ARUtilities",        // M_ScreenSpacePassthroughCamera, UpdateCameraTextureParam
            "RenderCore",         // ENQUEUE_RENDER_COMMAND, FlushRenderingCommands
            "RHI",                // FRHICommandListImmediate
            "HeadMountedDisplay", // IXRCamera::GetPassthroughCameraUVs_RenderThread        
        });

        if (Target.Platform == UnrealTargetPlatform.Android)
        {
            PrivateDependencyModuleNames.AddRange(new string[] {
                                  "GoogleARCoreBase",
                                  "GoogleARCoreSDK",       // supplies arcore_c_api.h
                                  "GoogleARCoreRendering", // GoogleARCoreDevice.h includes a header from it
                          });

            // Only the engine plugin's folder goes here. Nothing of your own.
            PrivateIncludePaths.Add(Path.Combine(EngineDirectory,
                    "Plugins", "Runtime", "AR", "Google", "GoogleARCore",
                    "Source", "GoogleARCoreBase", "Private"));
        }
        // Uncomment if you are using Slate UI
        // PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

        // Uncomment if you are using online features
        // PrivateDependencyModuleNames.Add("OnlineSubsystem");

        // To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
    }
}
