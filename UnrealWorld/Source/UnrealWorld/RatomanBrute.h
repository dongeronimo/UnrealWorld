// Fill out your copyright notice in the Description page of Project Settings.

#pragma once

#include "CoreMinimal.h"

#include "GameFramework/Character.h"
#include "RatomanBrute.generated.h"
/// <summary>
/// Ratoman Brute actor. He's the big bad rat dude.
/// </summary>
UCLASS()
class UNREALWORLD_API ARatomanBrute : public ACharacter
{
	GENERATED_BODY()
	
public:	
	// Sets default values for this actor's properties
	ARatomanBrute();

	// Angry facial expression control.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Face", meta = (ClampMin=0, ClampMax=1))
	float AngryWeight = 0.0f;

	// Evil Laugh facial expression control.
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Face", meta = (ClampMin = 0, ClampMax = 1))
	float EvilLaughWeight = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Face", meta = (ClampMin = 0, ClampMax = 1))
	float PainWeight = 0.0f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Face", meta = (ClampMin = 0, ClampMax = 1))
	float ScreamWeight = 0.0f;

protected:
	// Called when the game starts or when spawned
	virtual void BeginPlay() override;

public:	
	// Called every frame
	virtual void Tick(float DeltaTime) override;

};
