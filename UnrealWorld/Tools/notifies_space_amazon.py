"""Fearing's katana swaps as notifies on her Grruzam clips, by script: AttachToSocket on every draw and sheathe.

    UnrealEditor-Cmd.exe D:/UnrealWorld/UnrealWorld/UnrealWorld.uproject -run=pythonscript
        -script="D:/UnrealWorld/UnrealWorld/Tools/notifies_space_amazon.py"
    Output Log, box on Cmd:  py D:/UnrealWorld/UnrealWorld/Tools/notifies_space_amazon.py

Run it after clipes_space_amazon.py. Its input is D:/UnrealWorld/Art/space_amazon/grruzam_lote/unreal/katana_notifies.json,
from gurps tools/blender/lote_grruzam.py --quem fearing notificacoes. For each clip it holds `sacar` (the first frame the
katana is in her hand, Unreal frame = Blender frame - 1) and `guardar` (the frame after the last one in her hand). The
draw becomes UAnimNotify_AttachToSocket with socket katana_mao, the sheathe the same with katana_bainha, both on the
component tagged Katana. The C++ class is Source/UnrealWorld/AnimNotify_AttachToSocket.*.

The script owns every AttachToSocket notify on these clips. It removes the ones there, hand-placed or from an earlier run,
and adds the json's on a track named Katana, so a second run changes nothing. It also does this for the clips
import_space_amazon.py put flat in animclips/ under the same name (katana_intro and katana_embainhar, whose
notifies were placed by hand), if their frame count matches.

A clip that starts or ends with the katana in her hand gets no notify for that. That is the state machine's
business. The json's comeca_na_mao / termina_na_mao say which ones they are, and the log counts them.
"""
import json
import os

import unreal

ART = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "Art", "space_amazon"))
JSON = os.path.join(ART, "grruzam_lote", "unreal", "katana_notifies.json")
ANIM_DIR = "/Game/Chars/SpaceAmazon/animclips"
TRACK = "Katana"
TAG = "Katana"
SOCKET = {"KatanaParaMao": "katana_mao", "KatanaParaBainha": "katana_bainha"}

lib = unreal.AnimationLibrary
assets = unreal.EditorAssetLibrary


def attach_events(seq):
    return [e for e in lib.get_animation_notify_events(seq) if isinstance(e.notify, unreal.AnimNotify_AttachToSocket)]


def clear(seq):
    """Removes every AttachToSocket notify. The library removes by event name only, so each name must belong to
    AttachToSocket notifies alone, or some other notify would go with it."""
    events = lib.get_animation_notify_events(seq)
    names = {str(e.notify_name) for e in events if isinstance(e.notify, unreal.AnimNotify_AttachToSocket)}
    for n in names:
        other = [e for e in events if str(e.notify_name) == n and not isinstance(e.notify, unreal.AnimNotify_AttachToSocket)]
        if other:
            raise RuntimeError("%s: notify name %r is shared with %d other notifies" % (seq.get_path_name(), n, len(other)))
        lib.remove_animation_notify_events_by_name(seq, n)
    left = attach_events(seq)
    if left:
        raise RuntimeError("%s: %d AttachToSocket notifies would not go" % (seq.get_path_name(), len(left)))
    return len(names)


def place(seq, clip):
    clear(seq)
    if clip["notifies"] and not lib.is_valid_anim_notify_track_name(seq, TRACK):
        lib.add_animation_notify_track(seq, TRACK)
    for ev in clip["notifies"]:
        n = lib.add_animation_notify_event(seq, TRACK, ev["s"], unreal.AnimNotify_AttachToSocket)
        if n is None:
            raise RuntimeError("%s: could not add a notify at %.4f s (length %.4f s)" % (seq.get_path_name(), ev["s"], seq.get_play_length()))
        n.set_editor_property("component_tag", TAG)
        n.set_editor_property("socket", SOCKET[ev["notify"]])
    # read back: one AttachToSocket per json event, at its time, on its socket
    got = sorted((round(lib.get_anim_notify_event_trigger_time(e), 3), str(e.notify.get_editor_property("socket")))
                 for e in attach_events(seq))
    want = sorted((round(ev["s"], 3), SOCKET[ev["notify"]]) for ev in clip["notifies"])
    if len(got) != len(want) or any(abs(a[0] - b[0]) > 0.002 or a[1] != b[1] for a, b in zip(got, want)):
        raise RuntimeError("%s: notifies read back as %s, expected %s" % (seq.get_path_name(), got, want))
    assets.save_loaded_asset(seq)


def main():
    with open(JSON, encoding="utf-8") as fh:
        clips = json.load(fh)["clips"]
    done, flat, missing, mismatch = 0, [], 0, []
    swaps = 0
    for c in clips:
        stem = os.path.splitext(c["fbx"])[0]
        paths = ["%s/%s/%s" % (ANIM_DIR, c["pasta"], stem)]
        if assets.does_asset_exist("%s/%s" % (ANIM_DIR, stem)):
            paths.append("%s/%s" % (ANIM_DIR, stem))
        for i, p in enumerate(paths):
            if not assets.does_asset_exist(p):
                missing += 1          # folder not imported yet
                continue
            seq = assets.load_asset(p)
            keys = seq.get_editor_property("number_of_sampled_keys")
            if c.get("frames") and keys != c["frames"]:
                mismatch.append("%s: %d keys, the json says %d frames" % (p, keys, c["frames"]))
                continue
            place(seq, c)
            if i == 0:
                done += 1
                swaps += len(c["notifies"])
            else:
                flat.append(p)
    starts = sum(1 for c in clips if c["comeca_na_mao"])
    ends = sum(1 for c in clips if c["termina_na_mao"])
    unreal.log("notifies_space_amazon: %d clips set (%d swaps), %d in the json not imported; flat copies set: %s"
               % (done, swaps, missing, ", ".join(flat) or "none"))
    unreal.log("notifies_space_amazon: of all %d clips in the json, %d start and %d end with the katana in her hand"
               % (len(clips), starts, ends))
    if mismatch:
        raise RuntimeError("notifies_space_amazon: clips differ from the batch:\n  " + "\n  ".join(mismatch))


main()
