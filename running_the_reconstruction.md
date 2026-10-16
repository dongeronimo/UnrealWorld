
## The plan

`arcore_in_unreal.md` got ARCore pushing `FARFrameData` (camera image, raw depth, confidence, intrinsics, pose) to whoever listens. `adding_open_chisel.md` got OpenChisel compiling inside the `Reconstruction` plugin, with nobody calling it. This step connects the two: depth goes into the TSDF, meshes come out, and the meshes show up on the phone on top of the camera feed.

No colour, collision, navmesh, anchors or saving yet. Only geometry, as simple as possible, to confirm that the whole chain works on the device.

## Step 1 - Where the reconstruction lives: an actor, not a subsystem

This is the biggest difference from ToySoldiers. There, the reconstruction was global. Here it's **an actor that has many actors as children**:

```
AReconstructionActor          (transform = ARCore tracking space -> Unreal world)
  AReconChunkActor (0,0,0)    (relative location = chunk origin)
  AReconChunkActor (1,0,0)
  ...
```

Why:

- **Subsystems are too global and too powerful.** Anything anywhere can reach them, and their lifetime is the game instance's, not the level's. The reconstruction is part of the world, not of the game.
- **The lifetime is right.** The reconstruction dies with the level. That's fine as long as the field (and the anchor) get saved when the Android activity lifecycle would kill our data (task switch, locking the phone). That's for later.
- **One transform carries the whole room.** Tracking space to Unreal space is the root actor's transform, and the chunks are attached to it. Today that transform is copied from the pawn. Later an ARCore anchor goes there, and nothing else changes.
- **Navigation and collision don't care.** Navigation registers per component (ToySoldiers calls `FNavigationSystem::UpdateComponentData(*this)` per chunk component), so chunks as child actors work the same as chunks as components.
- **"But others have to find it"** isn't a real problem. Whoever needs it gets a reference, like anything else in Unreal.

The only subsystem stays `UARSessionStarter`, because the ARCore session really is global.

## Step 2 - The wrapper: FTsdfReconstruction

It goes in the `Reconstruction` module, next to OpenChisel, because OpenChisel has no export macros and can't be called from another DLL (Step 3 of `adding_open_chisel.md`). It's the only thing in that module with `RECONSTRUCTION_API`.

The header has the rule from Step 4 of `adding_open_chisel.md` written at the top: no `<open_chisel/...>`, no Eigen type. Everything Chisel goes behind a pimpl:

```cpp
class RECONSTRUCTION_API FTsdfReconstruction
{
public:
    explicit FTsdfReconstruction(const FTsdfConfig& Config);
    ~FTsdfReconstruction();

    // Fuses one depth image. Returns false if nothing in it survived the filters.
    bool Integrate(const FTsdfDepthFrame& Frame);

    // Runs marching cubes on up to MaxChunks dirty chunks. OutChanged gets the
    // chunks that now have a surface, OutRemoved those that had one and lost it.
    void Remesh(int32 MaxChunks, TArray<FIntVector>& OutChanged, TArray<FIntVector>& OutRemoved);

    bool GetChunkMesh(const FIntVector& Key, FTsdfChunkMesh& Out) const;
    FVector3f GetChunkOrigin(const FIntVector& Key) const;

    int32 GetPendingRemeshCount() const;
    const FTsdfStats& GetLastStats() const;
    const FTsdfConfig& GetConfig() const;

private:
    struct FImpl;
    TUniquePtr<FImpl> Impl;
};
```

Two decisions about the interface:

- **Everything in it is in ARCore tracking space**: right-handed, metres, +Y up. Converting to Unreal's left-handed centimetres with +Z up is the caller's job, so it happens in exactly one place (Step 7).
- **`FTsdfConfig` is all metres**, with the unit written next to each field. 16³ voxels of 4 cm (64 cm chunks), 6 cm truncation, depth range 0.3 to 3 m, carving on, confidence threshold 32 out of 255.

`FTsdfDepthFrame` is just pointers and numbers. The pointers are ARCore's own image memory, straight from `FARFrameData`, so they're only valid during the `OnARFrame` broadcast. `Integrate` copies what it needs and keeps nothing.

That's also why integration runs on the game thread, inside the broadcast. Back in the Project Tango days, phones could integrate on a single thread just fine, and modern phones are an order of magnitude faster. The numbers at the end of this doc agree.

## Step 3 - Integrate

Three things happen before OpenChisel sees the frame.

**Millimetres to metres, and 0 to NaN.** ARCore's raw depth is `uint16` millimetres, 0 meaning "no estimate". OpenChisel's integrator only skips a sample when it's `isnan`. A 0 would read as a surface touching the lens, and carving would dig a hole through everything in front of it wherever ARCore wasn't sure. So 0, out of range and low confidence all become NaN.

