# 002 — Milestone 1: two sessions in one app, an arena and the real room

**Area:** everything · **Status:** open · **Blocked by:** every card in the README's Next table

## Context

*Filed 2026-10-23.*

UnrealWorld is the redo of ToySoldiers. The reconstruction now runs on the phone, and a saved room
(`Content/ReconWorlds/room1.tsdf`) opens in PIE through the fixture (`Fixture.umap`,
`BP_FixtureGameMode`). The characters, Ratoman Brute and Sophia, exist as Blender work with
written plans (`Ratoman_Brute_Unreal.md`, `Sophia_Unreal.md`, `Sophia_Animation_Plan.md`). Ratoman
is imported and checked. Sophia isn't in Unreal yet.

The milestone ends with **one app holding two sessions that know nothing about each other**:

1. **The arena.** A simple greyboxed world. Sophia, played by the user, fights waves of Ratomen
   and reaches an extraction point. Nothing about it is AR. It proves the characters, the
   combat and the session loop.
2. **The real room.** The phone reconstructs the room, and a navmesh is generated on it that
   stays put. Something walks on it. It proves that the reconstruction can carry gameplay.

Joining the two (Sophia fighting in the real room) belongs to a later milestone. Keeping them apart
here is deliberate. Each session fails for its own reasons, and a failure in one must not hide
behind the other.

## What kind of game, and what that decides

**A third-person action game:** blades, guns, some parkour. It is hopefully multiplayer later,
with **two people in the same room**, each controlling a character (user, 2026-10-24). Multiplayer
is not in this milestone. But it decided one thing now: **every fight interaction goes through the
Gameplay Ability System** (037):
- health and damage are attributes and effects (030);
- each move is an ability (038, 039);
- states are tags;
- hit feedback is gameplay cues;
- anything that changes the game happens on authority.

The cheap check that keeps this honest is the occasional 2-player listen-server PIE run. Parkour
(040) and the multiplayer problems themselves (041: transport, a shared AR space, TSDF sync) are
filed in Known.

## Why the room session is the risky one

ToySoldiers died on its navmesh. The navmesh never converged to something stable and rarely
changed, because the mesh under it never stopped changing. The suspected causes (user, 2026-10-23)
are:

- an inadequate weighting function;
- the Galaxy S series' poor depth;
- carving competing with accumulation, which is a contradiction built into TSDF reconstruction:
  the field is asked both to forget (carving, so moving things and noise go away) and to
  remember (accumulation, so the surface settles).

Nobody measured which of these it was. So this milestone puts **measurement before navmesh**:

- recording and replaying raw frames (006);
- switchable weighting functions (007);
- a noise model for the sensor (008);
- depth filtering (009);
- a stability metric (011).

Only then the navmesh (012).

## Fronts

- **Reconstruction:** 003–012.
- **Ratoman:** 013–019.
- **Sophia:** 020–029.
- **Fight systems (GAS):** 037, 030, 038, 039.
- **Arena:** 031–033.
- **The room session:** 034.

## The tempting wrong fixes

- **Starting the navmesh before the field is stable.** It's what ToySoldiers did. A dynamic
  navmesh on a churning mesh rebuilds forever, and that looks like a navmesh problem when it's a
  reconstruction problem.
- **Putting Sophia in the real room to "test both at once".** A broken path then can't tell you
  whether it was the field, the navmesh, the AI or the character. That's the next milestone.
- **Polishing the arena.** It's greybox. The deliverable is the loop (spawn, fight, extract or
  die), not the look.

## Done when

- The app opens on a front door (033) offering two entries.
- **Arena:** Sophia, on the phone, fights at least three waves of Ratomen with katana and pistol,
  can die, and can reach the extraction point and win.
- **Room:** the phone scans a room. The navmesh on it stops changing once the scan stops: tile
  rebuilds fall to near zero within a stated time while the phone looks at a static room, a
  number set in 011. A Ratoman walks from one side of the room to the other on it, around the
  furniture.
- Both sessions run on the Galaxy device, not only in PIE.

## Files

```
issues/README.md                    the ledger
running_the_reconstruction.md       how the reconstruction works today
Ratoman_Brute_Unreal.md             Ratoman's plan
Sophia_Unreal.md, Sophia_Animation_Plan.md   Sophia's plans
klingensmith2015chisel.pdf          the Chisel paper: weighting, truncation, carving
```
