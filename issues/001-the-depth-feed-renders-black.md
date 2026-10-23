# 001 — The depth feed renders black

**Area:** ar + render · **Status:** open · **Blocks:** eyeballing depth quality on the device (009, 011)

## Context

AR Camera Feed was created in such a way that it can render either the rgb feed (actually yuv converted to rgb) or the depth feed with confidence data. The RGB feed works as intended, the depth not so much.

The relevant fields are `AARCameraFeed::Source`, `AARCameraFeed::FeedMaterial` and `AARCameraFeed::SetFeedEnabled`.

Source controls whether it will render Color or Depth and set feed enabled controls whether it is to actually render the feed or not. FeedMaterial is the material that is used to render, there's one material for color and another to depth.

The intended way to use ARCameraFeed is to create 2 blueprints (`BP_ARCameraFeed`, `BP_ARDepthFeed`), one of them to render the color, another to render the depth and only enable one of them. The material and the Source must align: `M_CameraDepthConfidenceFeed` with `Source==Depth` and `M_CameraRGBFeed` with `Source=Color`.

The bug is that BP_ARCameraFeed works as intended while BP_ARDepthFeed does not. BP_ARDepthFeed renders all black in distances that I know it should show depth values.

## The possibilities:
1) AR Camera Feed is actually working as designed and the problem is in the shader - either data is passed wrongly to it or MaxDepthMeters needs tuning: it is at 5m at the moment and `  float meters = Depth * 65.535; float v = 1 - saturate(meters / MaxDepth);` can make it go towards zero. Would have to use render doc in android to see what's happening.
2) Depth data don't have what I think it has, it's not in the range I think it, etc.

Right now `BP_ARDepthFeed` is hard disabled: PostProcess is manually disabled in the bp dropped in the level, Rendering is false too and hidden in game is true.

## Done when

It'll be considered fixed when console command `ar.Feed.Source 1` changes to depth view, activating what has to be activated in `BP_ARDepthFeed` and the depth values are shown in the screen in such a way that they make sense and `ar.Feed.Source 0` changes to color view. 

