#include "ReconstructionPersistence.h"
#include "TsdfReconstruction.h"
#include "HAL/FileManager.h"
#include "Misc/Paths.h"
#include "Serialization/Archive.h"

DEFINE_LOG_CATEGORY_STATIC(LogReconPersistence, Log, All);

namespace {
    constexpr uint32 Magic = 'T' | ('S' << 8) | ('D' << 16) | ('F' << 24); // "TSDF" on disk
    constexpr uint32 Version = 1;
    const TCHAR* const Extension = TEXT(".tsdf");

    // Both directions: FArchive's << reads when loading and writes when saving.
    // A field added to FTsdfConfig goes here AND bumps Version.
    void SerializeConfig(FArchive& Ar, FTsdfConfig& C) {
        Ar << C.ChunkVoxels << C.VoxelMetres << C.TruncationMetres << C.MaxWeight;
        Ar << C.bCarving << C.CarvingDistance << C.CarvingDecay << C.CarvingMinWeight << C.CarvingRate;
        Ar << C.ConfidenceThreshold << C.ConfidenceWeightFloor << C.ConfidenceWeightExponent;
        Ar << C.NearPlane << C.FarPlane;
        Ar << C.bColor << C.ColorMaxWeight << C.ColorFullConfidenceWeight;
    }

    // A name, not a path: whatever comes in over adb ends up under Folder.
    bool IsPlainName(const FString& Name) {
        if (Name.IsEmpty())
            return false;
        FText Reason;
        return FPaths::ValidatePath(Name, &Reason) && !Name.Contains(TEXT("/")) && !Name.Contains(TEXT("\\"))
            && !Name.Contains(TEXT("..")) && !Name.Contains(TEXT(":"));
    }
}

FString UReconstructionPersistence::GetDirectory() const {
    return FPaths::Combine(FPaths::ProjectSavedDir(), Folder);
}

FString UReconstructionPersistence::PathFor(const FString& Name) const {
    return FPaths::Combine(GetDirectory(), Name + Extension);
}

bool UReconstructionPersistence::Save(const FTsdfSnapshot& Snapshot, const FString& Name, FString& OutPath) const {
    if (!IsPlainName(Name)) {
        UE_LOG(LogReconPersistence, Error, TEXT("PERSISTENCE '%s' is not a usable world name"), *Name);
        return false;
    }
    const FString Final = PathFor(Name);
    // Written beside the real name and moved over it at the end, so a file
    // with the real name is always a complete one: recon.py waits for that
    // name to appear and pulls it straight away.
    const FString Partial = Final + TEXT(".part");
    OutPath = IFileManager::Get().ConvertToAbsolutePathForExternalAppForWrite(*Final);
    // Announced before the attempt: when it fails, which path was tried is
    // most of the diagnosis.
    UE_LOG(LogReconPersistence, Log, TEXT("PERSISTENCE saving %d chunks to %s"), Snapshot.Chunks.Num(), *OutPath);

    IFileManager::Get().MakeDirectory(*GetDirectory(), /*Tree=*/true);
    TUniquePtr<FArchive> Ar(IFileManager::Get().CreateFileWriter(*Partial));
    if (!Ar) {
        UE_LOG(LogReconPersistence, Error, TEXT("PERSISTENCE cannot open %s for writing"), *Partial);
        return false;
    }
    uint32 FileMagic = Magic, FileVersion = Version;
    FTsdfConfig Config = Snapshot.Config;
    int32 ChunkCount = Snapshot.Chunks.Num();
    *Ar << FileMagic << FileVersion;
    SerializeConfig(*Ar, Config);
    *Ar << ChunkCount;
    const int32 N = Config.ChunkVoxels * Config.ChunkVoxels * Config.ChunkVoxels;
    for (const FTsdfChunkVoxels& Chunk : Snapshot.Chunks) {
        // The header promised N of each; a short array would shift every chunk after it.
        if (Chunk.Sdf.Num() != N || Chunk.Weight.Num() != N || (Chunk.Rgbw.Num() != 0 && Chunk.Rgbw.Num() != N * 4)) {
            UE_LOG(LogReconPersistence, Error, TEXT("PERSISTENCE chunk %s doesn't hold %d voxels, not saving"), *Chunk.Key.ToString(), N);
            Ar.Reset();
            IFileManager::Get().Delete(*Partial);
            return false;
        }
        FIntVector Key = Chunk.Key;
        uint8 HasColour = Chunk.Rgbw.Num() > 0 ? 1 : 0;
        *Ar << Key.X << Key.Y << Key.Z;
        Ar->Serialize(const_cast<float*>(Chunk.Sdf.GetData()), N * sizeof(float));
        Ar->Serialize(const_cast<float*>(Chunk.Weight.GetData()), N * sizeof(float));
        *Ar << HasColour;
        if (HasColour)
            Ar->Serialize(const_cast<uint8*>(Chunk.Rgbw.GetData()), N * 4);
    }
    const bool bWritten = Ar->Close() && !Ar->IsError();
    Ar.Reset();
    if (!bWritten || !IFileManager::Get().Move(*Final, *Partial, /*Replace=*/true)) {
        UE_LOG(LogReconPersistence, Error, TEXT("PERSISTENCE failed writing %s"), *OutPath);
        IFileManager::Get().Delete(*Partial);
        return false;
    }
    UE_LOG(LogReconPersistence, Log, TEXT("PERSISTENCE saved %s (%.1f MB)"), *OutPath,
        IFileManager::Get().FileSize(*Final) / (1024.0 * 1024.0));
    return true;
}