**Confidence as weight, not just as a threshold.** Below `ConfidenceThreshold` the sample is dropped. Above it, the weight goes from a floor to 1 along a curve:

```cpp
const float T = (Conf[Col] - Base) / Span;
const float Shaped = bSquared ? T * T : std::pow(T, C.ConfidenceWeightExponent);
Weight = Floor + (1.0f - Floor) * Shaped;
```

The weights go into an image of the same size as the depth, handed to the integrator with `SetWeights` (that's the per-pixel weight modification in the fork). Depth on the Galaxy S22 and S25 is shit, and a threshold high enough to kill the bad samples also kills the floor. Weighting lets the floor accumulate slowly instead of disappearing.

**The pose.** ARCore's sensor pose is OpenGL convention: +Y up, looking down -Z. OpenChisel's integrator is computer vision convention: +Y down, +Z forward, depth read off `.z()`. So the rotation gets a flip of Y and Z:

```cpp
const Eigen::Quaternionf Rotation(Pose[3], Pose[0], Pose[1], Pose[2]); // w first
chisel::Transform T = chisel::Transform::Identity();
T.linear() = Rotation.toRotationMatrix() * Eigen::DiagonalMatrix<float, 3>(1.0f, -1.0f, -1.0f);
T.translation() = Eigen::Vector3f(Pose[4], Pose[5], Pose[6]);
```

Get this wrong and the reconstruction is a mirrored, upside-down mess, which is easy to mistake for bad depth.

`chisel::DepthImage` owns its buffer (it `delete[]`s it), so it can't point at ARCore's memory. The depth and weight images are allocated once and written into every frame.

Colour is off (`Chisel(..., false)`). It's fixed at construction, because chunks allocate their colour arrays (or don't) when they're created. Geometry first.

## Step 4 - Remesh

Integration marks chunks dirty. Marching cubes on a dirty chunk is what produces the mesh. A sweep of the phone dirties hundreds of chunks at once, and meshing all of them in one frame is a dropped frame. So `Remesh` takes a budget (`RemeshBudgetPerTick`, 8 by default).

With a budget comes a fairness problem. The obvious approach, taking the first N from OpenChisel's dirty set every frame, starves whatever hashes into the later buckets: new dirt keeps arriving at the front and those chunks never get meshed. So the wrapper keeps its own queue, and refills it from the dirty set (that's the "mutable access to the dirty set" modification) **only when it's empty**. Every chunk dirty at the start of a cycle gets meshed before anything newer.

Two more details:

- Integration dirties a 3x3x3 neighbourhood of chunks, which reaches chunks that were never allocated. Those get skipped.
- A `Live` set remembers which chunks had a surface last time, so a chunk that loses its surface (carving) can be reported as removed instead of silently staying on screen.

`GetChunkMesh` subtracts the chunk origin from every vertex. The mesh is stored relative to its chunk, which lets the float32 vertices keep their precision however far the chunk is from the tracking origin; the actor transform (doubles) puts it back in place.

## Step 5 - The same depth image twice

Depth updates slower than the camera. ARCore gives you a depth image on most camera frames, but often it's the same one as last frame. Integrating it twice counts one observation twice, and with carving on, carves twice.

So `FARFrameData` gained a timestamp, read in `UARSessionStarter`:

```cpp
int64_t DepthTimestampNs = 0;
ArImage_getTimestamp(Session, DepthImage, &DepthTimestampNs);
Data.DepthTimestampNs = DepthTimestampNs;
```

and the reconstruction actor skips any frame whose depth timestamp equals the last one it integrated. On the phone that's around two thirds of the frames (see the log at the end).

## Step 6 - RealtimeMeshComponent

The chunk meshes are drawn with RealtimeMeshComponent (RMC), not ProceduralMeshComponent (PMC). Marching cubes changes the topology of a chunk on every remesh, and PMC's only way to deal with that is throwing the section away and recreating it. RMC updates the section group in place.

I copied the plugin (5.3.2) from ToySoldiers, without `Binaries` and `Intermediate`, to `UnrealWorld/Plugins/RealtimeMeshComponent`. The `.gitignore` already ignores `Plugins/**/Binaries` and `Intermediate`.

The game module needs both new dependencies:

```csharp
"Reconstruction",     // FTsdfReconstruction, the TSDF (OpenChisel inside)
"RealtimeMeshComponent", // chunk meshes, updated in place on every remesh
```

## Step 7 - The chunk actor: AReconChunkActor

`UCLASS(NotPlaceable)`, because it's only ever spawned by the reconstruction actor. Its root is a `URealtimeMeshComponent` with no collision and no shadows (no collision yet, and an empty AR level has no lights).

