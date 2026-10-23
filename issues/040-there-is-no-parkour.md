# 040 — There's no parkour: Sophia can't vault, climb or mantle

**Area:** gameplay + anim · **Status:** known (not scheduled) · **Blocked by:** 029, 037

## Context

*Filed 2026-10-24.*

The game is third-person action with "blades, guns and some parkour" (user, 2026-10-24). Milestone 1
(002) doesn't require parkour, so it's filed here and not scheduled. Two things need settling
before anything is built, because both are expensive to change later:

- **Movement belongs to the movement component, not to GAS.** A vault is an ability: it checks
  tags, adds `State.Traversing`, plays the montage and can be blocked or cancelled. The *motion*
  is a custom movement mode on `UCharacterMovementComponent`, or a montage with root motion and a
  Motion Warping target. Either way, CharacterMovement predicts it and corrects it over the
  network. An ability that sets positions by hand desyncs the moment there are two machines (041).
- **Which movement system.**
  - **CharacterMovement plus Motion Warping** is mature and well understood. The Game Animation
    Sample already has traversal (vault, mantle, hurdle), built on exactly that, and it is the
    obvious starting point, since 026 already brings GAS locomotion onto Sophia.
  - **Mover** (Epic's newer movement plugin) was experimental as of the last check. Check its
    status in 5.7 before considering it.

## The tempting wrong fixes

- **Parkour as abilities that move the capsule with timelines.** It's smooth single-player, and it
  rubber-bands as soon as a server disagrees.
- **Detecting ledges on the reconstructed room now.** The TSDF mesh is a later milestone's problem.
  Prove traversal on the arena's greybox first.

## Done when

- Sophia vaults a waist-high box and mantles a chest-high ledge in the arena, as abilities driving
  Game Animation Sample traversal, and it works in a 2-player listen-server PIE.

## Files

```
issues/026 (GAS locomotion on her), 037 (GAS)
```
