# The arena vertical: from Sophia's import to milestone 1's arena

*Written 2026-10-27.* The order in which to work the cards so that Sophia, played on the phone,
fights waves of Ratomen in the arena, kills them, can be killed, and can extract. It doesn't
replace the cards. Each step below is a card, and the card has the details, the tempting wrong
fixes and its own done-when. This file sets only the **order**, the **checkpoints** and the
**decisions** that have to be made before some steps.

## Done when

This is the arena half of 002's done-when:

- On the Galaxy, Sophia fights at least three waves of Ratomen with katana and pistol, from touch.
- She can die (lose), and she can reach the extraction point (win). Retry and back both work.
- She's complete: clothing masks, wounds that follow her Health, correctives, hair and jacket
  physics, a face that reacts, the commissar stance.
- Every fight interaction is GAS, and the fight also works in a 2-player listen-server PIE.

**Milestone 1 needs more than this vertical:**
- the front door (033) and AR kept out of the arena (042), both in Phase 7 below;
- the room session (003–012, 034), which is its own front. It shares only Ratoman's brain (019)
  with this plan.

## Two tracks, one meeting point

The work splits by where it's done:

- **Editor track:** import, materials, physics assets, AnimBPs, clips. This is you in the
  Unreal editor (and Blender for the stance), one verified step at a time.
- **Code track:** GAS, damage, abilities, the AI, the game mode, waves. This is mostly C++ that
  Claude writes, with small blueprint subclasses that set assets.

They meet at **029**, where Sophia becomes the player. Until then they run side by side.
Alternating between them keeps the UI work in short sessions.

