#pragma once
// One ARCore frame as plain numbers and borrowed pointers. Not a USTRUCT,
// because reflection can't describe raw pointers into ARCore's images.
// Everything in here is only valid while OnARFrame is broadcasting: use it
// or copy it, never keep a pointer.
struct FARFrameData
{
    int64 TimestampNs = 0;

    // Sensor pose in ARCore's frame: right-handed, metres, +Y up, -Z forward.
    // Only meaningful while bTracking is true.
    bool bTracking = false;
    float SensorPose[7] = {}; // qx qy qz qw tx ty tz

    // Colour image intrinsics, in pixels of the CPU image.
    float ImageFx = 0, ImageFy = 0, ImageCx = 0, ImageCy = 0;
    int32 IntrinsicsWidth = 0, IntrinsicsHeight = 0;

    // Raw depth in millimetres, 0 = no estimate. Null when ARCore has none
    // this frame, which is normal whenever the phone is still.
    const uint16* DepthMm = nullptr;
    // When ARCore produced this depth image. Depth updates slower than the
    // camera, so consecutive frames can carry the same one: same timestamp,
    // same image. Integrating it twice would carve twice.
    int64 DepthTimestampNs = 0;
    int32 DepthWidth = 0, DepthHeight = 0, DepthRowStrideBytes = 0;
    // ARCore has no depth intrinsics API; these are derived from the colour ones.
    float DepthFx = 0, DepthFy = 0, DepthCx = 0, DepthCy = 0;

    // 0..255 per depth pixel. Null when unavailable.
    const uint8* Confidence = nullptr;
    int32 ConfidenceRowStrideBytes = 0;

    // Camera image, YUV 4:2:0 with interleaved chroma. Null when unavailable,
    // or when the layout isn't interleaved (we refuse rather than guess).
    const uint8* Y = nullptr;
    const uint8* UV = nullptr;
    bool bVFirst = false; // true = NV21, false = NV12
    int32 ImageWidth = 0, ImageHeight = 0, YRowStride = 0, UVRowStride = 0;

    // Where view corners (0,0), (1,0), (0,1) land in normalised image
    // coordinates. Three points define the affine view→image map.
    float ViewToImage[6] = {};

};