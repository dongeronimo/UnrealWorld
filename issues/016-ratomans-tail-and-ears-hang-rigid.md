# 016 — Ratoman's tail, ears and whiskers hang rigid

**Area:** anim · **Status:** open · **Blocked by:** 015 (same post-process ABP), 017 (the capsules the tail collides with)

## Context

*Filed 2026-10-23.*

No retargeted clip touches `CC_Extra_Tail01..10` (1.4 m in all, 14 cm per bone), `CC_Extra_L/R_Ear`
or `CC_Extra_L/R_Whisker`. A 1.4 m tail held rigid behind a fighting brute is the first thing anyone
sees. §6 of `Ratoman_Brute_Unreal.md` lists the options:

- **AnimDynamics** (built in), in chain mode on the tail, with gravity, damping and 25–35° limits per
  bone. It's the easiest.
- **Kawaii Physics** (free on Fab, UE 5.3–5.8), a spring chain with capsules on the thighs, so the
  tail doesn't pass through his legs. It looks better, and it's what ToySoldiers used.
- A Control Rig sine wave (Chain Harmonics) for an idle sway. It fights physics if combined with it.

## What to do

- Kawaii Physics on the tail, in `ABP_Ratoman_Post` after the twist Control Rig, colliding with
  thigh and calf capsules.
- AnimDynamics (or Kawaii) on each ear: a single bone, small limits, a stiff spring. It runs after
  the expression layer (013), because the expressions rotate the ears.
- Whiskers: a very stiff spring, or leave them rigid.
- A teleport or respawn **resets the chains to rest**, so a spawned wave (032) doesn't whip its
  tails across the map on the first frame.

## The tempting wrong fixes

- **Simulating `CC_Extra_Tail01`.** The root is where the tail meets the hip. Simulate from the
  first bone below it, or the base of the tail detaches. The same rule was measured in gurps 047
  for hair: the root stays kinematic.
- **Baking swing into the clips.** Retargeted clips don't carry it, and baked motion can't react
  to a hit or a turn.
- **Control Rig Physics.** It's experimental in 5.7 and in its own plugin.

## Done when

- He runs and turns, and the tail lags and swings without passing through his legs. The ears flap
  slightly with head motion and still pin back in the angry pose.
- Ten of them on screen on the phone: the cost is measured and recorded here (the arena's waves
  are the reason).

## Files

```
Ratoman_Brute_Unreal.md   §6, §9
D:\gurps\issues\047-hair-hangs-rigid.md   the root rule and the reset-on-teleport rule
```
