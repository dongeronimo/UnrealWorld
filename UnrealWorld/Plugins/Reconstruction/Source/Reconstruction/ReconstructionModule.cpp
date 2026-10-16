// Unreal wants an implementation for every module listed in a .uplugin. This one
// has no runtime behaviour to start or stop yet.
#include "Modules/ModuleManager.h"

IMPLEMENT_MODULE(FDefaultModuleImpl, Reconstruction);
