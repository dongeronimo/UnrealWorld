# Ratoman Brute in Unreal

A step-by-step guide from the FBX files to a character that moves well: imported, checked, retargeted,
with his twist bones driven by a Control Rig, his expressions as a Pose Asset, and his tail and ears
moving on their own.

Written 2026-10-14 for **UE 5.7**, checked against the 5.6 and 5.7 release notes. Those two versions changed
three things this guide touches: the IK Retargeter became a stack of operations, FBX import goes through
Interchange, and physics inside Control Rig moved into its own experimental plugin. Where I was not sure of
an exact menu or node name in 5.7, the text says what the thing *does*, so you can find it by searching.
I have not run these steps in an editor.

---

## 0. What you have

`D:\unrealworld\art\ratoman_brute_unreal_cm\`, in centimetres. The files with the same names in
`ratoman_brute_unreal\` are the old metre export; don't use them.

| File | What it is | Import as |
|---|---|---|
| `Ratoman_Brute.fbx` | the character: mesh, 115 bones, 12 morph targets, texture embedded | **Skeletal Mesh** (creates the Skeleton) |
| `Ratoman_Brute_aerobic_dance_315220.fbx` | test dance, 455 frames, 30 fps | **Animation**, onto his Skeleton |
| `Ratoman_Brute_Expressoes_poses.fbx` | 5 frames: neutral, angry, evil_laugh, pain, scream | **Animation**, then turned into a Pose Asset |
| `Ratoman_Brute_Expressoes_teste.fbx` | 265 frames that run through all four expressions | **Animation** |
| `Ratoman_Brute_tripo_rgb_….png` | the texture, also embedded in the FBX | a spare copy, if the embedded one fails |
| `..\ratoman_brute_unreal\Ratoman_Brute_unreal_cm.blend` | the Blender source of all the above | — |

What was already fixed in Blender, so you don't hunt for these problems:

- **Everything is in centimetres.** The FBX says "centimetres" (`UnitScaleFactor` 1), every node has
  scale 1, and `CC_Base_Hip` sits at 111. Unreal has nothing to convert, so there is no "root bone at
  scale 100" problem.
  The first export was in metres. Unreal converted it on import and put the ×100 on `RL_BoneRoot`. No
  Blender FBX export option avoids that, so `D:\UnrealWorld\blender_utils\to_centimeters.py` scaled
  the .blend itself ×100 (bones, mesh, shape keys and every action's location keys) and set the scene's
  Unit Scale to 0.01.
- **The reference pose is his A-pose.** The mesh is bound in the A-pose, which becomes his
  reference/retarget pose in Unreal. The T-pose action from AccuRig was left out on purpose.
- **No leaf bones.** There are no `_end` bones.
- **Single root.** The root is `RL_BoneRoot`. Blender writes an empty node named `Armature` above it,
  which Unreal normally drops. Check this in step 2.

### The skeleton in one paragraph

He has the 101-bone **CC_Base** skeleton (Reallusion/AccuRig) plus 14 extra bones:
- **Tail:** `CC_Extra_Tail01` to `CC_Extra_Tail10`, under `CC_Base_Hip`.
- **Ears:** `CC_Extra_L_Ear` and `CC_Extra_R_Ear`, under `CC_Base_Head`.
- **Whiskers:** `CC_Extra_L_Whisker` and `CC_Extra_R_Whisker`, also under the head.

The jaw is `CC_Base_JawRoot`, and on him **a negative rotation opens the mouth**.

The twist bones matter most for this guide: `UpperarmTwist01/02`, `ForearmTwist01/02`,
`ThighTwist01/02` and `CalfTwist01/02` on each side. The skin is weighted to them. **Nothing animates
them unless something drives them.** That is section 5.

---

## 1. Import the character

Drag `Ratoman_Brute.fbx` into a folder, for example `/Game/Characters/RatomanBrute/`.

| Option | Value | Why |
|---|---|---|
| Skeletal Mesh | on | |
| Skeleton | *none* (create new) | this is his own skeleton |
| Import Animations | **off** | the clips come separately |
| Import Morph Targets | **on** | the 11 face shapes plus `V_None` (a harmless leftover from AccuRig) |
| Use T0 As Ref Pose | **off** | the reference must be the bind pose (A-pose) |
| Convert Scene | on (default) | |
| Force Front X Axis | off | |
| Import Uniform Scale | 1.0 | |
| Normals | Import Normals | |
| Material | Create New Materials, Import Textures | |

**5.7 imports FBX through Interchange.** The dialog is laid out differently from the old one: a
pipeline with sections for skeletal meshes, animations, materials and so on. The options above are the
same ideas under different headings, so if you can't find one, use the dialog's search (`morph`, `T0`,
`scale`, `physics`). Also turn off *Create Physics Asset* if it's offered; section 7 builds a better one.

If Interchange misbehaves with this file (wrong skeleton, missing bones), the console variable
`Interchange.FeatureFlags.Import.FBX False` switches back to the legacy importer. Use it to rule the
importer out, not as a permanent setting: Epic is moving away from legacy, and 5.7 already fixed several
Interchange FBX skeleton bugs.

Unreal creates `Ratoman_Brute` (Skeletal Mesh), `Ratoman_Brute_Skeleton` and
`Ratoman_Brute_PhysicsAsset`. Delete the physics asset; you'll rebuild it in section 7 with better
settings.

**The material.** It's a Tripo bake: one texture with colour only. Plug it into Base Color, set
Roughness to about 0.7 and Metallic to 0. If you want the goggle lenses to glow, paint a small mask
later.

---

## 2. Check it before doing anything else

Open the Skeletal Mesh and go through this list. If something here is wrong, everything after it will be
wrong too.

- [x] **Height:** about **200 cm**. Use the viewport's measure tool, or check the bounds in the asset
      details.
- [x] **Skeleton tree:** the top bone is `RL_BoneRoot`, with no `Armature` bone above it. Total **115
      bones**.
- [x] **Bone scale:** select `RL_BoneRoot` and `CC_Base_Hip`; their scale is 1, 1, 1.
- [x] **Morph targets** (Skeletal Mesh editor → **Window → Morph Target Previewer**; it usually opens
      as a tab next to Asset Details): it lists `snarl_L/R`, `lipCornerBack_L/R`, `lipLowerDown_L/R`,
      `browDown_L/R`, `noseWrinkle`, `nostrilFlare`, `browInnerUp` (and `V_None`). Drag `snarl_L` to
      1: the upper lip lifts off the left fang.
- [x] **Texture:** present on the mesh.

Then import the three animation FBX files onto `Ratoman_Brute_Skeleton`. In Interchange, point the
animation import at the existing skeleton and **turn mesh import off**. The two `Expressoes_*` files
carry the mesh as well (it's how the morph curves travel), and you don't want a second copy of the
character.
- [x] **The dance** plays at about 15 s, and the skin follows. The forearms and thighs will look slightly
      stiff when twisted; section 5 fixes that.
- [x] **`Expressoes_teste`:** the face moves, the ears pin and droop, and the jaw opens. In the
      animation's **Curves** panel you see the morph curves (`snarl_L`, etc.).
- [x] **`Expressoes_poses`** is **5 frames** long.

If the reference pose shows a T-pose instead of the A-pose, *Use T0 As Ref Pose* was on. Reimport.

---

## 3. Retargeting (IK Rig + IK Retargeter)

You know this tool, so here is only what's specific to him.

### What changed in 5.6/5.7

If your retargeting practice is from 5.4 or 5.5, the Retargeter now looks different. Its work is an
**op stack**: an ordered list of operations you can reorder, switch off or add to. **Add Default Ops**
gives:

| Op | What it does |
|---|---|
| **Pelvis Motion** | moves the hips, scaled for proportions; formerly the "root" phase. Uses each IK Rig's **retarget pelvis**, or a pelvis bone you pick in the op |
| **FK Chains** | copies each mapped chain's rotation (and translation, by mode) |
| **IK Chains** / **Run IK Rig** | IK goals on hands and feet: plant feet, Floor Constraint, stride warping |
| **Root Motion** | copies or generates root motion |

Others worth knowing for him:
- **Copy Base Pose** aligns the target's resting pose to the source (A-pose against T-pose). It's the
  op-stack answer to a mismatched retarget pose.
- **Stretch Chains** matches chain lengths to the source.
- **Pole Vector Alignment** makes knees and elbows bend the same way as the source.
- **Filter Bones** smooths noise on large characters.
- 5.7 adds a **crotch height** setting, which stops the pelvis from crashing to the ground on a
  differently proportioned character, and a **floor constraint** for the feet.

Bones that aren't in any chain keep their reference pose relative to their parent. That's what happens to
the twist bones, and why section 5 exists.

### IK Rig for the Ratoman

**Retarget pelvis:** `CC_Base_Hip`. (Before 5.6 this was "Retarget Root".)

**Chains** (try the IK Rig's auto-creation of chains first, then fix the result against this table):

| Chain | Start | End | Note |
|---|---|---|---|
| Spine | `CC_Base_Waist` | `CC_Base_Spine02` | 3 bones (Manny has 5; the retargeter spreads it) |
| Neck | `CC_Base_NeckTwist01` | `CC_Base_NeckTwist02` | |
| Head | `CC_Base_Head` | `CC_Base_Head` | |
| LeftClavicle | `CC_Base_L_Clavicle` | `CC_Base_L_Clavicle` | |
| LeftArm | `CC_Base_L_Upperarm` | `CC_Base_L_Hand` | the twist bones are **not** on this path (Hand hangs from Forearm), so they stay out automatically |
| LeftLeg | `CC_Base_L_Thigh` | `CC_Base_L_Foot` | same: the twist bones hang to the side |
| Left fingers | `L_Thumb1..3`, `L_Index1..3`, … | | if the source has fingers |
| …the same on the right | | | |

**Leave unmapped:**
- the twist bones (section 5 drives them)
- `CC_Base_Pelvis`, which stays at rest under Hip and carries the thighs
- the tail, ears, whiskers and jaw (they get their own motion in sections 6 and 8)

The auto-mapping (including "map all (fuzzy)") will happily match `Tail`, `Twist` and `Ear` to something
on the source. Unmap those by hand.

### Retarget pose

His reference pose is an **A-pose with long arms and claws**.
- **UE5 Manny as the source:** also an A-pose, at a different angle. Edit his retarget pose and use
  **Auto Align** on the arms.
- **A T-pose source** (Mixamo and others): add the **Copy Base Pose** op, or make a retarget pose that
  brings one to the other. Don't leave an A against a T.

He is 2.0 m tall with a hunched neck and a long snout. If the head looks at the floor, rotate
`CC_Base_Head` a few degrees in his retarget pose.

---

## 4. Control Rig, demystified

### What it is

A **Control Rig is a node graph that runs every frame, reads the skeleton's pose and writes it back.**
That's all. It's to bones what a material graph is to pixels.

> If you know Blender: it's **drivers and constraints**, but as one graph you can read, running in
> the engine. In Blender, the AccuRig twist problem was solved with drivers ("ThighTwist01 rotates -0.8 ×
> the thigh's twist"). Control Rig is exactly that, in Unreal.

### Why it looks baroque

The same asset type does three different jobs, and the tutorials mix them together:

1. **Animator rig.** Controls (the coloured shapes), FK/IK switches and spaces, for keyframing in
   Sequencer. This is the big, intimidating part. **You don't need it.**
2. **Procedural layer.** A small graph on top of any animation: "twist these bones from those", "make
   the tail sway", "aim the head". **This is what you need.** No controls at all.
3. **Modular Control Rig.** Rigs built from prefab modules. Also not needed.
4. **Control Rig Physics** (experimental). Physics bodies simulated inside the graph. In 5.7 it moved
   into its own experimental plugin and also needs the Physics Control plugin. It's interesting for the
   tail one day, but it's experimental; section 6 uses tools that are stable today.

5.7 also added a **Dependency View** to the Control Rig editor, which draws how data flows through the
graph. It's handy for checking that a twist bone reads from the bone you meant.

So for the Ratoman you'll use only the **Forwards Solve** event: the graph that runs every frame after
the animation has posed the skeleton. No controls, no Backwards Solve, no Construction event.

### How it runs on top of every animation

Two ways:

- **Inside an Animation Blueprint:** AnimGraph → `[your locomotion etc.] → Control Rig node →
  Output Pose`.
- **As a Post Process Anim Blueprint** (recommended for twist). In the Skeletal Mesh asset details,
  *Post Process Anim Blueprint* runs **after** whatever animation the mesh is playing: an AnimBP, a
  single clip, Sequencer or a retargeted animation. You set the twist once on the mesh and every animation
  gets it.

---

## 5. Twist bones with a Control Rig (the main recipe)

### The problem

The skin of his arms and legs is spread across the twist bones. Animations from other skeletons
(Explosive, Mixamo, Manny without its twist setup) don't animate them, so they sit in the reference pose
while the hand or thigh rotates. The skin then twists all at once at one point: a candy-wrapper wrist,
or a folded fold at the hip. The fix is to **work out each twist bone's rotation from the bone that
actually rotates**.

### The idea: swing and twist

Any rotation of a bone splits into two parts:
- **Swing:** where the bone points.
- **Twist:** how much it rolls around its own length.

Only the **twist** gets spread across the twist bones, never the swing. Control Rig has a node that does
the split for you (**To Swing & Twist**, in the Quaternion math nodes).

### What drives what (his hierarchy, checked in the .blend)

```
Upperarm ─┬─ UpperarmTwist01 ── UpperarmTwist02     (Twist01 starts at the shoulder, same point as the Upperarm)
          └─ Forearm ─┬─ ForearmTwist01 ── ForearmTwist02
                      └─ Hand
