"""Fearing's Control Rig in one short editor command: regenerate CR_SpaceAmazon, then run the parity test on
the three clips that move the most.

    Output Log, box on Cmd:  py D:/UnrealWorld/UnrealWorld/Tools/fearing_control_rig.py

Exists because the full gerar_control_rig.py / paridade_control_rig.py lines are long enough to wrap when
copied, and a wrapped line reaches the Output Log as two commands. The arguments are the ones in
SpaceAmazon_Unreal.md section 2; this only fills them in. Add "paridade" to skip the regeneration.
"""
import runpy
import sys

import unreal

TOOLS = "D:/UnrealWorld/UnrealWorld/Tools/"
ART = "D:/UnrealWorld/Art/space_amazon/unreal/"
RECEITAS = ART + "SpaceAmazon_receitas.json"
CURVAS = ART + "SpaceAmazon_curvas_ref.json"
MESH = "/Game/Chars/SpaceAmazon/SpaceAmazon"
CR = "/Game/Chars/SpaceAmazon/CR_SpaceAmazon"
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
    unreal.log("fearing_control_rig: parity on " + clip)
    try:
        run("paridade_control_rig.py", RECEITAS, "/Game/Chars/SpaceAmazon/animclips/SpaceAmazon_" + clip, CR, "0.05", CURVAS)
    except Exception as e:
        unreal.log_error("fearing_control_rig: %s FAILED: %s" % (clip, e))
        falhas.append(clip)
if falhas:
    raise RuntimeError("fearing_control_rig: parity FAILED on %s" % falhas)
unreal.log("fearing_control_rig: regenerated=%s, parity PASS on %s" % (not so_paridade, ", ".join(CLIPS)))
