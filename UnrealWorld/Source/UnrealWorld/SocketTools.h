#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "SocketTools.generated.h"

class USkeletalMesh;

/// <summary>
/// Sockets on skeletal mesh assets from editor Python (import_drow.py). Python cannot name a socket:
/// USkeletalMeshSocket::SocketName is VisibleAnywhere, so set_editor_property refuses it, and USkeletalMesh::AddSocket
/// names a nameless socket "Socket_N". Nor can it remove one. This creates or updates a mesh-only socket in place, so
/// an import script can own its sockets and a rerun changes nothing.
/// </summary>
UCLASS()
class UNREALWORLD_API USocketTools : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/// Creates the mesh-only socket SocketName on Mesh, or updates it if there is one. Editor only; false if the
	/// bone is not in the mesh or outside the editor. Does not save the asset.
	UFUNCTION(BlueprintCallable, Category = "Editor|Sockets")
	static bool SetMeshSocket(USkeletalMesh* Mesh, FName SocketName, FName BoneName, FVector RelativeLocation,
		FRotator RelativeRotation);
};