Thigh ────┬─ ThighTwist01 ── ThighTwist02           (Twist01 starts at the hip)
          └─ Calf ─┬─ CalfTwist01 ── CalfTwist02
                   └─ Foot
```

There are two kinds of twist bone, and they need opposite treatment:

**A. Upper arm and thigh: counter-twist near the root.** The twist bones are children of the bone
that rotates, so they already inherit 100% of its twist. Without a correction, the whole roll reaches
the shoulder and hip skin. Undo most of it at the root and give most of it back at mid-limb:

| Bone | Local rotation around its own axis | Result (share of the twist it keeps) |
|---|---|---|
| `UpperarmTwist01` | **−0.8 ×** the twist of `Upperarm` (local) | 20% at the shoulder |
| `UpperarmTwist02` | **+0.6 ×** the twist of `Upperarm` | 80% from mid-arm to the elbow |
| `ThighTwist01` | **−0.8 ×** the twist of `Thigh` (local) | 20% at the hip |
| `ThighTwist02` | **+0.6 ×** the twist of `Thigh` | 80% from mid-thigh to the knee |

These are the same numbers used in Blender for Aslanyah (`torcao_coxa.py`), where they turned a folded
fold at the hip into a soft crease.

**B. Forearm and shin: spread the twist of the child.** The twist comes from the **hand** rolling
(pronation) or the foot turning. The forearm twist bones are its *siblings*, so they inherit none of it,
and the wrist skin takes the whole roll. Give them part of it:

| Bone | Local rotation around its own axis | Result |
|---|---|---|
| `ForearmTwist01` | **+0.25 ×** the twist of `Hand` (local) | 25% near the elbow |
| `ForearmTwist02` | **+0.5 ×** the twist of `Hand` (adds to 01) | 75% near the wrist |
| `CalfTwist01` | **+0.25 ×** the twist of `Foot` (local) | |
| `CalfTwist02` | **+0.5 ×** the twist of `Foot` | |

Start with these and adjust by eye. The forearm is the one that matters most for claws doing things.

### Building it

1. **Create the asset.** Right-click `Ratoman_Brute` (the Skeletal Mesh) → **Create → Control
   Rig**. If your version doesn't offer that, use Content Browser → Animation → Control Rig and pick the
   plain **Control Rig**, not Modular. Name it `CR_Ratoman_Twist`.
   If the Rig Hierarchy panel is empty, right-click in it and choose **Import** from the Skeletal Mesh.
2. **Find the twist axis.** In the Rig Hierarchy or the Skeleton editor, turn on the bones' local axes
   and look at `CC_Base_L_Forearm`. Note which local axis runs **along the bone**, from elbow to wrist.
   From a Blender export it is normally **Y**. Use that axis everywhere below. If the twist ends up
   looking like a bend, you picked the wrong axis.
3. **Make one reusable function.** In My Blueprint → Functions, add `DistributeTwist` with these inputs:
   - `Driver` (Rig Element Key: the bone whose twist you read)
   - `Twist01`, `Twist02` (Rig Element Key)
   - `F01`, `F02` (Float)
   - `Axis` (Vector, `(0,1,0)` if your axis is Y)

   Body:
   ```
   Get Transform (Item = Driver, Space = Local, Initial = false)
     → Rotation → To Swing & Twist (Twist Axis = Axis) → Twist (quaternion)
     → To Axis And Angle → Axis, Angle
   From Axis And Angle (Axis, Angle × F01) → Set Rotation (Item = Twist01, Space = Local)
   From Axis And Angle (Axis, Angle × F02) → Set Rotation (Item = Twist02, Space = Local)
   ```
   Set Rotation in **Local** space *replaces* the twist bone's local rotation, measured from the parent's
   current pose. That's what the tables above assume.
4. **Forwards Solve:** chain eight calls.
   ```
   DistributeTwist(L_Upperarm, L_UpperarmTwist01, L_UpperarmTwist02, -0.8, 0.6)
   DistributeTwist(R_Upperarm, R_UpperarmTwist01, R_UpperarmTwist02, -0.8, 0.6)
   DistributeTwist(L_Thigh,    L_ThighTwist01,    L_ThighTwist02,    -0.8, 0.6)
   DistributeTwist(R_Thigh,    R_ThighTwist01,    R_ThighTwist02,    -0.8, 0.6)
   DistributeTwist(L_Hand,     L_ForearmTwist01,  L_ForearmTwist02,   0.25, 0.5)
   DistributeTwist(R_Hand,     R_ForearmTwist01,  R_ForearmTwist02,   0.25, 0.5)
   DistributeTwist(L_Foot,     L_CalfTwist01,     L_CalfTwist02,      0.25, 0.5)
   DistributeTwist(R_Foot,     R_CalfTwist01,     R_CalfTwist02,      0.25, 0.5)
   ```
5. **Test inside the Control Rig editor.** The preview can play an animation: pick the dance in the
   preview settings. Then rotate the hand around the forearm in the viewport, or scrub to a frame where
   he turns a palm. The forearm should roll gradually instead of pinching at the wrist.
6. **Plug it in.** Create an Animation Blueprint `ABP_Ratoman_Post` for his skeleton. Its AnimGraph is
   `Input Pose → Control Rig (CR_Ratoman_Twist) → Output Pose`. In the Skeletal Mesh asset, set
   **Post Process Anim Blueprint = ABP_Ratoman_Post**. From then on, every animation on him (the dance,
   anything retargeted, Sequencer) gets the twist.

> **Pitfall:** the angle from *To Axis And Angle* can come out in the range 0..360° with a flipped
> axis. If a twist bone suddenly snaps 180° at some pose, normalise the angle to −180..180 before
> multiplying, or take the twist quaternion's shortest form (some versions have an *Unit / Shortest*
> option on the node).

> **Why not Control Rig's built-in "Twist Bones" node?** It spreads the twist of the *end* of a chain
> along the bones of that chain. The CC twist bones aren't arranged that way: the forearm twist bones are
> siblings of the hand, and the upper-arm ones have to *counter*-twist. The small function above says
> exactly what each bone gets.

> **Why not a dual quaternion deformer?** 5.7 ships a prebuilt dual-quaternion deformer (Deformer
> Graph) that keeps volume when a joint twists, and it supports morph targets. It reduces candy-wrapping
> without twist bones, but it changes how *all* of his skin deforms, and his weights were tuned for
> standard skinning. Try it later as a comparison, not instead of the twist bones.

> **Why not just mapping the twist bones in the retargeter?** It only copies what the *source* animates.
> Explosive has no twist bones, so there's nothing to copy. And when the source does have twist bones,
> their distribution was tuned for another body. Working them out from the main bones gives the same
> result whatever the source.

---

## 6. Tail and ears that move on their own

The retargeted animations don't touch the tail, ears or whiskers. Give them motion in the same post-process
ABP, before or after the Control Rig node.

**Tail.** 10 bones, 14 cm each, 1.4 m in total.
- **Easiest:** the **AnimDynamics** node (built in). Set it to chain mode, with `CC_Extra_Tail01` as
  the bound bone and `CC_Extra_Tail10` as the chain end. Give it some gravity and damping, plus angular
  limits per bone (about 25–35°). That gives inertial lag and swing when he moves.
- **Better looking:** the **Kawaii Physics** plugin (free, on Fab; its listing covers UE 5.3 to 5.8). Spring-chain physics with collision
  capsules on the thighs, so the tail doesn't pass through his legs. It's what most UE5 animal tails
  use.
- **Idle sway without physics:** a Control Rig node that writes a travelling sine wave down a chain
  (*Chain Harmonics*). Fine for an idle; combined with physics it can fight.

**Ears.** The same AnimDynamics setup on `CC_Extra_L_Ear` and `CC_Extra_R_Ear` (single bone, small
limits, stiff spring) makes them flap a little when he moves his head. Keep it subtle. The expressions
also rotate the ears (section 8), so put the physics **after** the expression layer.

**Whiskers.** Leave them rigid, or give them a very stiff AnimDynamics. Up close, a tiny quiver sells
"rat".

---

## 7. Physics asset

The default auto-generated physics asset puts a body on every twist and finger bone, which makes a mess.
Right-click the mesh → **Create → Physics Asset** with:
- **Minimum bone size** about 8–10 cm, so finger and twist bones are skipped.
- **Capsules.**
- Then delete any body still on twist bones, fingers, toes, jaw, whiskers and the ear-ring area.

Keep: Hip, Waist/Spine, Head, upper arm, forearm, hand, thigh, calf, foot. For the **tail**, add 3–4
small capsules spread along it, or leave it to Kawaii Physics' own capsules.

---

## 8. Facial expressions (Pose Asset)

The four expressions combine a jaw rotation (the bone), ear, whisker and head rotations, and morph
targets. The `Expressoes_poses` clip holds all four, one per frame:

| Frame (Unreal, starting at 0) | Pose |
|---|---|
| 0 | neutral |
| 1 | angry |
| 2 | evil_laugh |
| 3 | pain |
| 4 | scream |

### Make the Pose Asset

1. Right-click the `Expressoes_poses` animation → **Create → Create Pose Asset**.
2. Open it and rename the poses `Pose_0..4` to `Neutral`, `Angry`, `EvilLaugh`, `Pain`, `Scream`.
3. In its settings, make it **Additive** with **Base Pose = Neutral**. Each expression is then stored
   as "the difference from neutral", and you can layer it on any body animation: dancing, fighting or
   walking while angry.

### Use it in an Animation Blueprint

The flexible way, which lets you blend several at once:
```
[body animation] ──────────────────────────────┐
                                                ├─ Apply Additive (Alpha = 1) → [twist/tail post-process] → Output