It has two methods. `SetGeometry` builds a stream set and creates the section group the first time, then updates it:

```cpp
RealtimeMesh::FRealtimeMeshStreamSet StreamSet;
{
    RealtimeMesh::TRealtimeMeshBuilderLocal<uint32> Builder(StreamSet);
    Builder.EnableTangents();
    Builder.EnablePolyGroups();
    for (int32 V = 0; V < Positions.Num(); ++V)
        Builder.AddVertex(Positions[V]).SetNormalAndTangent(Normals[V], PerpendicularTo(Normals[V]));
    for (int32 T = 0; T + 2 < Triangles.Num(); T += 3)
        Builder.AddTriangle(Triangles[T], Triangles[T + 1], Triangles[T + 2], /*PolyGroup=*/0);
}

if (bHasSectionGroup) {
    Mesh->UpdateSectionGroup(ChunkGroupKey(), MoveTemp(StreamSet));
} else {
    Mesh->CreateSectionGroup(ChunkGroupKey(), MoveTemp(StreamSet));
    bHasSectionGroup = true;
}
```

`ClearGeometry` removes the section group. Marching cubes gives normals but no tangents; nothing samples a normal map, so any vector perpendicular to the normal will do.

## Step 8 - The reconstruction actor: AReconstructionActor

**BeginPlay** builds an `FTsdfConfig` from its properties, creates the `FTsdfReconstruction` and subscribes to `OnARFrame`. **EndPlay** unsubscribes (the subsystem outlives the actor), destroys the chunks and the TSDF.

**HandleFrame** is the broadcast handler. It skips frames without depth, frames where ARCore isn't tracking (a pose from a frame that isn't tracking would fuse depth in the wrong place) and repeated depth (Step 5), then copies the pointers into an `FTsdfDepthFrame` and calls `Integrate`.

**Tick** does three things:

1. Copies the player pawn's transform onto itself (`bFollowPawnOrigin`). The AR camera is a child of the pawn and its relative transform is the tracking pose, so the pawn's transform is tracking space to world. That's what the anchor will replace.
2. Remeshes up to the budget, spawning chunk actors as needed:

```cpp
Chunk = GetWorld()->SpawnActor<AReconChunkActor>(AReconChunkActor::StaticClass(), FTransform::Identity, Params);
// Relative: the chunk's own transform is its origin in tracking
// space and nothing else; this actor carries tracking -> world.
Chunk->AttachToActor(this, FAttachmentTransformRules::KeepRelativeTransform);
Chunk->SetActorRelativeLocation(FVector(ToUnreal(Tsdf->GetChunkOrigin(Key), WorldToMeters)));
```

   A chunk that loses its surface is cleared, not destroyed: usually it's one the sensor hasn't seen enough of yet, and it comes back.
3. Once a second, logs a `RECON` line (Step 11).

**The coordinate conversion** happens only here:

```cpp
// ARCore (right-handed, metres, +Y up, -Z forward) to Unreal (left-handed,
// centimetres, +Z up, +X forward).
FVector3f ToUnreal(const FVector3f& V, float WorldToMeters) {
    return FVector3f(-V.Z, V.X, V.Y) * WorldToMeters;
}
```

It's the same basis change as `MakeBlueprintPose` in `ARSessionStarter.cpp`. It has determinant -1, so it mirrors and the triangle winding flips. Unreal also treats the opposite winding as front-facing compared to OpenChisel's right-handed convention, and **the two flips cancel**: indices are copied unchanged. ToySoldiers settled this on the device by drawing both windings and seeing which one was solid.

## Step 9 - The blueprint and the material

`AReconstructionActor` is `UCLASS(Abstract, Blueprintable)`. What goes in the level is a blueprint subclass, and that blueprint is where the material and the settings are chosen.

My first version had the C++ constructor find the material by path with `ConstructorHelpers::FObjectFinder`, plus a `DirectoriesToAlwaysCook` entry in `DefaultGame.ini`, because the cook doesn't follow references that only exist in C++. I threw that away. Magical configurations relying on paths and patterns are a source of grief, and this one proved it straight away: the path pointed at `/Game/Materials/` while the material was still sitting in `/Game/`, so it would have found nothing, silently, and the chunks would have been grey. A `UPROPERTY` set on a blueprint is an explicit reference: the editor shows it, and the cook follows it.

So:

- `M_ChunkUnshaded` in `/Game/Materials`: Material Domain Surface, Shading Model **Unlit**, Emissive Color = `VertexNormalWS * 0.5 + 0.5`. Unlit because the level has no lights. Colouring by normal makes the shape readable without lighting: floors one colour, walls another depending on which way they face.
- `BP_ReconstructionActor` in `/Game/AR`, deriving from `AReconstructionActor`, with `ChunkMaterial = M_ChunkUnshaded`.
- `BP_ReconstructionActor` placed in `AR_Blank` at (0,0,0).

