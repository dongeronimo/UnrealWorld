"""The drow's katana swaps as AttachToSocket notifies on her clips, by script. notifies_space_amazon.py for her
flat pilot clips (drow handoff, step 5); the Grruzam batch (step 6) will bring her own katana_notifies.json.

    UnrealEditor-Cmd.exe D:/UnrealWorld/UnrealWorld/UnrealWorld.uproject -run=pythonscript -script="D:/UnrealWorld/UnrealWorld/Tools/notifies_drow.py"
    Output Log, box on Cmd:  py D:/UnrealWorld/UnrealWorld/Tools/notifies_drow.py [JSON]

Input: D:/drow/unreal/Drow_katana_notifies.json, from gurps tools/blender/exportar_unreal.py (modular), read off the
katana_na_mao key of each action: frame_ue is the first frame in her hand (to katana_mao) or the first frame after
it (to katana_bainha), counted from the clip's first frame. A clip's `pasta` is its subfolder of animclips ('' =
flat). The notify is UAnimNotify_AttachToSocket on the component tagged Katana (ADrow, as ASpaceAmazon).

The script owns every AttachToSocket notify on these clips: it removes the ones there and adds the json's on a track
named Katana, so a second run changes nothing.
"""
import json
import sys

import unreal

JSON = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith(".json") else "D:/drow/unreal/Drow_katana_notifies.json"
ANIM_DIR = "/Game/Chars/Drow/animclips"
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
    if attach_events(seq):
        raise RuntimeError("%s: AttachToSocket notifies would not go" % seq.get_path_name())


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
    got = sorted((round(lib.get_anim_notify_event_trigger_time(e), 3), str(e.notify.get_editor_property("socket")))
                 for e in attach_events(seq))
    want = sorted((round(ev["s"], 3), SOCKET[ev["notify"]]) for ev in clip["notifies"])
    if len(got) != len(want) or any(abs(a[0] - b[0]) > 0.002 or a[1] != b[1] for a, b in zip(got, want)):
        raise RuntimeError("%s: notifies read back as %s, expected %s" % (seq.get_path_name(), got, want))
    assets.save_loaded_asset(seq)


def main():
    with open(JSON, encoding="utf-8") as fh:
        clips = json.load(fh)["clips"]
    done, swaps, missing, mismatch = 0, 0, [], []
    for c in clips:
        stem = c["fbx"].rsplit(".", 1)[0]
        p = "/".join(x for x in (ANIM_DIR, c["pasta"], stem) if x)
        if not assets.does_asset_exist(p):
            missing.append(p)
            continue
        seq = assets.load_asset(p)
        keys = seq.get_editor_property("number_of_sampled_keys")
        if c.get("frames") and keys != c["frames"]:
            mismatch.append("%s: %d keys, the json says %d frames" % (p, keys, c["frames"]))
            continue
        place(seq, c)
        done += 1
        swaps += len(c["notifies"])
        for ev in c["notifies"]:
            unreal.log("notifies_drow: %s frame %d (%.3f s) -> %s" % (stem, ev["frame_ue"], ev["s"], SOCKET[ev["notify"]]))
    unreal.log("notifies_drow: %d clips set (%d swaps); not imported: %s" % (done, swaps, ", ".join(missing) or "none"))
    if mismatch:
        raise RuntimeError("notifies_drow: clips differ from the export:\n  " + "\n  ".join(mismatch))


main()
