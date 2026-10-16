#include "ARCameraFeed.h"
#include "ARSessionStarter.h"
#include "Components/PostProcessComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/Texture2D.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "HAL/IConsoleManager.h"
#include "EngineUtils.h"   // TActorIterator
static TAutoConsoleVariable<int32> CVarFeedSource(
    TEXT("ar.Feed.Source"),
    0,
    TEXT("0 = Color, 1 = Depth"),
    ECVF_Default);
// (Re)creates the texture when the size changes, which in practice is the
// first frame only.
static UTexture2D* EnsureTexture(TObjectPtr<UTexture2D>& Texture, int32 Width, int32 Height,
    EPixelFormat Format, TextureFilter Filter) {
    if (Texture && Texture->GetSizeX() == Width && Texture->GetSizeY() == Height)
        return Texture;
    Texture = UTexture2D::CreateTransient(Width, Height, Format);
    Texture->SRGB = false; // Y, UV and depth are data, the material does the colour maths
    Texture->Filter = Filter;
    Texture->UpdateResource();
    return Texture;
}

// The upload happens on the render thread, a frame or so after OnARFrame
// returned and ARCore released the image. So the rows are copied into a buffer
// of our own, and the render thread frees it when it's done. A buffer kept on
// the actor would be overwritten by the next frame while the render thread may
// still be reading it.
// Rows are copied one by one: Android doesn't pad the last row to the stride,
// so copying Stride * Rows can read past the end of the plane.
static void UploadPlane(UTexture2D* Texture, const uint8* Src, int32 SrcRowStride,
    int32 RowBytes, int32 Rows, int32 BytesPerPixel) {
    uint8* Copy = static_cast<uint8*>(FMemory::Malloc(RowBytes * Rows));
    for (int32 Row = 0; Row < Rows; ++Row)
        FMemory::Memcpy(Copy + Row * RowBytes, Src + Row * SrcRowStride, RowBytes);
    // UpdateTextureRegions keeps the region pointer as well, not a copy of it.
    FUpdateTextureRegion2D* Region =
        new FUpdateTextureRegion2D(0, 0, 0, 0, RowBytes / BytesPerPixel, Rows);
    Texture->UpdateTextureRegions(0, 1, Region, RowBytes, BytesPerPixel, Copy,
        [](uint8* Data, const FUpdateTextureRegion2D* Regions) {
            FMemory::Free(Data);
            delete Regions;
        });
}

AARCameraFeed::AARCameraFeed() {
    // Driven by OnARFrame, not by tick.
    PrimaryActorTick.bCanEverTick = false;
    PostProcess = CreateDefaultSubobject<UPostProcessComponent>(TEXT("Feed Post Process"));
    RootComponent = PostProcess;
    // Unbound: applies to the whole view, wherever the actor is.
    PostProcess->bUnbound = true;
    // Exposure still scales a Replacing the Tonemapper output. With an empty
    // scene, auto exposure brightens all the way and the feed washes out
    // (measured: x2.4). The camera already exposed the image, so fix the gain
    // at 1: manual, no physical camera model, bias 0.
    FPostProcessSettings& Settings = PostProcess->Settings;
    Settings.bOverride_AutoExposureMethod = true;
    Settings.AutoExposureMethod = AEM_Manual;
    Settings.bOverride_AutoExposureApplyPhysicalCameraExposure = true;
    Settings.AutoExposureApplyPhysicalCameraExposure = false;
    Settings.bOverride_AutoExposureBias = true;
    Settings.AutoExposureBias = 0.f;
}

void AARCameraFeed::BeginPlay() {
    Super::BeginPlay();
    if (FeedMaterial) {
        FeedMID = UMaterialInstanceDynamic::Create(FeedMaterial, this);
        PostProcess->AddOrUpdateBlendable(FeedMID.Get(), 1.f);
    }
    if (UARSessionStarter* Starter = GetGameInstance()->GetSubsystem<UARSessionStarter>())
        FrameHandle = Starter->OnARFrame.AddUObject(this, &AARCameraFeed::HandleFrame);

}

void AARCameraFeed::EndPlay(const EEndPlayReason::Type EndPlayReason) {
    // The subsystem outlives the actor, so it has to forget us explicitly.
    if (UGameInstance* GameInstance = GetGameInstance())
        if (UARSessionStarter* Starter = GameInstance->GetSubsystem<UARSessionStarter>())
            Starter->OnARFrame.Remove(FrameHandle);
    FrameHandle.Reset();

}

