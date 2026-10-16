// The reconstruction module, with OpenChisel (ToySoldiers' fork) vendored inside.
//
// The settings below are ToySoldiers' PutoranaRecon.Build.cs, minus what belonged
// to its facade (glm, putorana/, the android/log.h stub). The full reasoning for
// each one is there and in openchisel/OPENCHISEL-README.md; only the short version
// is kept here.

using UnrealBuildTool;
using System.IO;

public class Reconstruction : ModuleRules
{
	public Reconstruction(ReadOnlyTargetRules Target) : base(Target)
	{
		// OpenChisel lives INSIDE this module, not in a module of its own. Nothing in
		// it carries an export macro, so as a separate module its editor DLL would
		// export nothing and the Win64 link fails (ToySoldiers hit this: 17
		// unresolved chisel:: symbols; Android links fine because it is monolithic).
		// The facade that will wrap it goes in this module too.
		//
		// Private include path: nothing outside this module can include
		// <open_chisel/...>, so Eigen types never leak into game code.
		PrivateIncludePaths.Add(Path.Combine(ModuleDirectory, "openchisel", "include"));

		// Unreal ships Eigen 3.4.0, the version OpenChisel was built against.
		// Private for the same reason as the include path.
		PublicDependencyModuleNames.Add("Core");
		PrivateDependencyModuleNames.Add("Eigen");

		// Optimised even in Debug: unoptimised Eigen expression templates are slow
		// enough to hide real performance problems.
		OptimizeCode = CodeOptimization.Always;

		// Allows FMA fusion (Unreal defaults to -ffp-contract=off). The integrator
		// is almost all multiply-adds; determinism doesn't matter for a TSDF fed by
		// a noisy depth sensor. Scoped to this module only.
		FPSemantics = FPSemanticsMode.Imprecise;

		// NDEBUG is deliberately NOT set: Unreal already defines it globally, and
		// setting it here would make this module's Eigen differ from Chaos' etc. in
		// Debug builds (ODR violation).

		// Raycast.cpp throws std::out_of_range; -fno-exceptions makes that an error.
		bEnableExceptions = true;

		// Vendored C++ that has never seen an Unreal header.
		PCHUsage = PCHUsageMode.NoPCHs;
		bUseUnity = false;

		// Target is BuildSettingsVersion.V6, which promotes warnings to errors.
		// These are the ones OpenChisel trips.
		bWarningsAsErrors = false;
		CppCompileWarningSettings.RangeLoopConstructWarningLevel = WarningLevel.Off;
		CppCompileWarningSettings.ReturnTypeWarningLevel = WarningLevel.Off;
		CppCompileWarningSettings.ShadowVariableWarningLevel = WarningLevel.Off;
		CppCompileWarningSettings.UnsafeTypeCastWarningLevel = WarningLevel.Off;
		CppCompileWarningSettings.UndefinedIdentifierWarningLevel = WarningLevel.Off;
		CppCompileWarningSettings.DeprecatedCopyWarningLevel = WarningLevel.Off;
		CppCompileWarningSettings.DeprecatedCopyWithUserProvidedCopyWarningLevel = WarningLevel.Off;
		CppCompileWarningSettings.SwitchUnhandledEnumeratorWarningLevel = WarningLevel.Off;
		CppCompileWarningSettings.EnumConversionWarningLevel = WarningLevel.Off;
		CppCompileWarningSettings.OrderedCompareFunctionPointers = WarningLevel.Off;
		bDisableStaticAnalysis = true;
		IWYUSupport = IWYUSupport.None;
	}
}