[Pose Asset node: PA_Ratoman_Faces] ────────────┘
      ▲
      └── driven by curves named Angry / EvilLaugh / Pain / Scream (0..1)
          set them with a "Modify Curve" node from float variables (AngryWeight, …)
```
Dragging the Pose Asset into the AnimGraph gives a node that evaluates the poses by **curve weight**.
Each curve with a pose's name blends that pose in, so `Angry = 0.5` is half-angry. Drive those curves
from variables that your gameplay sets.

The simple way: one **Pose By Name** node per expression, chosen with **Blend Poses by Enum** from an
`EFace` enum. You get one expression at a time, with blend time between them.

### Things to know

- **The head rotates in two of them.** `evil_laugh` tips the head back 10° and `scream` raises it 6°.
  Additively, that rides on top of the body animation, which is usually what you want for a laugh. If
  you'd rather the body keep full control of the head, zero `CC_Base_Head` in those two poses in the
  Pose Asset editor.
- **The jaw opens with a negative angle on this rig.** If you animate the mouth by hand or from
  dialogue, rotate `CC_Base_JawRoot` the negative way. About −20° is talking or laughing, −38° is the
  scream. Beyond −45° the cheeks stretch like a membrane.
- **There are no eyes to animate.** The goggle lenses replace the eyes, so there are no eyelids and no
  blink. The eye bones exist (`CC_Base_L/R_Eye`) but move nothing.
- **You can fix a shape in the editor.** 5.6 added a **Sculpt** mode in the Skeletal Mesh editor that
  edits morph targets with the modeling tools. If a key looks off, fix it there. Note that the next
  reimport from Blender overwrites it, so carry the fix back into the json if it should last.
- **The individual morph targets work on their own too.** You can mix your own expressions in the
  Pose Asset editor, or set morph values directly from Blueprint (*Set Morph Target*). A one-sided
  snarl (`snarl_L` only) is a good sneer.
- **Test clip.** `Expressoes_teste` plays all four in sequence, with the laugh's jaw chattering and the
  scream trembling. It's the quickest way to see all of it working once the Pose Asset path is set up.

---

## 9. The order that works

```
AnimBP (gameplay):  locomotion / retargeted clip
                    → Apply Additive (face Pose Asset)
                    → Output
