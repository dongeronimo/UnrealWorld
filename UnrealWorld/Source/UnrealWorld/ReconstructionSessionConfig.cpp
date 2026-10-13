#include "ReconstructionSessionConfig.h"

UReconstructionSessionConfig::UReconstructionSessionConfig()
{
    EnabledSessionTrackingFeature = EARSessionTrackingFeature::SceneDepth;
    bEnableAutoFocus = false;
    bHorizontalPlaneDetection = false;
    bVerticalPlaneDetection = false;
    LightEstimationMode = EARLightEstimationMode::AmbientLightEstimate;
    bEnableAutomaticCameraOverlay = false;
}