bool UReconstructionPersistence::Load(const FString& Name, FTsdfSnapshot& Out) const {
    if (!IsPlainName(Name)) {
        UE_LOG(LogReconPersistence, Error, TEXT("PERSISTENCE '%s' is not a usable world name"), *Name);
        return false;
    }
    const FString Path = PathFor(Name);
    TUniquePtr<FArchive> Ar(IFileManager::Get().CreateFileReader(*Path));
    if (!Ar) {
        // Saved/ is gitignored: a fresh clone has no worlds until one is pulled.
        UE_LOG(LogReconPersistence, Error, TEXT("PERSISTENCE no world at %s. Capture one with: python Tools/recon.py save %s"),
            *FPaths::ConvertRelativePathToFull(Path), *Name);
        return false;
    }
    uint32 FileMagic = 0, FileVersion = 0;
    *Ar << FileMagic << FileVersion;
    if (FileMagic != Magic || FileVersion != Version) {
        UE_LOG(LogReconPersistence, Error, TEXT("PERSISTENCE %s is not a version %u world file (magic %08x, version %u)"),
            *Path, Version, FileMagic, FileVersion);
        return false;
    }
    SerializeConfig(*Ar, Out.Config);
    int32 ChunkCount = 0;
    *Ar << ChunkCount;
    const int32 Side = Out.Config.ChunkVoxels;
    if (Ar->IsError() || Side < 1 || Side > 64 || ChunkCount < 0) {
        UE_LOG(LogReconPersistence, Error, TEXT("PERSISTENCE %s has a broken header"), *Path);
        return false;
    }
    const int32 N = Side * Side * Side;
    // Checked against the file's size before allocating anything: a broken
    // count would otherwise ask for gigabytes.
    const int64 MinChunkBytes = 3 * sizeof(int32) + 2 * int64(N) * sizeof(float) + 1;
    if (int64(ChunkCount) * MinChunkBytes > Ar->TotalSize() - Ar->Tell()) {
        UE_LOG(LogReconPersistence, Error, TEXT("PERSISTENCE %s claims %d chunks but is too short to hold them"), *Path, ChunkCount);
        return false;
    }
    Out.Chunks.Reset(ChunkCount);
    int32 Coloured = 0;
    for (int32 C = 0; C < ChunkCount; ++C) {
        FTsdfChunkVoxels& Chunk = Out.Chunks.AddDefaulted_GetRef();
        uint8 HasColour = 0;
        *Ar << Chunk.Key.X << Chunk.Key.Y << Chunk.Key.Z;
        Chunk.Sdf.SetNumUninitialized(N);
        Chunk.Weight.SetNumUninitialized(N);
        Ar->Serialize(Chunk.Sdf.GetData(), N * sizeof(float));
        Ar->Serialize(Chunk.Weight.GetData(), N * sizeof(float));
        *Ar << HasColour;
        if (HasColour) {
            Chunk.Rgbw.SetNumUninitialized(N * 4);
            Ar->Serialize(Chunk.Rgbw.GetData(), N * 4);
            ++Coloured;
        }
        if (Ar->IsError()) {
            UE_LOG(LogReconPersistence, Error, TEXT("PERSISTENCE %s ended in the middle of chunk %d of %d"), *Path, C, ChunkCount);
            Out.Chunks.Reset();
            return false;
        }
    }
    UE_LOG(LogReconPersistence, Log, TEXT("PERSISTENCE loaded %s: %d chunks of %d^3 voxels at %.3f m, %d with colour"),
        *Path, ChunkCount, Side, Out.Config.VoxelMetres, Coloured);
    return true;
}

bool UReconstructionPersistence::LoadSelected(FTsdfSnapshot& Out) const {
    return !WorldToLoad.IsEmpty() && Load(WorldToLoad, Out);
}

TArray<FString> UReconstructionPersistence::GetWorldNames() const {
    TArray<FString> Files;
    IFileManager::Get().FindFiles(Files, *FPaths::Combine(GetDirectory(), FString(TEXT("*")) + Extension), true, false);
    TArray<FString> Names;
    Names.Reserve(Files.Num() + 1);
    Names.Add(FString());
    for (const FString& File : Files)
        Names.Add(FPaths::GetBaseFilename(File));
    Names.Sort();
    return Names;
}
