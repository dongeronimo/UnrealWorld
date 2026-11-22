"""The drow's Control Rig in one command: regenerate CR_Drow from the recipes, then the parity test on the three clips
that move the most. fearing_control_rig.py with her paths (drow handoff, step 5).

    UnrealEditor-Cmd.exe D:/UnrealWorld/UnrealWorld/UnrealWorld.uproject -run=pythonscript -script="D:/UnrealWorld/UnrealWorld/Tools/drow_control_rig.py"
    Output Log, box on Cmd:  py D:/UnrealWorld/UnrealWorld/Tools/drow_control_rig.py [paridade]

"paridade" skips the regeneration. The rig is built on the leader (Drow); the pieces carry the same CORR_* morph
targets, and a follower in Leader Pose reads the leader's curves by name (SkeletalMeshComponent.cpp,
UpdateFollowerComponent), so this one rig drives every piece.
"""
import runpy
import sys

import unreal

TOOLS = "D:/UnrealWorld/UnrealWorld/Tools/"
ART = "D:/drow/unreal/"
RECEITAS = ART + "Drow_receitas.json"
CURVAS = ART + "Drow_curvas_ref.json"
MESH = "/Game/Chars/Drow/Drow"
CR = "/Game/Chars/Drow/CR_Drow"
CLIPS = ["aerobic_dance_315220", "katana_intro", "katana_embainhar"]


def run(script, *args):
    # both scripts read sys.argv at module level
    sys.argv = [TOOLS + script] + list(args)
    runpy.run_path(TOOLS + script, run_name="__main__")


so_paridade = "paridade" in sys.argv[1:]
if not so_paridade:
    run("gerar_control_rig.py", RECEITAS, MESH, CR)

falhas = []
for clip in CLIPS:
    unreal.log("drow_control_rig: parity on " + clip)
    try:
        run("paridade_control_rig.py", RECEITAS, "/Game/Chars/Drow/animclips/Drow_" + clip, CR, "0.05", CURVAS)
    except Exception as e:
        unreal.log_error("drow_control_rig: %s FAILED: %s" % (clip, e))
        falhas.append(clip)
if falhas:
    raise RuntimeError("drow_control_rig: parity FAILED on %s" % falhas)
unreal.log("drow_control_rig: regenerated=%s, parity PASS on %s" % (not so_paridade, ", ".join(CLIPS)))
