"""Do the drow's pieces get the correctives? Headless, by UModularChecks::FollowerMorphReport (Source/UnrealWorld):
the body posed at a time of a clip, post process on and off, a piece in Leader Pose beside it, and for each curve the
body's value and both morph weights (drow handoff, step 5; Drow_Unreal.md section 3, item 1).

    UnrealEditor-Cmd.exe D:/UnrealWorld/UnrealWorld/UnrealWorld.uproject -run=pythonscript -script="D:/UnrealWorld/UnrealWorld/Tools/check_drow_correctives.py"

The times and keys are where the correctives move each piece most in the aerobic clip, measured in Blender: the pants
91 mm at 8.53 s (left hip), the jacket at least 78 mm through 8.67-9.13 s (right armpit; its 109 mm peak, at 10.07 s,
lasts one frame). Fails if, with the post process on, a curve
is not on the body or the piece's morph weight differs from it, or if, with it off, a weight is not 0.
"""
import unreal

ROOT = "/Game/Chars/Drow"
CLIP = ROOT + "/animclips/Drow_aerobic_dance_315220"
CASES = [
    ("Drow_Cargo_Pants", 8.53, ["CORR_L_Quadril_f090_a00", "CORR_L_Quadril_f125_a00"]),
    ("Drow_Jacket", 8.90, ["CORR_R_Axila_b090_f045", "CORR_R_Axila_b090_f000"]),
]
assets = unreal.EditorAssetLibrary


def main():
    body = assets.load_asset(ROOT + "/Drow")
    clip = assets.load_asset(CLIP)
    bad = []
    for piece, t, curves in CASES:
        mesh = assets.load_asset(ROOT + "/Pieces/" + piece)
        for on in (True, False):
            rep = unreal.ModularChecks.follower_morph_report(body, mesh, clip, t, on, curves)
            for line in rep.splitlines():
                unreal.log("check_drow_correctives: " + line)
            for line in rep.splitlines()[1:]:
                name, rest = line.strip().split(": ", 1)
                vals = [float(x.split()[-1]) for x in rest.split(", ")]
                curve, lead, foll = vals
                if on and (curve < 0.05 or abs(foll - curve) > 0.01 or abs(lead - curve) > 0.01):
                    bad.append("%s %s on: curve %.3f, body %.3f, piece %.3f" % (piece, name, curve, lead, foll))
                if not on and (abs(lead) > 0.01 or abs(foll) > 0.01):
                    bad.append("%s %s off: body %.3f, piece %.3f" % (piece, name, lead, foll))
    if bad:
        raise RuntimeError("check_drow_correctives: FAILED\n  " + "\n  ".join(bad))
    unreal.log("check_drow_correctives: PASS")


main()
