#include "ModularChecks.h"

#include "Animation/AnimInstance.h"
#include "Animation/AnimSequence.h"
#include "Animation/MorphTarget.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "PreviewScene.h"

namespace
{
	float MorphWeight(const USkeletalMeshComponent* C, FName Name)
	{
		const UMorphTarget* M = C->GetSkeletalMeshAsset() ? C->GetSkeletalMeshAsset()->FindMorphTarget(Name) : nullptr;
		if (!M)
		{
			return -1.f;
		}
		const int32* Index = C->ActiveMorphTargets.Find(M);
		return Index && C->MorphTargetWeights.IsValidIndex(*Index) ? C->MorphTargetWeights[*Index] : 0.f;
	}
}

FString UModularChecks::FollowerMorphReport(USkeletalMesh* Leader, USkeletalMesh* Follower, UAnimSequence* Anim,
	float Time, bool bPostProcess, const TArray<FName>& Curves)
{
#if WITH_EDITOR
	if (!Leader || !Follower || !Anim)
	{
		return TEXT("missing leader, follower or clip");
	}
	FPreviewScene Scene(FPreviewScene::ConstructionValues().SetCreatePhysicsScene(false));

	USkeletalMeshComponent* L = NewObject<USkeletalMeshComponent>(GetTransientPackage());
	L->SetSkeletalMeshAsset(Leader);
	L->SetDisablePostProcessBlueprint(!bPostProcess);
	L->SetAnimationMode(EAnimationMode::AnimationSingleNode, false);
	// what the details panel sets: Anim to Play, Initial Position, Playing off
	L->AnimationData.AnimToPlay = Anim;
	L->AnimationData.SavedPosition = Time;
	L->AnimationData.bSavedPlaying = false;
	Scene.AddComponent(L, FTransform::Identity);

	USkeletalMeshComponent* F = NewObject<USkeletalMeshComponent>(GetTransientPackage());
	F->SetSkeletalMeshAsset(Follower);
	Scene.AddComponent(F, FTransform::Identity);
	F->SetLeaderPoseComponent(L);

	// no tick function: the evaluation runs here, on this thread, and finalizing the leader updates its followers
	for (int32 i = 0; i < 3; ++i)
	{
		L->TickAnimation(1.f / 30.f, false);
		L->RefreshBoneTransforms(nullptr);
		F->UpdateFollowerComponent();
	}

	FString Out = FString::Printf(TEXT("%s + %s, %s at %.2f s, post process %s (instance %s)"),
		*Leader->GetName(), *Follower->GetName(), *Anim->GetName(), Time, bPostProcess ? TEXT("on") : TEXT("off"),
		L->GetPostProcessInstance() ? *L->GetPostProcessInstance()->GetClass()->GetName() : TEXT("none"));
	const UAnimInstance* Inst = L->GetAnimInstance();
	for (const FName& Name : Curves)
	{
		Out += FString::Printf(TEXT("\n  %s: leader curve %.3f, leader morph %.3f, follower morph %.3f"), *Name.ToString(),
			Inst ? Inst->GetCurveValue(Name) : -1.f, MorphWeight(L, Name), MorphWeight(F, Name));
	}
	Scene.RemoveComponent(F);
	Scene.RemoveComponent(L);
	return Out;
#else
	return TEXT("editor only");
#endif
}
