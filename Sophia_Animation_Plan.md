# Sophia's animation set: plan

How to build a commissar/inquisitor/sororitas-style animation set for Sophia, using Claude Code
for the parts code does well. Her style: a pistol in one hand, held out almost straight and fired
without support; a katana low in the other hand, lowered but ready.

Written 2026-10-16. It assumes [`Sophia_Unreal.md`](Sophia_Unreal.md) for everything about
getting her into Unreal. Tool and licence facts are as I know them at this date; check the
licences before shipping anything.

---

## 1. What Claude can and can't do here

Being clear about this shapes the whole plan.

**Does well** (scripts in Blender, measured with numbers and renders, as with her rig):
- **Poses from targets, not from eyeballed angles.** For example: "the muzzle points at this point
  1.8 m high, 10 m ahead"; "the katana tip 20 cm off the floor, 40° out to the side"; "the left
  foot here". An IK solve places the bones, the result is baked to plain keys, and the error is
  measured (muzzle direction error in degrees, hand in the body, joints past their limits).
- **Procedural motion:** aim offsets, recoil, breathing, idle sway, weight shifts, overlap
  (secondary motion that lags), foot locking, loop closing, mirroring left/right.
- **Pipelines:** video → 3D motion → her skeleton → clean-up → Unreal FBX, with a proof at each
  step, like `retarget_movimento.py` and its 0.000° check.
- **Reading reference frames you give me** (extracted images): naming the key poses, the
  contact frames and the timing beats.

**Does badly:**
- **Organic full-body motion from text alone** (a sword combo, a stumble). Without a performance
  behind them, keyframed key poses look stiff.
- **Judging the *feel*.** I can show you renders and numbers; you decide whether it reads as
  a commissar.
- **Watching video.** I only see the frames that get extracted and handed to me. The heavy work
  (pose estimation) runs as tools on your machine, and I run them.

So the split is:
- **procedural and target-based** for everything that is mostly a pose (most of this set);
- **your own performance on video** for the organic moves;
- **Epic's free sets** for locomotion.

---

## 2. The set, and where each clip comes from

The default hands are **pistol right, katana left**, because her `Pistol` is parented to
`CC_Base_R_Hand`. Mirroring a whole action is a script, if you change your mind.

| clip | what | source |
|---|---|---|
| **Ready pose** | pistol arm almost straight (elbow about 10–15°), muzzle on the aim line; katana low and slightly forward, tip near the floor, wrist ready; weight on the back foot | target-based pose |
| **Ready idle** | the pose plus breathing, a small sway and a slow weight shift; it loops | procedural on the pose |
| **Aim offset** | 9 poses (yaw −90/0/+90 × pitch −45/0/+45), or 15 with ±45 yaw | target-based: spine and shoulder share the turn, the arm keeps the muzzle on target. Measured |
| **Fire** | additive recoil: wrist kick up 8–12°, elbow gives, shoulder back, about 4 frames out and 10 back | procedural |
| **Fire, rapid** | fire with growing drift, recovering between shots | procedural |
| **Locomotion** | walk, jog and run in 8 directions, starts, stops, turns | **Game Animation Sample** (Manny → her IK Retargeter), with the ready pose layered on the upper body from `spine_01` |
| Run with gun | the forward run | already have it (`hold_gun_fastrun_forward` start, loop, end) |
| **Melee** | 2–3 katana cuts, one thrust, a parry, a shoot-then-cut | **your performance on video** (§3), then cleaned up. Or keyed on target poses if a stiff first version is acceptable |
| **Draw / holster pistol** | pistol from the holster | performance or keyframes; contact frames become anim notifies for the socket swap |
| **Sheathe / unsheathe katana** | | performance; this unblocks the katana's attachment |
| **Reload, one hand** | the hard one: katana in the other hand. The usual trick is to drop the mag, holster the pistol, take the new mag from the belt and draw again; or tuck the katana under the arm | performance |
| **Execution** (the commissar trope) | arm up, a pause, one shot | target-based pose + procedural, it is mostly a pose |
| Hit react, death | | Lyra/GAS sets or a performance |

About half the set is target-based and procedural. That half is the "Claude does well" column.

