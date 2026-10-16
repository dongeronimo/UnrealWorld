Unreal World: how to reconstruct the real world in Unreal using TSDFs

The objective is to reconstruct the physical world on the virtual world in two devices, sharing and combining
the reconstruction, and getting them to see the same reconstructed world and characters walking around.

Steps:
I   - Getting arcore to run as i need.
II  - TSDFs with OpenChisel
III - Quantification and stabilization of the world
IV  - Characters and their navigation.
V   - Distributed reconstruction
VI  - Distributed characters 

Relevant files:
- arcore_in_unreal.md : getting what we need to do spatial reconstruction running is truly the Gom Jabbar.

Saving the reconstruction to the workstation:

With the app running on the phone and the room scanned, from `UnrealWorld/`:

```
python Tools/recon.py save <name>
```

It sends `Recon.Save <name>` to the app over adb, waits for the file and pulls it into
`UnrealWorld/Saved/Recon/<name>.tsdf`, where the fixture game mode's World To Load dropdown finds it.
Add `-s <serial>` (e.g. `-s 192.168.0.66:5555`) when adb sees more than one device. `list` and
`pull [name]` show and fetch worlds already saved on the phone.

Wireless debugging, with the phone on USB once: `adb tcpip 5555`, then `adb connect <phone ip>:5555`.
Lost on reboot.