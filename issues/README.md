# Issues

One file per work item, named `NNN-short-slug.md`. Each one is picked up in its own conversation.

A card carries its own context. Assume whoever opens it hasn't seen the conversation that filed
it, and don't make them read the git history to find out what it's about. A card covers only what
it was filed for, and adjacent concerns become a new card. Cards state the tempting *wrong* fix
and why it's wrong, which is the most valuable part.

- **Next** is the queued work, grouped by front. Within a front, the order is the intended order.
- **Known** holds recorded gaps that are deliberately not scheduled. Filing there costs nothing.
  A card there is a record that something was noticed, not a promise to build it.
- When a card is done, move its row to **Done** with the date, and check the `Blocks:` lines of
  the other cards for staleness.

Project layout:

```
D:\UnrealWorld\
  running_the_reconstruction.md, arcore_in_unreal.md, adding_open_chisel.md   how the AR side was built
  Ratoman_Brute_Unreal.md, Sophia_Unreal.md, Sophia_Animation_Plan.md         character plans
  klingensmith2015chisel.pdf      the Chisel paper
  Art\                            Blender sources and exports
  blender_utils\                  project-local Blender scripts
  issues\                         this folder
  UnrealWorld\                    the Unreal project (UE 5.7)
    Source\UnrealWorld\           game module: AR session, reconstruction actors, game modes
    Plugins\Reconstruction\       FTsdfReconstruction + the vendored OpenChisel fork
    Plugins\RealtimeMeshComponent\
    Tools\recon.py                pulls saved worlds off the device
```

## Next

| # | Title | Area | Blocks |
|---|---|---|---|
| [002](002-milestone-1-two-sessions.md) | Milestone 1: two sessions in one app, an arena and the real room | everything | — |

### Reconstruction front (the room session)

Measurement comes before navmesh. That order is the lesson from ToySoldiers (002).

| # | Title | Area | Blocks |
|---|---|---|---|
| [003](003-chunks-ignore-the-fused-colour.md) | The chunks ignore the fused colour, on the fixture and on the phone | render | judging by eye |
| [004](004-the-room-follows-the-pawn.md) | The room follows the pawn instead of an ARCore anchor | ar + recon | 005, 010, 012 |
| [006](006-raw-frames-cannot-be-replayed.md) | Only the fused field is saved, so no function can be compared on the same data | recon + tools | 007, 008, 009, 011 |
| [011](011-the-surface-never-settles.md) | No metric for how much the mesh keeps changing | recon + tools | 012 |
| [007](007-one-weighting-function-hardcoded.md) | One weighting function is hardcoded: confidence curve and ray profile can't be switched | recon | 008, 011 |
| [008](008-no-noise-model-for-the-sensor.md) | No noise model for the Galaxy's depth: no dynamic truncation, no hit-probability weight | recon + tools | 011 |
| [009](009-bad-depth-is-fused.md) | Bad depth is fused: motion blur, grazing angles, flying pixels | recon | 011 |
| [010](010-the-chunks-have-no-collision.md) | The chunks have no collision | recon + physics | 012, 034 |
| [005](005-the-room-dies-with-the-activity.md) | The room dies when Android backgrounds or kills the app | ar + recon | long sessions |
| [012](012-no-navmesh-on-the-room.md) | No navmesh on the reconstructed room | recon + ai | 034 |
| [034](034-nothing-walks-the-room.md) | Nothing walks the real room | ar + ai | 002 |

### Ratoman front

| # | Title | Area | Blocks |
|---|---|---|---|
| [015](015-ratomans-twist-bones-are-not-driven.md) | Ratoman's twist bones are not driven: candy-wrapper wrists | anim | 016, 018 |
| [017](017-ratomans-physics-asset-is-the-default.md) | Ratoman's physics asset is the auto-generated one | anim + physics | 016, 030 |
| [016](016-ratomans-tail-and-ears-hang-rigid.md) | Ratoman's tail, ears and whiskers hang rigid | anim | — |
| [018](018-ratoman-has-no-fighting-clips.md) | Ratoman has no clips to fight with | anim + content | 019 |
| [019](019-ratoman-has-no-brain.md) | Ratoman has no brain: nothing makes him chase, attack or walk | ai + gameplay | 032, 034 |