<!-- TODO: screenshot of BP_ReconstructionActor's details panel -->

## Step 10 - Seeing it: the camera feed paints over everything

First run on the phone: the log said 37 chunk actors with meshes, and the screen showed only the camera feed.

`M_CameraRGBFeed` is a post process material in **Replacing the Tonemapper**. It runs after the scene is rendered and writes the camera image into every pixel, without looking at what was there. The chunks were being drawn, and then painted over.

The fix is in the material: write the feed only where nothing was drawn. Nothing drawn means the depth is the far plane, a huge number; anything drawn is much closer.

```
SceneTexture (SceneDepth) .Color ──► ComponentMask (R) ──► If.A
Constant 100000 ───────────────────────────────────────► If.B
SceneTexture (PostProcessInput0) .Color ───────────────► If.A<B
YUV→RGB result ────────────────────────────────────────► If.A>B
YUV→RGB result ────────────────────────────────────────► If.A==B
If output ─────────────────────────────────────────────► Emissive Color
```

- `SceneDepth` is in centimetres, so 100000 is 1 km. 
- `PostProcessInput0` is the rendered scene, i.e. the chunks.
- The UVs inputs of the SceneTexture nodes stay unconnected: unconnected means "the pixel being shaded", which is what we want.
- Wire A==B too. An unconnected If input is black.
- No colour space trouble: the feed was already decoded to linear in `arcore_in_unreal.md`, so both branches are linear and the engine encodes both on the way to the screen.

For seeing the room through the mesh, `Lerp(feed, PostProcessInput0, 0.5)` in the A<B branch works.

<!-- TODO: material graph screenshot -->

## Step 11 - The result

<!-- TODO: screenshot from the phone -->

The log, once a second:

```
LogReconstruction: RECON 1.0s: 31 frames, 9 integrated (6.2 ms mean), 22 repeated depth, 0 not tracking | last: 7564 samples fused, 23 chunks touched, 9 discarded | 43 chunks, 36 actors, 180 meshed, 1 awaiting remesh
LogReconstruction: RECON 1.0s: 31 frames, 0 integrated (0.0 ms mean), 31 repeated depth, 0 not tracking | last: 7564 samples fused, 23 chunks touched, 9 discarded | 43 chunks, 36 actors, 1 meshed, 0 awaiting remesh
LogReconstruction: RECON 1.0s: 30 frames, 1 integrated (4.9 ms mean), 29 repeated depth, 0 not tracking | last: 7253 samples fused, 28 chunks touched, 10 discarded | 46 chunks, 36 actors, 27 meshed, 0 awaiting remesh
LogReconstruction: RECON 1.0s: 30 frames, 4 integrated (8.3 ms mean), 26 repeated depth, 0 not tracking | last: 10504 samples fused, 33 chunks touched, 9 discarded | 50 chunks, 37 actors, 74 meshed, 32 awaiting remesh
```

How to read it:

- **frames / integrated / repeated depth / not tracking**: camera frames in the last second, how many brought a new depth image and were fused, how many carried the same depth as before, how many came while tracking was lost. Depth arrives at well under the camera's 30 fps, and when the phone is still ARCore stops producing new depth altogether (the 0 integrated lines).
- **ms mean**: time inside `IntegrateDepthScan`. **5 to 8 ms**, on the game thread. ToySoldiers measured 22 to 68 ms per depth frame. So no worker thread.
- **samples fused**: depth pixels that survived the zero, range and confidence filters in the last integrated frame.
- **chunks touched / discarded**: chunks the integration visited, and chunks it allocated and then threw away because nothing landed in them. It's the probe for whether the ray walk is doing its job (section 9 of `OPENCHISEL-README.md`): with the old frustum fill it was ~90% wasted, with the ray walk 18–24% in the Vulkan prototype. Here it's 25–40% (9 of 23, 10 of 28, 7 of 23). Not alarming, but higher, and worth watching.
- **chunks / actors**: chunks in the TSDF, and chunk actors with a surface. Fewer actors than chunks is normal: a chunk can hold voxels with no zero crossing in it.
- **meshed / awaiting remesh**: marching cubes runs in the last second, and what's still queued. The queue goes back to 0 within a second or two, so the budget of 8 per tick keeps up.

So: the reconstruction runs on the device, on the game thread, as an actor with chunk actors under it.

## What's next

- Colour: fusing the YUV image in the depth path (the fork already supports it).
- An ARCore anchor on the root actor instead of following the pawn.
- Collision and navmesh per chunk.
- Saving the field and the anchor when Android would kill the activity (task switch, locking the phone).
- Filtering the bad depth: motion blur, grazing angles.
