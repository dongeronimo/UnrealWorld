
## The plan

With the AR frame data being pushed to whoever listens (see `arcore_in_unreal.md`), the next thing is the thing that will listen: the TSDF. For that I use OpenChisel, the reference implementation of the CHISEL paper (Klingensmith et al., *CHISEL: Real Time Large Scale 3D Reconstruction Onboard a Mobile Device using Spatially Hashed Signed Distance Fields*, RSS 2015).

This step only adds the library to the project and gets it compiling for the editor and for the phone. Nobody calls it yet. The class that feeds it `FARFrameData` and gets meshes out of it is the next step.

## Step 1 - This is NOT the OpenChisel from github

**Read this before anything else: the code in `Plugins/Reconstruction/Source/Reconstruction/openchisel/` is not replaceable by a fresh clone.**

Upstream is here:

```
https://github.com/personalrobotics/OpenChisel
commit 3a8f2fee985eea44c0bd5c3007af464e185f577b (25 Feb 2024)
```

What I put in the project is a fork that went through two previous experiments: first my native Android prototype (Java + C++ + Vulkan, CMake build), then ToySoldiers (`D:\toysoldiers\Plugins\Putorana\Source\PutoranaRecon\openchisel`). Most of the changes came out of running it on the phone and seeing the reconstruction come out wrong, slow or both, and each one cost days.

A short list of what it has that upstream doesn't:

- **Smaller voxels.** Upstream puts a virtual destructor on almost every class. `DistVoxel` is two floats and was paying 8 bytes of vtable pointer for 8 bytes of data. With the vtables gone `DistVoxel` goes from 16 to 8 bytes and `ColorVoxel` from 16 to 4, so a 16³ chunk goes from 128 KB to 48 KB. That's roughly one notch of voxel resolution for free. And remember: phones don't have that much RAM: even a flagship like Galaxy S22 will have more or less 12gb, shared between GPU, OS, other apps and our app. 
- **No virtual calls in the integration loop.** `Truncator` and `Weighter` were virtual class hierarchies called for every voxel, millions of times per second, so the compiler couldn't inline anything. Now they're concrete value types. Upstream also squared a float with `pow(x, 2)`.
- **Marching cubes shares vertices.** Upstream emits a triangle soup, a new vertex for every corner of every triangle. Now vertices are keyed on the grid edge they sit on. 4 to 4.7 times fewer vertices on device.
- **Per-pixel weights.** The depth path ignored the weighter and integrated everything with weight 1.0. Now it takes an image of per-pixel weights, which is where ARCore's confidence map goes. Weighting instead of thresholding, because a threshold high enough to kill bad samples also kills the floor.
  - I have yet to build a custom function instead of the default ones (linear, exponential) based on the actual confidence of the scene and the device as it's mentioned in passing in the paper:
  
  *It is possible [32] to directly compute the weighting function ατ from the hit probability (2) of the sensor; but in favor of better performance, linear, exponential, and constant approximations of ατ can be used [11, 12, 14, 15]. We use the constant approximation ατ (u) = 1 2τ. This results in poorer surface reconstruction quality in areas of high noise than methods which more closely approximate the hit probability of the sensor* (page 4 of the paper).
    - " `poorer surface reconstruction quality in areas of high noise than methods which more closely approximate the hit probability of the sensor` is exactly the problem that I face with the Galaxy phones since their depth data is shit due to the lack of real depth sensors.
  