---

## 3. Video → motion → her skeleton

### Which tool

**Rule (user, 2026-10-16): no tool or model with a non-commercial licence, anywhere in the
pipeline.** That rules out OpenPose (CMU, non-commercial) and every tool built on the SMPL body
model (HMR 2.0 / 4D-Humans, GVHMR, WHAM, SMPLify): SMPL is licensed for non-commercial use only.

| tool | gives | licence | use |
|---|---|---|---|
| **MediaPipe Pose** | 33 accurate 2D keypoints, plus a rough depth | Apache 2.0 | **yes**: the 2D detector |
| **RTMPose** (MMPose) | accurate 2D keypoints, including hands as an option | Apache 2.0 (check the weights' terms for the model you download) | **yes**: an alternative or second opinion |
| Rokoko Vision, DeepMotion, Move One | FBX from video, as a service | commercial; output rights depend on the plan, so check the terms | paid alternative |
| OpenPose, HMR, GVHMR, WHAM | | non-commercial | **no** |

**The method: fit her own skeleton to the 2D keypoints.** This is what SMPLify does, but with
Sophia's CC skeleton and proportions, which are ours.
- Search for the pose whose joints, projected through the photo's camera, land on the detected
  keypoints.
- It uses joint limits, a preference for natural poses, and the IK targets that matter (muzzle,
  blade, feet).
- **The weak point is depth:** from one view, an arm reaching forward and one reaching back can
  project alike. **Two views of the same pose (front and side) mostly remove that.** A single view
  falls back on the priors, and on me judging the render against the photo.
- **For video,** the same fit runs per frame, with a smoothness term over time.
- **Drawings:** the detectors are trained on photos and are less reliable on stylised art. There
  I read the pose by eye and set it through targets, comparing a render of Sophia from the same
  camera with the drawing.

### Recording yourself (or a friend)

- **Phone at 60 fps, on a tripod,** at hip height, 3–4 m away. The whole body in frame the whole
  time, including the feet.
- **Fitted clothes and good light.** Loose clothes hide the joints.
- **A second phone at the side**, if you can. With two views the fit resolves depth.
- **A stand-in prop of the right length:** a broom handle for the katana, something
  pistol-sized. The hand placement is what matters.
- **One move per take.** Start and end in the ready pose, which makes cutting and blending easy.
- **Shoot from the front and the side at the same time** when you can. One view works, but the depth then comes from the priors.

### The pipeline (scripts to write, in `D:\gurps\tools\blender\`)

1. **`pontos_2d.py`**: MediaPipe (or RTMPose) on the clip or photos. The output is a JSON of 2D
   keypoints per frame and view, with their confidences.
2. **`ajustar_pose.py`**: fits Sophia's CC skeleton to those keypoints, as above, and bakes the
   result to keys on her armature. The proofs:
   - the reprojection error in pixels per joint;
   - joint limits respected;
   - with two views, the disagreement between them.
   - The fingers are not fitted; they get the fixed grip poses.
3. **`limpar_movimento.py`**:
   - **Filter jitter in rotation space** (a One-Euro or Savitzky–Golay filter on quaternions),
     **never on positions.**
   - **Detect foot contacts** from foot speed and height, and lock them with IK.
   - **Root motion:** hip XY becomes the root bone; Unreal uses that for movement.
   - **Close the loop** where one is wanted: blend the last N frames into the first. Measure the
     seam step against the median step, as with the run loop.
4. **`armas.py`**: weapon constraints applied on top, then baked:
   - the pistol hand keeps the muzzle on the aim line (two-bone IK plus a wrist aim);
   - the katana hand keeps the blade in its plane;
   - fixed grips for both hands.

   The measured output: muzzle error in degrees, frame by frame.
5. **Key reduction.** A video gives a key on every frame. Simplify the curves (Blender's Decimate
   on F-curves, with an error limit), so you can still edit them by hand afterwards.
6. **Check:**
   - renders from 3 angles, with Sophia in her distinct colours;
   - `diag_camadas.py`, to count the clothes crossing in the new clip;
   - the correctives' joint angles staying inside their sampled range.
7. **Export:** `aplicar_escala.py` and `exportar_unreal.py`, as for the other clips.

### Key poses and in-betweens (for the keyed clips)

- **Key poses are solved from targets** (§1). The timing is a list of frames.
- **In-betweens:**
  - quaternion splines through the key poses, with eases;
  - **moving holds**: a tiny drift during a hold, so it never freezes;
  - **overlap**: each chain (spine → head, shoulder → hand → blade tip) lags its parent by
    1–3 frames;
  - **arcs**: the hand and blade tip paths are drawn in the review render so you can judge them.
- **This is where a short performance video helps most, even a rough one.** Its timing and
  weight shifts, applied to clean key poses, beat any keyframe-only result.

---

## 4. Reference videos of store assets

You want your own keys and, eventually, your own animset, without buying the store asset. There
is one line I won't help cross:

- **Fine, and I'll help.** Studying a preview as **reference**: the beats, the timing, the
  silhouette, what makes a move read as a commissar. Give me extracted frames and I'll write a
  **shot list and a timing sheet**: key poses, frame counts, contacts, holds. That is ordinary
  animator practice. You then **perform** the move inspired by it (§3), or I key it from the
  sheet with my own key poses (§2).
- **Not something I'll do.** Running motion extraction on the store preview itself, to turn the
  seller's animation into keys. That is copying the animation you'd otherwise pay for. It is also
  the same data whether the extraction is automated or not.

Free sets you can legally take keys from:
- **Game Animation Sample** and **Lyra** (Epic): free, for Unreal projects. Locomotion, pistol
  and rifle.
- **Mixamo** (Adobe): free, royalty-free in games; you may not redistribute the raw files.
  Retargeting them needs a name map (`mixamorig:*` → `CC_Base_*`).
- **CMU Motion Capture Database**: free for any use, including commercial; you may not resell
  the raw data.
- **100STYLE**: CC BY 4.0. Locomotion in 100 styles; a "proud" or "military" walk is a good base
  for a commissar.
- **Bandai Namco motion dataset**: CC BY-NC (non-commercial only).

---

## 5. The animset in Unreal

- **Locomotion state machine** (or Motion Matching, from the Game Animation Sample), full body.
- **Layered Blend per Bone** from `spine_01`: the upper body takes the **ready pose / ready idle**.
  The legs keep walking.
- **Aim Offset** on the upper body, driven by the aim yaw and pitch.
- **Additive slot** for **fire**, on top of everything.
- **Montages** with an UpperBody slot (or full body where needed): melee, reload, draw/holster,
  sheathe/unsheathe, execution, hit react.
- **Anim notifies:** fire (muzzle flash and sound), socket swaps (pistol hand ↔ holster, katana
  hand ↔ scabbard), footsteps, a sword trail on the cuts.
- **Last in the graph:** the corrective and twist evaluation from `Sophia_Unreal.md` §5. It must
  run after everything else, on the final pose.

---

## 6. Phases

| phase | what | who | done when |
|---|---|---|---|
| 0 | Sophia imported, with correctives, masks and physics (`Sophia_Unreal.md`); Game Animation Sample retargeted to her | you, in Unreal | she walks around with the GAS locomotion |
| 1 | Target-based **ready pose**, **ready idle**, **aim offset**, **fire additive**, **execution** | Claude (scripts and measurements), you judge the renders | muzzle error < 1° across the aim offset; layered over GAS locomotion in Unreal |
| 2 | The video/photo pipeline: MediaPipe set up, `pontos_2d.py`, `ajustar_pose.py`, `limpar_movimento.py`, `armas.py`. First test: poses from 2–3 reference images, then you recording a draw/holster | Claude writes and runs it, you record | one recorded clip is on her in Unreal, with feet locked and the muzzle on target |
| 3 | Melee, sheathe/unsheathe, reload, hit react: one performance each, through the pipeline | you perform, Claude cleans | the montages play in the AnimBP |
| 4 | The animset: AnimBP, notifies, socket swaps, the katana attached | you, with Claude on the logic and the docs | a full loop: draw, aim, fire, cut, sheathe |

Phase 1 needs nothing from you except opinions, and it is most of what makes her read as a
commissar: the stance and the shot.