void AARCameraFeed::SetFeedEnabled(bool bEnabled) {
    PostProcess->bEnabled = bEnabled;
}

void AARCameraFeed::HandleFrame(const FARFrameData& Frame) {
    if (!PostProcess->bEnabled || !FeedMID)
        return;
    if (Source == EARFeedSource::Color)
        UpdateColor(Frame);
    else
        UpdateDepth(Frame);
}

void AARCameraFeed::UpdateColor(const FARFrameData& Frame) {
    if (!Frame.Y || !Frame.UV)
        return; // keep showing the last image
    const int32 W = Frame.ImageWidth, H = Frame.ImageHeight;
    // Chroma is half resolution both ways; each texel is one (U,V) or (V,U) pair.
    EnsureTexture(YTexture, W, H, PF_G8, TF_Bilinear);
    EnsureTexture(UVTexture, W / 2, H / 2, PF_R8G8, TF_Bilinear);
    UploadPlane(YTexture, Frame.Y, Frame.YRowStride, W, H, 1);
    UploadPlane(UVTexture, Frame.UV, Frame.UVRowStride, (W / 2) * 2, H / 2, 2);

    FeedMID->SetTextureParameterValue(TEXT("FeedY"), YTexture);
    FeedMID->SetTextureParameterValue(TEXT("FeedUV"), UVTexture);
    FeedMID->SetScalarParameterValue(TEXT("VFirst"), Frame.bVFirst ? 1.f : 0.f);
    SetViewToImage(Frame.ViewToImage);
}

void AARCameraFeed::UpdateDepth(const FARFrameData& Frame) {
    if (!Frame.DepthMm || Frame.IntrinsicsHeight == 0)
        return; // normal while the phone is still
    const int32 W = Frame.DepthWidth, H = Frame.DepthHeight;
    // Nearest: blending a 0 (no estimate) with its neighbours invents depths.
    EnsureTexture(DepthTexture, W, H, PF_G16, TF_Nearest);
    UploadPlane(DepthTexture, reinterpret_cast<const uint8*>(Frame.DepthMm),
        Frame.DepthRowStrideBytes, W * 2, H, 2);
    FeedMID->SetTextureParameterValue(TEXT("FeedDepth"), DepthTexture);
    // Same size as the depth map, one byte per pixel, 255 = most confident.
    if (Frame.Confidence) {
        EnsureTexture(ConfidenceTexture, W, H, PF_G8, TF_Nearest);
        UploadPlane(ConfidenceTexture, Frame.Confidence, Frame.ConfidenceRowStrideBytes, W, H, 1);
        FeedMID->SetTextureParameterValue(TEXT("FeedConfidence"), ConfidenceTexture);
    }

    // ViewToImage is in colour image coordinates. The depth map is the colour
    // image centre-cropped to the depth aspect (see DeriveDepthIntrinsics), so
    // move the three points into the crop.
    const float SrcAspect = float(Frame.IntrinsicsWidth) / float(Frame.IntrinsicsHeight);
    const float DepthAspect = float(W) / float(H);
    float CropW = 1.f, CropH = 1.f; // fraction of the colour image the depth covers
    if (DepthAspect > SrcAspect) CropH = SrcAspect / DepthAspect;
    else                         CropW = DepthAspect / SrcAspect;
    float ViewToDepth[6];
    for (int32 i = 0; i < 3; ++i) {
        ViewToDepth[i * 2]     = (Frame.ViewToImage[i * 2]     - (1.f - CropW) * 0.5f) / CropW;
        ViewToDepth[i * 2 + 1] = (Frame.ViewToImage[i * 2 + 1] - (1.f - CropH) * 0.5f) / CropH;
    }
    SetViewToImage(ViewToDepth);
}

// The three points are where view corners (0,0), (1,0), (0,1) land in the image.
void AARCameraFeed::SetViewToImage(const float ViewToImage[6]) {
    const float* P = ViewToImage;
    FeedMID->SetVectorParameterValue(TEXT("ViewToImageOrigin"),
        FLinearColor(P[0], P[1], 0.f, 0.f));
    FeedMID->SetVectorParameterValue(TEXT("ViewToImageAxes"),
        FLinearColor(P[2] - P[0], P[3] - P[1], P[4] - P[0], P[5] - P[1]));
}