### Sophia front

| # | Title | Area | Blocks |
|---|---|---|---|
| [020](020-sophia-is-not-in-unreal.md) | Sophia isn't in Unreal: export, import, first check | art + anim | 021–029 |
| [021](021-sophias-hips-collapse.md) | Her hips collapse: correctives and thigh twist have no driver | anim | 029 |
| [026](026-sophia-cannot-walk.md) | She can't walk: no IK Rig, no locomotion | anim | 027, 029 |
| [022](022-sophias-masks-are-not-in-the-materials.md) | Body and shirt masks aren't in the materials | art + render | 029 |
| [023](023-sophias-physics-asset-and-hair.md) | No physics asset, and her hair goes through the jacket | anim + physics | 024, 030 |
| [027](027-sophia-has-no-commissar-stance.md) | No stance: ready pose, aim offset, shot | anim + tools | 029, 030 |
| [028](028-the-katana-never-leaves-the-scabbard.md) | The katana never leaves the scabbard | anim + content | 029, 030 |
| [025](025-sophias-face-never-moves.md) | Her face never moves | anim | — |
| [024](024-sophias-jacket-hangs-rigid.md) | Her jacket hangs rigid | art + physics | — |
| [029](029-sophia-cannot-be-played.md) | She can't be played: no character, controls or camera on the phone | gameplay + anim | 031, 032 |

### Fight systems front (GAS)

Every fight interaction goes through the Gameplay Ability System (user decision, 2026-10-24): a
third-person action game meant for two-player same-room multiplayer later. Effects are applied on
authority, and a 2-player listen-server PIE run is the cheap check.

| # | Title | Area | Blocks |
|---|---|---|---|
| [037](037-there-is-no-ability-system.md) | No ability system: GAS isn't enabled, nothing owns combat state | gameplay | 030, 038, 039 |
| [030](030-nothing-can-be-hurt.md) | Nothing can be hurt: no damage effects, hit reactions or death | gameplay | 019, 032, 038, 039 |
| [039](039-ratoman-has-no-abilities.md) | Ratoman's attacks aren't abilities: claw and roar | gameplay + ai | 019 |
| [038](038-sophia-has-no-abilities.md) | Sophia's moves aren't abilities: shoot, combo, draw/sheathe, dodge | gameplay + anim | 029 |

### Arena front

| # | Title | Area | Blocks |
|---|---|---|---|
| [031](031-there-is-no-arena.md) | No arena: greybox level, extraction point, win and lose | gameplay + level | 032 |
| [032](032-there-are-no-waves.md) | No waves: nothing spawns enemies | gameplay | — |
| [033](033-the-app-has-no-front-door.md) | The app has no front door | gameplay + ui | 002 |

## Known

| # | Title | Area |
|---|---|---|
| [001](001-the-depth-feed-renders-black.md) | The depth feed renders black | ar + render |
| [035](035-motion-from-video.md) | Sophia's organic moves have no source: the video-to-motion pipeline | tools + anim |
| [036](036-a-reloaded-room-does-not-know-where-it-is.md) | A reloaded room doesn't know where it is: no relocalization | ar + recon |
| [040](040-there-is-no-parkour.md) | There's no parkour: vault, climb, mantle (movement component + abilities) | gameplay + anim |
| [041](041-two-players-in-one-room.md) | Two players can't share a room: transport, shared AR space, TSDF sync | net + ar + recon |

## Done

| # | Title | Date |
|---|---|---|
| [014](014-ratoman-has-no-ik-rig.md) | Ratoman has no IK Rig | 2026-10-24 |
| [013](013-ratomans-face-is-not-in-an-animbp.md) | Ratoman's expressions play only as a test clip: no Pose Asset in an AnimBP | 2026-10-24 |
