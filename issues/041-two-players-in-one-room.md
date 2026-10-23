# 041 — Two players can't share a room: no session, no shared AR space, no TSDF sync

**Area:** net + ar + recon · **Status:** known (not scheduled; a later milestone) · **Blocked by:** 037

## Context

*Filed 2026-10-24.*

The hope is multiplayer with **two people in the same room**, each controlling a character (user,
2026-10-24). GAS (037) was chosen with that in mind: attributes, tags, abilities and cues already
replicate. Three problems are left, and GAS solves none of them:

1. **Transport.** Unreal's replication runs over its IP NetDriver. Two phones on the **same Wi-Fi**
   is plain IP, and a listen server on one phone works. **No router** means Wi-Fi Direct or Nearby
   Connections, which give a byte channel and not an IP network that the NetDriver can use. That
   would take a custom NetDriver. This was the one objection in ToySoldiers' rejection of GAS
   (`D:\ToySoldiers\docs\GDD.md`) that applies here too. Decide whether "same Wi-Fi" is acceptable
   before designing anything.
2. **A shared space.** Each phone's ARCore session has its own tracking space. For both players to
   see a character on the same spot of the real floor, the two spaces need a common anchor. The
   candidates are Cloud Anchors, or one phone's reconstruction registered into the other's by ICP
   (036 is the same problem across time instead of across devices).
3. **The TSDF itself** ("another can of worms", user, 2026-10-24). Who reconstructs:
   - one phone, with chunks sent to the other;
   - both, with fused or merged fields;
   - or the host's field only.

   What crosses the network: chunk voxels (the persistence format already serialises them), or
   meshes. The navmesh (012) and collision (010) must be identical on both machines, or the server
   corrects every step the client takes.

## The tempting wrong fixes

- **Replicating the chunk actors with Unreal's actor replication.** Thousands of voxels per chunk
  overwhelm property replication. Chunks are bulk data, to be sent as compressed snapshots
  (`UReconstructionPersistence`'s format) over a reliable channel or an RPC stream, rate-limited.
- **Both phones reconstructing on their own and hoping they agree.** They won't, as 011 measures
  inside a single phone.

## Done when

This card is a record. It gets split into real cards when the multiplayer milestone is planned.

## Files

```
issues/036 (relocalization), 037 (GAS), 010, 012 (what must agree on both machines)
UnrealWorld/Source/UnrealWorld/ReconstructionPersistence.h   the snapshot format, a candidate wire format
D:\ToySoldiers\docs\GDD.md   the transport objection
```
