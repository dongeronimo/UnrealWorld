#include "SocketTools.h"

#include "Engine/SkeletalMesh.h"
#include "Engine/SkeletalMeshSocket.h"

bool USocketTools::SetMeshSocket(USkeletalMesh* Mesh, FName SocketName, FName BoneName, FVector RelativeLocation,
	FRotator RelativeRotation)
{
#if WITH_EDITOR
	if (!Mesh || SocketName.IsNone() || Mesh->GetRefSkeleton().FindBoneIndex(BoneName) == INDEX_NONE)
	{
		return false;
	}
	// Mesh-only list, not FindSocket: FindSocket also answers with the skeleton's sockets, and editing one of those
	// would change every mesh on the skeleton.
	TArray<TObjectPtr<USkeletalMeshSocket>>& Sockets = Mesh->GetMeshOnlySocketList();
	USkeletalMeshSocket* Socket = nullptr;
	for (USkeletalMeshSocket* S : Sockets)
	{
		if (S && S->SocketName == SocketName)
		{
			Socket = S;
			break;
		}
	}
	Mesh->Modify();
	if (!Socket)
	{
		Socket = NewObject<USkeletalMeshSocket>(Mesh);
		Socket->SocketName = SocketName;
		Sockets.Add(Socket);
	}
	Socket->Modify();
	Socket->BoneName = BoneName;
	Socket->RelativeLocation = RelativeLocation;
	Socket->RelativeRotation = RelativeRotation;
	Socket->RelativeScale = FVector::OneVector;
	Mesh->RebuildSocketMap();
	Mesh->MarkPackageDirty();
	return true;
#else
	return false;
#endif
}