Post Process ABP:   Input Pose
                    → Control Rig: CR_Ratoman_Twist      (twist bones)
                    → AnimDynamics / Kawaii: tail, ears  (physics last, so it reacts to everything above)
                    → Output
```

---

## 10. Known limits of this model

- **Coarse mesh.** Triangles are 3–5 cm, so the snarl and nose wrinkle are broad shapes, and an arm
  fully overhead shows facets. It's fine at gameplay distance; in close-ups it shows.
- **Front of the groin.** It still collapses in a very deep squat; the original AccuRig weights were
  kept there on purpose. Corrective shape keys exist as a technique (`corretivo_volume.py` in Blender)
  if you ever need it.
- **Hip chain.** The chain on his left hip bunches slightly when the leg opens very wide.
- **Fur fringes.** These are flat jagged cards: they flicker a little in motion. Use a two-sided
  material with alpha clip if you see holes.

---

## Changing something later

Every step was a script, recorded in `D:\gurps\tools\blender\README.md`, section "Malha-sopa do Tripo".
The expression values (control positions, intensities, the four presets) live in
`D:\gurps\tools\blender\pele\ratoman_brute.json`. To make the scream bigger or the ears flatter, edit that
file and re-run `expressoes_focinho.py` on the metre .blend (`Ratoman_Brute_unreal.blend`; those scripts
were written for metres). Then convert and export:
```
blender -b Ratoman_Brute_unreal.blend -P D:\UnrealWorld\blender_utils\to_centimeters.py -- Ratoman_Brute_unreal_cm.blend
blender -b Ratoman_Brute_unreal_cm.blend -P D:\gurps\tools\blender\exportar_unreal.py -- D:\unrealworld\art\ratoman_brute_unreal_cm Ratoman_Brute
```
**Reimport the FBX files over the existing assets** to keep the references.
