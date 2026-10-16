#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ARCameraFeed.generated.h"
struct FARFrameData;
class UTexture2D;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UPostProcessComponent;

UENUM(BlueprintType)
enum class EARFeedSource : uint8 {
    Color, // camera image as Y + UV textures, converted to RGB in the material
    Depth, // raw depth, millimetres as a G16 texture
};

// Shows one ARCore image stream full screen, through an unbound post-process.
// Several can coexist (colour, depth for debugging); keep only one enabled at a time
// or they draw over each other.
//
// Material parameters it sets:
//   Color: FeedY (G8), FeedUV (R8G8), VFirst (1 = NV21, bytes are V,U)
//   Depth: FeedDepth (G16, value * 65535 = millimetres, 0 = no estimate)
//          FeedConfidence (G8, 0..1, 1 = most confident)
//   Both:  ViewToImageOrigin (xy), ViewToImageAxes (xy = +view x, zw = +view y)
//          image uv = Origin.xy + ViewUV.x * Axes.xy + ViewUV.y * Axes.zw
UCLASS()
class AARCameraFeed : public AActor {
    GENERATED_BODY()
public:
    AARCameraFeed();

    UPROPERTY(EditAnywhere, Category = "AR Feed")
    EARFeedSource Source = EARFeedSource::Color;

    // A Post Process domain material reading the parameters above.
    UPROPERTY(EditAnywhere, Category = "AR Feed")
    TObjectPtr<UMaterialInterface> FeedMaterial;

    // Off = nothing drawn and nothing uploaded. The last image is kept.
    UFUNCTION(BlueprintCallable, Category = "AR Feed")
    void SetFeedEnabled(bool bEnabled);

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    void HandleFrame(const FARFrameData& Frame);
    void UpdateColor(const FARFrameData& Frame);
    void UpdateDepth(const FARFrameData& Frame);
    void SetViewToImage(const float ViewToImage[6]);



    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UPostProcessComponent> PostProcess;

    // Transient UPROPERTYs: the GC keeps them alive.
    UPROPERTY(Transient)
    TObjectPtr<UMaterialInstanceDynamic> FeedMID;
    UPROPERTY(Transient)
    TObjectPtr<UTexture2D> YTexture;
    UPROPERTY(Transient)
    TObjectPtr<UTexture2D> UVTexture;
    UPROPERTY(Transient)
    TObjectPtr<UTexture2D> DepthTexture;
    UPROPERTY(Transient)
    TObjectPtr<UTexture2D> ConfidenceTexture;

    FDelegateHandle FrameHandle;
};