- **Space carving that actually removes things.** Upstream's carving can't delete a surface, for four separate reasons (it adds weight to the voxel it's erasing, pulls it towards the surface instead of free space, tests the wrong half of the voxels, and is unreachable at the configured distance anyway). Rebuilt.
- **Colour fused in the depth path**, from the YUV camera image directly, with no second projection.
- **Integration walks the depth rays instead of filling the frustum.** This one was the biggest: 159.8 ms down to 4.8 ms per depth frame, 4-5 fps to 30 fps.
- Mutable access to the dirty chunk set so meshing can be spread over several frames, and two real bugs fixed (range loops copying every element, a `bool` function falling off the end).

Every change is marked in the source with a `LOCAL MODIFICATION:` comment explaining what and why. The long version, with the measurements, is in `openchisel/OPENCHISEL-README.md`, which came along with the code.

So: **don't "update" it from upstream, don't replace it, and don't let it exist in only one place.** It's in git here, and it still lives in ToySoldiers. If it ever needs to be re-synced with upstream (upstream gets a commit every year or two, so probably never), grep for `LOCAL MODIFICATION:` and reapply by hand.

## Step 2 - The plugin

The layout:

```
UnrealWorld/Plugins/Reconstruction/
  Reconstruction.uplugin
  Source/Reconstruction/
    Reconstruction.Build.cs
    ReconstructionModule.cpp
    openchisel/
      include/open_chisel/...
      src/...
      OPENCHISEL-README.md
```

`Reconstruction.uplugin` declares one Runtime module, `EnabledByDefault: true`, so it doesn't need an entry in the `.uproject`. `ReconstructionModule.cpp` is just `IMPLEMENT_MODULE(FDefaultModuleImpl, Reconstruction);` because Unreal wants an implementation for every module listed in a `.uplugin`, even one with nothing to start or stop.

OpenChisel keeps its own layout (`include/` and `src/`) instead of Unreal's `Public/` and `Private/`. Keeping the files identical to the other copies matters more than following the convention.

## Step 3 - Why OpenChisel can't live in a module of its own

The obvious structure is two modules: `OpenChisel`, holding the library, and `Reconstruction`, holding my code that uses it. That's how the CMake build did it, two targets. ToySoldiers tried exactly that.

It compiled and linked for Android, then failed to link the Win64 editor with 17 unresolved `chisel::` symbols.

  - We'll need a Win64 editor build because in the future we'll scan the room with the device, save the field there, copy the field to the workstation and then reconstruct the space from the field in the Editor so that we can test things like navigation, actors, etc much faster then we'd do if the only way to test was to deploy to the device.

It's the same thing I described in `arcore_in_unreal.md` about reaching into the GoogleARCore plugin's private classes, from the other side:

- The **Android** target is monolithic. Every module ends up in one big `.so`, the `_API` macros expand to nothing and every symbol resolves inside that one binary.
- The **editor** is modular. Every module is its own DLL, and a DLL only exports what is marked with an export macro (`MYMODULE_API`, which expands to `__declspec(dllexport)`).

OpenChisel is vendored code from 2014 that has never heard of an export macro. As its own module its DLL exports nothing, and any other module that calls `chisel::Chisel::IntegrateDepthScan` can't find it. The phone build works, the editor build doesn't, and the editor has to build because it builds every module of the project.

The two ways out were to add an export macro to about 25 vendored headers, which means changing every file and dragging an Unreal dependency into the library, or to put the library and the code that uses it in the same module. Same module wins: inside one DLL nothing needs exporting. Also doing such massive change to the vendored code would screw me when i tried to sync with changes that i'd eventually do in Putorana (the vk project) or toysoldiers. If everything is different diff won't save me.

It also has a side effect I like. OpenChisel's include path is **private** to the module:

```csharp
PrivateIncludePaths.Add(Path.Combine(ModuleDirectory, "openchisel", "include"));
```

so no code outside `Reconstruction` can even write `#include <open_chisel/Chisel.h>`, the compiler won't find it. That is what keeps Eigen out of the rest of the project (see the next step).

That's also why the module is called `Reconstruction` and not `OpenChisel`: the class that wraps the library, the one that takes `FARFrameData` and gives back meshes, has to go in this same module, so it isn't just OpenChisel's module.

## Step 4 - Eigen

OpenChisel is written on top of Eigen, and that's where most of the `Build.cs` comes from.

### Optimised always, even in Debug

Eigen is an expression template library. With aggressive optimisation, `a + b * c` on vectors collapses into a few instructions. Without optimisation, every one of those operations stays a chain of real function calls, temporary objects and `eigen_assert` bounds checks on every element access. It's not "a bit slower" in debug, it's **orders of magnitude slower**: lightning fast or glacially slow, with nothing in between.

For a lot of code that's just annoying. For real time reconstruction **slowness is a bug in itself**. If integration takes longer than a frame, frames get skipped, the camera moves more between the frames that do get integrated, and the reconstruction itself comes out different. Such behaviour looks like a bug (and it is, slowness itself is a bug in realtime rendering like this system) in the reconstruction algorithm instead of being caused by slowness.

So the library is always built optimised, whatever the configuration:

```csharp
OptimizeCode = CodeOptimization.Always;
```

The price: stepping through OpenChisel in a debugger is going to be painful (variables optimised out, lines jumping around).

### But Unreal has its own Eigen

I don't vendor Eigen. Unreal 5.7 ships Eigen 3.4.0 at `Engine/Source/ThirdParty/Eigen`, with a module already written for it. That's the same version the CMake build downloaded, so it's one line:

```csharp
PrivateDependencyModuleNames.Add("Eigen");
```

That's convenient but it means it's not *my* Eigen. It's shared: Chaos compiles it, so do AnimGraphRuntime, PoseSearch and FullBodyIK. 

In the CMake build the fast flags were `-O3 -DNDEBUG`, set only on OpenChisel. Eigen reads `NDEBUG` to decide whether `eigen_assert` is live. Its functions are header inline functions, so each translation unit that includes them compiles its own copy, and the linker keeps **one** of them, silently. If two translation units compile the same Eigen header with different `NDEBUG`, they produce two different bodies for the same function and the linker picks whichever it likes. That's an ODR violation, and it's the worst kind of bug: no error, no warning, and code that sometimes runs with asserts and sometimes without, depending on link order.

In CMake the fix was to set `NDEBUG` narrowly and make sure everything that touched OpenChisel's headers got the same flags. In Unreal the rule is the opposite: **don't touch NDEBUG**. Unreal already defines `NDEBUG=1` for every translation unit in every configuration that doesn't use the debug CRT, so everybody already agrees. If I set it on my module, a Debug build would have my Eigen compiled differently from Chaos's Eigen, and I'd be the one creating the ODR violation.

So it comes down to keeping Eigen contained:

- Eigen is a **private** dependency, so its include paths only reach this module.
- OpenChisel's headers are on a **private** include path, so nothing outside this module parses them.
- The wrapper class I write next **must not leak Eigen types via its public headers**. Floats, arrays, Unreal types, anything but Eigen. If an Eigen type leaks into a public header, every module that includes it starts compiling Eigen with its own flags.

### One thing Unreal changed in its Eigen

ToySoldiers once blamed `EIGEN_STRONG_INLINE=inline` (set by `Eigen.Build.cs`) for slow integration. It's a no-op: on clang, the Android compiler, stock Eigen already defines it as plain `inline`.

The actual difference is that Epic edited their copy of Eigen's `Macros.h`:

```cpp
// LOCAL CHANGE: do not use __attribute__((always_inline)) as this
// gives a warning on the PS4 Debug build
#define EIGEN_ALWAYS_INLINE EIGEN_STRONG_INLINE
```

Stock Eigen forces inlining on the coefficient accessors, the hottest code in the integrator. Unreal's copy turns that into a hint. There's no `#ifndef` around it, so a `-D` can't undo it. The only way back would be to vendor stock Eigen and put it first on the include path. I'm not doing that now: `-O3` is on and clang inlines small functions anyway, so this is a small effect, not a disaster. If integration ever measures slower than it did in the Vulkan prototype, this is the first place to look.

## Step 5 - The rest of the Build.cs

These came from the same ToySoldiers file, and each one is there because something broke without it:

```csharp
FPSemantics = FPSemanticsMode.Imprecise;
```
Unreal compiles with `-ffp-contract=off`, which forbids fusing a multiply and an add into one FMA instruction (i think). Unreal wants that for determinism (replication, replays). The integrator is almost entirely dot products and matrix-vector products, so it's almost all multiply-adds, and each one becomes two instructions. A TSDF fed by a noisy depth sensor doesn't care about bit-exact floats. This only applies to this module.

```csharp
bEnableExceptions = true;
```
`Raycast.cpp` throws `std::out_of_range`. Under Unreal's default `-fno-exceptions` that's a compile error, not a warning.

```csharp
PCHUsage = PCHUsageMode.NoPCHs;
bUseUnity = false;
```
This code has never seen an Unreal header and will never see, at least the OpenChisel part. A shared PCH would force one in, and unity builds would glue `.cpp` files together that were written assuming they're separate.

```csharp
bWarningsAsErrors = false;
CppCompileWarningSettings.RangeLoopConstructWarningLevel = WarningLevel.Off;
// ... and the rest
```
The targets use `BuildSettingsVersion.V6`, which turns warnings into errors. OpenChisel produces plenty of warnings, so they're turned off for this module only. Two of them Unreal won't let me turn off on clang (`-Wrange-loop-construct` and `-Wreturn-type`), and those were fixed in the source in ToySoldiers. They're the two bugs at the end of the Step 1 list.

## Step 6 - Testing the build

Editor:

```powershell
& "D:\UE5.7\UE_5.7\Engine\Build\BatchFiles\Build.bat" UnrealWorldEditor Win64 Development `
  -Project="D:\UnrealWorld\UnrealWorld\UnrealWorld.uproject" -WaitMutex
```

Phone:

```powershell
& "D:\UE5.7\UE_5.7\Engine\Build\BatchFiles\Build.bat" UnrealWorld Android Development `
  -Project="D:\UnrealWorld\UnrealWorld\UnrealWorld.uproject" -WaitMutex
```

Both succeed. MSVC prints a few harmless warnings (`%lu` with a `size_t` in two debug `printf`s, and a struct padded because of alignment). I left them alone so the files stay identical to ToySoldiers' copy.

Note that the `UnrealWorld` game module doesn't depend on `Reconstruction` yet. The plugin builds because it's enabled, but nothing links against it. That dependency comes with the wrapper class.

## What's next

The wrapper class inside `Reconstruction`: a game facing class with no Eigen in its headers, that listens to `FARFrameData`, converts depth from millimetres to metres, uses the confidence map as per-pixel weights, integrates, and gives meshes back.