**The code track doesn't wait for Sophia.** The player character is Abstract C++, and the mesh is
a blueprint setting, so the fight can be proved with **Manny as a stand-in player**
(`BP_Sophia_Standin`, the Third Person template's mesh) against the Ratoman, who is already in
Unreal. When Sophia is ready, `BP_Sophia` sets her mesh and ABP on the same class. This proves
GAS, damage, the AI and the waves months before the art is done, and it keeps a failure in one
track from hiding behind the other (002's rule).

## Decisions to make before the step that needs them

| decision | needed before | where it's recorded |
|---|---|---|
| **Mobile skinning: 4 or 8 influences.** If the Galaxy caps at 4, run `limitar_influencias.py` in Blender and re-export | 021 (the correctives were solved against the exact weights) | 020 |
| **Which hand holds what.** The katana bone is under `R_Hand`, and the plan says pistol right | 027 (every pose is solved from this) | `Sophia_Animation_Plan.md` §2, 027 |
| **Locomotion: state machine or motion matching** | 026 | 026 (measured, not chosen by taste) |
| **Jacket: Chaos Cloth or Kawaii chains** | 024's end | 024 (phone cost) |
| **Ratoman's tail collision: Kawaii capsules or physics bodies** | 017 | 016 and 017 together |

## The phases

Within a phase, cards on different tracks can run in parallel. A phase ends at its checkpoint.

### Phase 1: Sophia stands in Unreal, and GAS exists

| card | track | what |
|---|---|---|
| [020](issues/020-sophia-is-not-in-unreal.md) | editor | Unpark it. Import, `M_Sophia_Base` instances, §3's checks, the props as static meshes, **the skinning decision** |
| [037](issues/037-there-is-no-ability-system.md) | code | **GAS enters here.** Plugin, ASCs (Sophia's on the PlayerState, Ratoman's on his character), `UCombatAttributeSet`, tags, `UInputAbilityMap`, `UAbilitySet` |

**Checkpoint:** Sophia stands textured in a test level. A test ability fires from input on the
Manny stand-in and on a Ratoman, and `showdebug abilitysystem` shows both, also in a 2-player
listen server.

### Phase 2: her body is right, and things can be hurt

| card | track | what |
|---|---|---|
| [021](issues/021-sophias-hips-collapse.md) | editor | The correctives and thigh twist as a Control Rig, checked against the CSV. Reuse 015's twist rig for the arms and calves |
| [022](issues/022-sophias-masks-are-not-in-the-materials.md) | editor | **The clothing-mask system:** `M_Sophia_Body`, `M_Sophia_Shirt`, the `Wear` vector. **Phone test** |
| [043](issues/043-sophias-wounds-never-show.md) | editor, then code | **The wound layer:** the `HP` scalar in `M_Sophia_Body`, scrubbed by hand first, then wired to Health once 030 lands |
| [017](issues/017-ratomans-physics-asset-is-the-default.md) | editor | Unpark it. Ratoman's bodies, so he can be hit |
| [030](issues/030-nothing-can-be-hurt.md) | code | `GE_Damage`, `ApplyHit`, `GA_HitReact`, `GA_Death`, cues. Proved with a debug "hit the thing I'm looking at" ability from the stand-in |

**Checkpoint:** she crouches with no hip collapse, and taking a garment off shows only the skin
under it, on the phone. The stand-in kills a Ratoman with a debug hit, the Ratoman flinches
and dies, and every hit logs bone and damage.

### Phase 3: she moves, her hair and jacket follow, and the brute can fight

| card | track | what |
|---|---|---|
| [026](issues/026-sophia-cannot-walk.md) | editor | `IK_Sophia`, `RTG_Manny_to_Sophia`, `ABP_Sophia` v0 locomotion. Measure the locomotion choice |
| [023](issues/023-sophias-physics-asset-and-hair.md) | editor | **The hair physics** and her physics asset. Expect 017's CC limb-body problem again |
| [024](issues/024-sophias-jacket-hangs-rigid.md) | editor | Jacket cloth on the panels. **Phone cost decides the solver** |
| [025](issues/025-sophias-face-never-moves.md) | editor | **The facial-expression system:** additive Pose Asset, the blink, face-bone tracks stripped |
| [018](issues/018-ratoman-has-no-fighting-clips.md) | editor | Ratoman's locomotion, swings with gameplay-event notifies, hit react, death |
| [016](issues/016-ratomans-tail-and-ears-hang-rigid.md) | editor | His tail and ears. Can slip to Phase 6 if time is short |
| [039](issues/039-ratoman-has-no-abilities.md) | code | `GA_RatomanClaw`, `GA_RatomanRoar` |
| [019](issues/019-ratoman-has-no-brain.md) | code | `ARatomanAIController`, State Tree, navmesh in `Arena.umap`. **Proved against the stand-in** |

**Checkpoint:** Sophia runs and turns with hair and jacket swinging and her face blinking. In the
arena, five Ratomen chase the stand-in, claw it only inside their hit windows, and die to debug
hits. This is the combat loop working without Sophia.

### Phase 4: her fighting clips

| card | track | what |
|---|---|---|
| [027](issues/027-sophia-has-no-commissar-stance.md) | Blender + editor | **The hands decision first.** Ready pose, aim offset, fire additive, solved and measured (muzzle error < 1°) |
| [028](issues/028-the-katana-never-leaves-the-scabbard.md) | editor | Draw, sheathe, the combo montage, socket swaps, gameplay-event notifies |
| [044](issues/044-sophia-has-no-clips-to-be-hurt-with.md) | editor | Her hit react, death and dodge clips: the clips 030 and 038 play on her |

**Checkpoint:** in a test level she walks with the ready upper body, aims, recoils, draws over the
shoulder, runs a 3-hit combo with the notifies logging, sheathes, flinches, dodges and dies.

### Phase 5: Sophia is the player

| card | track | what |
|---|---|---|
| [038](issues/038-sophia-has-no-abilities.md) | code | `GA_FirePistol`, `GA_KatanaCombo`, draw and sheathe, `GA_Dodge`, built on the stand-in's input path |
| [029](issues/029-sophia-cannot-be-played.md) | both | `BP_Sophia` on the stand-in's class, camera, touch controls, the full `ABP_Sophia` reading GAS tags. **The two tracks meet here** |
| [043](issues/043-sophias-wounds-never-show.md) | code | Second half: `HP` follows the Health attribute, plus the wounded walk and the pained face at the same thresholds |

**Checkpoint:** 029's done-when. On the Galaxy, from touch, she runs, aims, shoots, draws, cuts
and sheathes at a stable frame rate. She kills a Ratoman with each weapon, and her wounds open
as he hits her.

### Phase 6: the arena loop

| card | track | what |
|---|---|---|
| [031](issues/031-there-is-no-arena.md) | code + editor | `AArenaGameMode` replaces the empty one, extraction point, win and lose, HUD |
| [032](issues/032-there-are-no-waves.md) | code | `UWaveSet`, spawn points, three waves. **The largest wave's frame time caps the wave size** |
| [016](issues/016-ratomans-tail-and-ears-hang-rigid.md) | editor | If it slipped from Phase 3. The reset-on-spawn rule matters now |

**Checkpoint:** the vertical's done-when, on the phone.

### Phase 7: milestone 1's arena side closes

| card | what |
|---|---|
| [042](issues/042-ar-runs-in-every-level.md) | ARCore stays out of the arena |
| [033](issues/033-the-app-has-no-front-door.md) | The front door, with the arena as one entry. The room entry waits for 034 |

## The order of dependencies

```
020 ─┬─ 021 ─────────────────────────────┐
     ├─ 022 ── 043a                       │
     ├─ 026 ─┬─ 027 ──────────┐           │
     │       ├─ 028 ──────────┤           │
     │       └─ 044 ──────────┤           │
     ├─ 023 ── 024            │           │
     └─ 025                   │           │
                              ▼           ▼
037 ── 030 ──┬── 038 ─────────────────►  029 ── 043b ──┐
   017 ──┘   │                                         ├── 031 ── 032 ── 033
   018 ──────┴── 039 ── 019 ───────────────────────────┘
   (023 is also 030's: bodies to hit on her)
```

## Phone checkpoints

Desktop proves nothing about the phone (gurps 019). The cards that need a Galaxy measurement, in
the order they come up:

| card | what's measured |
|---|---|
| 020 | the skinning influence limit |
| 022 | the NaN trick survives the mobile renderer and its shadow pass |
| 026 | the locomotion's CPU cost |
| 024 | the jacket alone, then with five Ratomen |
| 016 | ten Ratomen with tail physics |
| 029 | frame time with Sophia playable |
| 032 | frame time with the largest wave alive |

If a number comes back bad, fix it at that card. Don't carry it to 032 and discover it there.

## Not in this vertical

- Parkour (040), multiplayer transport (041), motion from video (035). Known, not scheduled.
- Sophia's alt bodies and outfits. The `Wear` vector supports them, but they aren't built.
- Wounds on the clothes. 043 is the body only, as `Art/sophia_feridas_UNREAL.md` decides.
- An art pass on the arena. It's greybox (031).
