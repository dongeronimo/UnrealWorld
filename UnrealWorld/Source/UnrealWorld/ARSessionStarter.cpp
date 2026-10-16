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
        int64_t DepthTimestampNs = 0;
        ArImage_getTimestamp(Session, DepthImage, &DepthTimestampNs);
        Data.DepthTimestampNs = DepthTimestampNs;
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
