#include "ARPawn.h"
#include "Camera/CameraComponent.h"

AARPawn::AARPawn(){
    PrimaryActorTick.bCanEverTick = false;
    // A plain scene comp with no visuals, it's just a transform.
    Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
    RootComponent = Root;
    // The AR-Driven camera, attached to Root - phone pose is now
    // an offset from origin instead of overwritting the pawn's own
    // transform.
    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("AR Camera"));
    Camera->SetupAttachment(Root);
    //The reason this class exists, this is what makes the
    //camera be where the phone is
    Camera->bLockToHmd = true;
    //The AR session sets the view from the real sensor. 
    //The controller must not overwrite the sensor.
    Camera->bUsePawnControlRotation = false;
}


