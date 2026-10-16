"""Moves recorded reconstructions from the phone into this project.

    python Tools/recon.py save [name]   Recon.Save on the running app, wait, pull it
    python Tools/recon.py pull [name]   pull one world, or all of them, already saved
    python Tools/recon.py list          what's on the device and what's here

Worlds land in UnrealWorld/Saved/Recon/<name>.tsdf, which is where the fixture
game mode's Persistence looks, so they show up in its WorldToLoad dropdown.

`save` reaches the app through the console-command broadcast receiver Unreal
registers on Android, so the app has to be running with a reconstruction in
progress; nothing is rebuilt and nobody touches the screen. The file is written
under a temporary name and renamed when complete, so appearing means finished.
"""
import argparse
import datetime
import os
import subprocess
import sys
import time

PACKAGE = "dev.dongeronimo.unrealworld"
EXTENSION = ".tsdf"
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_DIR = os.path.join(PROJECT_DIR, "Saved", "Recon")


def adb(args, serial, check=True):
    cmd = ["adb"] + (["-s", serial] if serial else []) + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"{' '.join(cmd)} failed:\n{result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def device_worlds(serial, package):
    """name -> device path. Searched rather than assumed: where Unreal puts
    Saved/ under the app's external files dir has moved between engine versions."""
    root = f"/sdcard/Android/data/{package}/files"
    out = adb(["shell", f"find {root} -path '*/Saved/Recon/*{EXTENSION}' 2>/dev/null"], serial, check=False)
    worlds = {}
    for line in out.splitlines():
        line = line.strip()
        if line.endswith(EXTENSION):
            worlds[os.path.basename(line)[: -len(EXTENSION)]] = line
    return worlds


def pull(serial, name, device_path):
    os.makedirs(LOCAL_DIR, exist_ok=True)
    local = os.path.join(LOCAL_DIR, name + EXTENSION)
    adb(["pull", device_path, local], serial)
    print(f"{name}: {os.path.getsize(local) / (1024 * 1024):.1f} MB -> {local}")


def cmd_save(args):
    name = args.name or datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    if any(c in name for c in "/\\: '\""):
        sys.exit(f"'{name}' isn't a plain name")
    before = device_worlds(args.serial, args.package).get(name)
    if before:
        # It would be overwritten, and its presence can't signal completion.
        adb(["shell", f"rm '{before}'"], args.serial)
    adb(["shell", f"am broadcast -a android.intent.action.RUN -e cmd 'Recon.Save {name}'"], args.serial)
    print(f"Recon.Save {name} sent, waiting for the file...")
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        path = device_worlds(args.serial, args.package).get(name)
        if path:
            pull(args.serial, name, path)
            return
        time.sleep(0.5)
    sys.exit(f"no {name}{EXTENSION} after {args.timeout} s. Is the app running with a reconstruction? "
             f"adb logcat -s UE:* | findstr \"PERSISTENCE RECON\" says why.")


def cmd_pull(args):
    worlds = device_worlds(args.serial, args.package)
    if args.name:
        if args.name not in worlds:
            sys.exit(f"no {args.name} on the device. There is: {', '.join(sorted(worlds)) or 'nothing'}")
        worlds = {args.name: worlds[args.name]}
    if not worlds:
        sys.exit("no worlds on the device")
    for name, path in sorted(worlds.items()):
        pull(args.serial, name, path)


def cmd_list(args):
    worlds = device_worlds(args.serial, args.package)
    print("device:", ", ".join(sorted(worlds)) or "nothing")
    local = sorted(f[: -len(EXTENSION)] for f in os.listdir(LOCAL_DIR) if f.endswith(EXTENSION)) \
        if os.path.isdir(LOCAL_DIR) else []
    print(f"here ({LOCAL_DIR}):", ", ".join(local) or "nothing")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-s", "--serial", help="adb device serial, when more than one is connected")
    parser.add_argument("--package", default=PACKAGE)
    sub = parser.add_subparsers(dest="command", required=True)
    save = sub.add_parser("save", help="save the running reconstruction and pull it")
    save.add_argument("name", nargs="?", help="default: a timestamp")
    save.add_argument("--timeout", type=float, default=60, help="seconds to wait for the file")
    save.set_defaults(run=cmd_save)
    pull_cmd = sub.add_parser("pull", help="pull saved worlds")
    pull_cmd.add_argument("name", nargs="?", help="default: all of them")
    pull_cmd.set_defaults(run=cmd_pull)
    sub.add_parser("list", help="list worlds on the device and here").set_defaults(run=cmd_list)
    args = parser.parse_args()
    # Otherwise "no device" reads as "no worlds on the device".
    state = subprocess.run(["adb"] + (["-s", args.serial] if args.serial else []) + ["get-state"],
                           capture_output=True, text=True)
    if state.stdout.strip() != "device":
        sys.exit(f"no usable adb device: {state.stderr.strip() or state.stdout.strip()}")
    args.run(args)


if __name__ == "__main__":
    main()
