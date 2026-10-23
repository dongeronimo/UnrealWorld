# 003 — The chunks ignore the colour OpenChisel fuses, on the fixture and on the phone

**Area:** render · **Status:** open · **Blocks:** judging the reconstruction by eye (006–011 are easier with it)

## Context

*Filed 2026-10-23.*

The fusion already carries colour. `FTsdfConfig::bColor` is on, `AReconstructionActor::bIntegrateColor`
defaults to true, the depth path fuses the YUV image into the voxels (fork change §7 in
`OPENCHISEL-README.md`), and `AReconChunkActor::SetGeometry` always writes a colour stream into the
RealtimeMesh section. **Nothing reads it.** Both the fixture and the phone use `M_ChunkUnshaded`, which
is Unlit with `Emissive = VertexNormalWS * 0.5 + 0.5`. It colours by normal, to make the shape
readable in a level with no lights.

What the vertex colour holds (see `FTsdfChunkMesh::Colors`):
- **RGB:** **gamma encoded**, as the camera saw it.
- **A:** how much colour evidence stands behind it. 0 means never seen in colour, and 255 means
  `ColorFullConfidenceWeight` (4) observations or more.

Two materials are wanted:

1. **Fixture, `M_ChunkColour`.** Unlit, emissive = the vertex colour, decoded to linear.
   - Where A is low, lerp towards the normal colour, so unseen geometry is still readable
     instead of black.
   - The fixture is for looking at a recorded room from anywhere, so this is the colour that
     tells you whether the fusion put the right colour in the right place.
2. **Phone, `M_ChunkColourAR`.** The same colour, shown over the camera feed.
   - The feed is a post process that replaces the tonemapper, and it only writes where
     `SceneDepth` is the far plane (Step 10 of `running_the_reconstruction.md`).
   - So the mesh is visible where it was drawn, and a toggle between "mesh", "feed" and
     "50/50 blend" makes misregistration obvious: the mesh colour should line up with the feed's
     edges.
   - A console variable is enough for the toggle (`recon.Chunk.View 0|1|2`).

Both are set on the blueprints, `BP_ReconstructionActor` and whatever the fixture places, never
found by path (`ChunkMaterial` is already a `UPROPERTY`).

## The tempting wrong fixes

- **Feeding the vertex colour straight into Emissive.** It's gamma encoded. Unreal's Vertex
  Color node hands the bytes over as 0..1 without an sRGB decode, so the room comes out washed
  out and too bright. Decode it in the material (a `pow(c, 2.2)` or the exact sRGB curve).
  Don't change the C++: the snapshot format and the stored voxels are gamma, and changing what
  the bytes mean would make every saved world wrong.
- **Making the chunks Lit "to look nicer".** The AR level has no lights, and the camera's
  colour already includes the room's lighting. Lighting it again lights it twice.
- **Changing `M_ChunkUnshaded`.** Keep it. It's the material for reading geometry, and both
  views stay useful.

## Watch for

- **`room1.tsdf` may have been saved without colour.** A chunk with no colour has an empty
  `Rgbw`, and the mesh then carries A = 0 everywhere. If the fixture shows only the fallback,
  check the file before suspecting the material.
- **Colour on the phone has never been looked at.** It has been fused but never shown, so the
  first look may reveal a registration problem: the YUV and depth intrinsics are expressed
  against different image sizes (`FTsdfColorFrame::IntrinsicsWidth/Height`). That is a separate
  card if it appears.

## Done when

- The fixture shows `room1`, or a newly saved room, in camera colour, with the normal-colour
  fallback where A is low.
- On the phone, the coloured mesh draws over the feed, and the toggle switches mesh, feed and
  blend. A screenshot of the blend view goes in the card.

## Files

```
UnrealWorld/Source/UnrealWorld/ReconChunkActor.cpp       the colour stream
UnrealWorld/Source/UnrealWorld/ReconstructionActor.h     ChunkMaterial, bIntegrateColor
UnrealWorld/Plugins/Reconstruction/Source/Reconstruction/Public/TsdfReconstruction.h   FTsdfChunkMesh::Colors
UnrealWorld/Content/Materials/M_ChunkUnshaded, M_CameraRGBFeed
running_the_reconstruction.md                            Steps 9 and 10
```
