// The promise UReconstructionPersistence makes: a world that goes through a file
// comes back as the same voxels and meshes into the same triangles, colour
// included. Run from the editor's Session Frontend, or headless:
//
//     UnrealEditor-Cmd.exe UnrealWorld.uproject -nullrhi -unattended
//         -ExecCmds="Automation RunTests UnrealWorld.Reconstruction; quit"
#include "ReconstructionPersistence.h"
#include "TsdfReconstruction.h"
#include "HAL/FileManager.h"
#include "Misc/AutomationTest.h"

#if WITH_DEV_AUTOMATION_TESTS

namespace {
    // A flat wall 1 m in front of a camera at the origin, grey with a red
    // band, which is enough to give several chunks a surface and a colour.
    bool IntegrateSyntheticWall(FTsdfReconstruction& Tsdf) {
        constexpr int32 DW = 160, DH = 120, CW = 320, CH = 240;
        TArray<uint16> Depth;
        Depth.Init(1000, DW * DH);
        TArray<uint8> Confidence;
        Confidence.Init(255, DW * DH);
        TArray<uint8> Y, UV;
        Y.Init(128, CW * CH);
        UV.Init(128, CW * CH / 2);
        // V high on the left third: reddish.
        for (int32 Row = 0; Row < CH / 2; ++Row)
            for (int32 Col = 0; Col < CW / 3; Col += 2)
                UV[Row * CW + Col + 1] = 220;

        FTsdfDepthFrame F;
        F.DepthMm = Depth.GetData();
        F.Width = DW;
        F.Height = DH;
        F.RowStrideBytes = DW * sizeof(uint16);
        F.Confidence = Confidence.GetData();
        F.ConfidenceRowStrideBytes = DW;
        F.Fx = F.Fy = 100.0f;
        F.Cx = DW / 2.0f;
        F.Cy = DH / 2.0f;
        F.SensorPose[3] = 1.0f; // identity rotation, at the origin
        F.Color.Y = Y.GetData();
        F.Color.UV = UV.GetData();
        F.Color.Width = CW;
        F.Color.Height = CH;
        F.Color.YRowStride = CW;
        F.Color.UVRowStride = CW;
        F.Color.Fx = F.Color.Fy = 200.0f;
        F.Color.Cx = CW / 2.0f;
        F.Color.Cy = CH / 2.0f;
        F.Color.IntrinsicsWidth = CW;
        F.Color.IntrinsicsHeight = CH;
        return Tsdf.Integrate(F);
    }

    TMap<FIntVector, FTsdfChunkMesh> MeshEverything(FTsdfReconstruction& Tsdf) {
        TMap<FIntVector, FTsdfChunkMesh> Meshes;
        TArray<FIntVector> Changed, Removed;
        while (Tsdf.GetPendingRemeshCount() > 0) {
            Tsdf.Remesh(64, Changed, Removed);
            for (const FIntVector& Key : Changed)
                Tsdf.GetChunkMesh(Key, Meshes.FindOrAdd(Key));
        }
        return Meshes;
    }
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FReconstructionPersistenceRoundTrip, "UnrealWorld.Reconstruction.PersistenceRoundTrip",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FReconstructionPersistenceRoundTrip::RunTest(const FString& Parameters) {
    FTsdfConfig Config;
    Config.ChunkVoxels = 8; // something other than the defaults, so the file's config has to win
    Config.VoxelMetres = 0.05f;
    Config.TruncationMetres = 0.1f;
    FTsdfReconstruction Original(Config);
    if (!TestTrue(TEXT("synthetic wall integrates"), IntegrateSyntheticWall(Original)))
        return false;
    const TMap<FIntVector, FTsdfChunkMesh> Before = MeshEverything(Original);
    TestTrue(TEXT("the wall has a surface"), Before.Num() > 0);

    FTsdfSnapshot Saved;
    Original.Export(Saved);
    UReconstructionPersistence* Persistence = NewObject<UReconstructionPersistence>();
    Persistence->Folder = TEXT("ReconTest");
    FString Path;
    if (!TestTrue(TEXT("saves"), Persistence->Save(Saved, TEXT("roundtrip"), Path)))
        return false;
    FTsdfSnapshot Loaded;
    const bool bLoaded = Persistence->Load(TEXT("roundtrip"), Loaded);
    IFileManager::Get().DeleteDirectory(*Persistence->GetDirectory(), false, true);
    if (!TestTrue(TEXT("loads"), bLoaded))
        return false;

    TestEqual(TEXT("chunk voxels"), Loaded.Config.ChunkVoxels, Config.ChunkVoxels);
    TestEqual(TEXT("voxel metres"), Loaded.Config.VoxelMetres, Config.VoxelMetres);
    TestEqual(TEXT("truncation"), Loaded.Config.TruncationMetres, Config.TruncationMetres);
    TestEqual(TEXT("chunk count"), Loaded.Chunks.Num(), Saved.Chunks.Num());
    int32 Coloured = 0;
    for (int32 C = 0; C < FMath::Min(Saved.Chunks.Num(), Loaded.Chunks.Num()); ++C) {
        const FTsdfChunkVoxels& A = Saved.Chunks[C];
        const FTsdfChunkVoxels& B = Loaded.Chunks[C];
        TestTrue(*FString::Printf(TEXT("chunk %s identical"), *A.Key.ToString()),
            A.Key == B.Key && A.Sdf == B.Sdf && A.Weight == B.Weight && A.Rgbw == B.Rgbw);
        Coloured += A.Rgbw.Num() > 0;
    }
    TestTrue(TEXT("colour was saved"), Coloured > 0);

    FTsdfReconstruction Restored(Loaded.Config);
    FString Error;
    if (!TestTrue(TEXT("imports"), Restored.Import(Loaded, Error)))
        return false;
    const TMap<FIntVector, FTsdfChunkMesh> After = MeshEverything(Restored);
    TestEqual(TEXT("same chunks meshed"), After.Num(), Before.Num());
    bool bAnyRed = false;
    for (const TPair<FIntVector, FTsdfChunkMesh>& Pair : Before) {
        const FTsdfChunkMesh* Other = After.Find(Pair.Key);
        const FTsdfChunkMesh& M = Pair.Value;
        TestTrue(*FString::Printf(TEXT("chunk %s meshes into the same triangles"), *Pair.Key.ToString()),
            Other && M.Positions == Other->Positions && M.Normals == Other->Normals && M.Indices == Other->Indices
            && M.Colors == Other->Colors);
        for (const FColor& Colour : M.Colors)
            bAnyRed |= Colour.A > 0 && Colour.R > Colour.G + 40;
    }
    TestTrue(TEXT("the red band made it into the vertex colours"), bAnyRed);
    return true;
}

#endif
