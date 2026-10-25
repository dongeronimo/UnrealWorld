# Sophia: corrective shape keys and twist drivers for Unreal

Read this before you import Sophia into Unreal. The source file is
**`D:\UnrealWorld\Art\Sophia_corretivos.blend`** (mesh `Body_Rigged`, armature `Armature`, AccuRig
`CC_Base_*` rig). Use only that file: the other `Sophia_*.blend` files in this folder are
intermediate steps.

The hip of this mesh only looks right when two things happen together:

1. **26 corrective morph targets** (`CORR_*`) are weighted by joint angles every frame.
2. **4 thigh twist bones** get a fraction of the thigh's twist every frame.

In Blender, drivers do both. **Drivers do not survive FBX export.** The morph targets and the bones
reach Unreal, but nothing moves them. You have to rebuild the rules below in Unreal. Without them
she will deform in Unreal like the plain skinned mesh: hip collapse, a groove between glute and
thigh, and the twist wringing the hip skin like a cloth.

---

## 1. What is in the file

| | |
|---|---|
| Mesh | `Body_Rigged`, 14,397 verts / 27,494 tris, already densified at the hips |
| Skinning | Linear (Unreal default). At most **8 influences per vertex**, so import with at least 8 (1,613 verts use more than 4) |
| Armature object scale | 0.01 (AccuRig works in cm) |
| Clips | `Armature\|aerobic-dance_315220\|retarget` (1–455), `Armature\|c08_low_hold_gun_turn180_l\|retarget` (1–91), `Armature\|dance-graceful-378939\|retarget.001` (1–1394, Shahzadah's dance). Ignore `0_T-Pose` and `Key\|0_T-Pose` |
| Other shape keys | `Basis` and `V_None`, which came with the AccuRig/Tripo import and are not part of this system |
| Rule table | JSON string in the custom property `Body_Rigged['corretivos']` (30 rows: 26 keys + 4 twist bones) |
| Live strengths | `Body_Rigged['forca_gluteo'] = 1.0` and `Body_Rigged['forca_quadriceps'] = 0.0` |
| Reference values | **`Sophia_corretivos_referencia.csv`** (next to this file): every frame of the three clips with the joint angles, all 26 key weights and the 4 twist values that Blender computed. Use it to verify your Unreal implementation |

### How the keys were made, and why exactness carries over

Each key is a **rest-space** delta, applied *before* skinning, which is exactly what a UE morph
target is. It was solved so that `LBS(rest + delta) = target shape`, exactly (to 0.001 mm), at its
sample angle, using these skin weights. Between samples the weights blend neighbouring keys
linearly.

So the result in Unreal matches Blender only if:

- **skinning is linear** (not dual quaternion),
- **the skin weights are the same.** Keep 8 influences, and turn on high-precision weights if the
  import offers it,
- **the morph targets are applied unscaled** at the weights computed below.

If you re-weight the mesh in Unreal, or anywhere else, the keys stop being correct. They have to be
regenerated in Blender with the tools in `D:\gurps\tools\blender` (section 6).

---

## 2. The angles: what to measure

Each rule reads **one bone's local rotation relative to its rest pose**, decomposed into
**swing × twist about the bone's long axis**. In Blender that long axis is local **Y**
(head → tail). Blender driver mode `SWING_TWIST_Y`, `LOCAL_SPACE`.

```
q            = bone's local rotation relative to rest (Blender pose_bone.matrix_basis as quaternion)
q            = swing * twist,   twist about local Y
rx (degrees) = degrees( 2 * asin(swing.x) )
rz (degrees) = degrees( 2 * asin(swing.z) )
twist (deg)  = the twist angle about Y
```

I checked this exact formula against the CSV (max difference 0.00007 in key weight).

Signs as measured on this rig:

| Quantity | Formula | Positive means |
|---|---|---|
| Hip **flexion** F, per side | `F = +rx` of `CC_Base_<L\|R>_Thigh` | knee goes forward |
| Hip **abduction** A, Left | `A = +rz` of `CC_Base_L_Thigh` | knee moves away from the midline |
| Hip **abduction** A, Right | `A = −rz` of `CC_Base_R_Thigh` | knee moves away from the midline |
| **Knee flexion** K, per side | `K = −rx` of `CC_Base_<L\|R>_Calf` | foot goes back |
| Thigh **twist** T, per side | twist about Y of `CC_Base_<L\|R>_Thigh` | |

**Axis warning, the main trap.** Unreal bone axes are *not* Blender's: the FBX exporter remaps the
bone axes, and Unreal flips handedness on import. Do not copy "X" and "Z" literally. Pick one of
these:

- **Recommended:** identify the axes geometrically in Unreal. The long axis runs from the thigh head
  to the knee (calf head). Flexion is the swing component that moves the knee forward. Abduction is
  the one that moves the knee away from the body's midline. Measure each relative to the **ref pose**
  in the bone's local (parent-relative) space, using the same `2·asin` swing convention.
- Then **calibrate against the CSV.** Play `c08_low_hold_gun_turn180_l` (the deep squat, the
  strongest case) and `aerobic` in Unreal. Log F, A, K and T per frame and compare them with the
  CSV columns `L_Thigh_rx`, `L_Thigh_rz` (×−1 for R), `L_Calf_rx` (×−1) and `L_Thigh_twist`.
  Signs and magnitudes must match to about a degree. If they do not, the key weights will be wrong
  everywhere.

---

## 3. The rules

`hat` is a piecewise-linear tent: 0 at the previous sample, 1 at its own sample, 0 at the next. The
last sample stays at 1 above itself. Everything is clamped to [0, 1].

```
clamp01(x) = min(max(x, 0), 1)
rise(a, a0, a1) = (a - a0) / (a1 - a0)      fall(a, a1, a2) = (a2 - a) / (a2 - a1)
```

### 3a. Hip volume: 14 keys, `CORR_<L|R>_Quadril_f<flex>_a<abd>`, no strength multiplier

This is a bilinear grid over flexion F × abduction A. The weight is `wF × wA`.

**Abduction weight wA:**
- `_a00` keys: `clamp01((35 − A) / 35)`. Full at A ≤ 0, so adduction (crossing the leg) **keeps**
  the flexion correction. Fades to 0 at 35°.
- `_a35` keys: `clamp01(A / 35)`.

**Flexion weight wF:**

| Key | wF |
|---|---|
| `f045_a00` | `clamp01(min(F/45, (90−F)/45))` |
| `f090_a00` | `clamp01(min((F−45)/45, (125−F)/35))` |
| `f125_a00` | `clamp01((F−90)/35)` |
| `f000_a35` | `clamp01((45−F)/45)`, full at F ≤ 0 (pure abduction or extension) |
| `f045_a35` | same as `f045_a00` |
| `f090_a35` | same as `f090_a00` |
| `f125_a35` | same as `f125_a00` |

Example: the L key `CORR_L_Quadril_f090_a00` at F = 70, A = 10 has
`wF = min(25/45, 55/35) = 0.556` and `wA = 25/35 = 0.714`, so the weight is 0.397.

### 3b. Glute: 6 keys, `CORR_<L|R>_Gluteo_flex_<045|090|125>`, × `forca_gluteo` (= 1.0)

Driven by the hip flexion F of that side only. Samples 45/90/125, starting from 0:
- `045`: `clamp01(min(F/45, (90−F)/45))`
- `090`: `clamp01(min((F−45)/45, (125−F)/35))`
- `125`: `clamp01((F−90)/35)`

Multiply by `forca_gluteo`. Expose it as a tunable parameter defaulting to **1.0**. The user
approved that strength on the sister character (Aslanyah) and on Sophia. The value can go
negative or above 1 (range −5..5 in Blender).

### 3c. Quadriceps: 6 keys, `CORR_<L|R>_Quadriceps_joelho_<045|090|130>`, × `forca_quadriceps` (= **0.0**)

Driven by knee flexion K. Samples 45/90/130, starting from 0:
- `045`: `clamp01(min(K/45, (90−K)/45))`
- `090`: `clamp01(min((K−45)/45, (130−K)/40))`
- `130`: `clamp01((K−90)/40)`

Multiply by `forca_quadriceps`, which **defaults to 0, so the keys are off**. The user found any
positive strength looked worse. Implement it anyway so it can be tried; a negative value deflates
the muscle.

### 3d. Thigh twist bones: 4 bones, not morphs

In the AccuRig rig, `ThighTwist01` is a child of `Thigh` with the same axis, and nothing
counter-rotates it. Without this rule the thigh's whole twist reaches the hip skin. Set **local
rotation about the bone's long axis** to:

| Bone | Local twist | Twist that bone ends up with |
|---|---|---|
| `CC_Base_<L\|R>_ThighTwist01` (hip to mid-thigh) | `−0.8 × T` | 20 % |
| `CC_Base_<L\|R>_ThighTwist02` (child of 01, mid-thigh to knee) | `+0.6 × T` | 80 % |
| `CC_Base_<L\|R>_Calf` (child of Thigh) | untouched | 100 % |

T is the twist of `CC_Base_<same side>_Thigh` (section 2). The twist bones' own swing stays
at rest. The rule *overrides* whatever the animation keys on them.

**Do not cancel the twist on the whole thigh instead.** On Aslanyah that tore a seam at the knee,
because the calf hangs off `Thigh` and keeps all the twist.

---

## 4. Recommended Unreal implementation

- **Use a Post Process Anim Blueprint** on the Skeletal Mesh, with one **Control Rig** node (or
  AnimGraph Blueprint math) that does both jobs:
  1. reads the 6 bone rotations,
  2. writes the 4 twist bones,
  3. writes 26 **morph target curves** with the exact formulas above.
- A post-process ABP runs after *every* animation: the three clips, retargeted clips, blends and IK.
  That is what you want, because the correction is a property of the mesh, not of the clip.
- **Read the angles after IK and other pose edits.** The thigh angles must be the final ones.
- **Prefer this over Pose Driver.** Pose Driver is RBF interpolation, which does not reproduce these
  tents and the bilinear grid. In particular, it does not reproduce "hold `_a00` under adduction" or
  "hold `f000_a35` under extension". You will get weights that differ from what the keys were solved
  for. Use Pose Driver only if you deliberately accept approximate results.
- The 30 rows of `Body_Rigged['corretivos']` hold everything you need in machine-readable form. The
  `CORR_*Quadril*` rows (`eixo: swing_xz_local`) carry the literal Blender expressions in `peso_x`
  and `peso_z`, where `rx` and `rz` are in radians and `57.29578` converts to degrees. The `Gluteo` and
  `Quadriceps` rows (`eixo: swing_x_local`) carry `sinal`, `graus`, `anterior`, `seguinte` and
  `forca`. The `TORCAO_*` rows carry `fracao_local`. To read it:
  `blender -b Sophia_corretivos.blend --python-expr "import bpy;print(bpy.data.objects['Body_Rigged']['corretivos'])"`

---

## 5. Exporting from Blender

- Export the mesh with **shape keys** and import with **Import Morph Targets** on. All 26 `CORR_*`
  must appear as morph targets with these exact names, because the curves are matched by name.
- **Export at a frame where every `CORR_*` value is 0**, or mute the shape-key drivers first.
  Otherwise the exporter may bake a non-zero mix into the base mesh. Frame 1 of the T-pose action is
  safe: the thigh is at rest. Check `Basis` against the result if in doubt.
- **Animations:** the FBX exporter bakes the evaluated bone transforms, so the exported clips already
  contain the driven twist-bone rotations. That is harmless, because the post-process rule overwrites
  them. The exporter may also bake the driven key weights as morph curves inside each AnimSequence.
  If that happens, drop those curves on import or let the post-process values win. Do not rely on
  them, because they only exist for these three clips.
- Armature scale is 0.01. Check that Sophia comes in at human size (about 1.7 m) and that the
  thigh/knee angles in the CSV match (section 2). A scale mistake does not change the angles, but an
  axis mistake does.

---

## 6. If something has to change upstream

The keys are generated, not hand-sculpted. The tools live in `D:\gurps\tools\blender` and are run
in this order on the densified mesh:

1. `corrigir_quadril.py` (arg `k1 0.6`)
2. `lombar_quadril.py`
3. `corretivo_volume.py`
4. `corretivo_musculo.py`

The twist drivers come from `torcao_coxa.py`. Each script's docstring explains its choices and the
rejected alternatives.

- **Any change to the mesh or to the skin weights invalidates every `CORR_*` key.** Regenerate in
  Blender and re-export. Do not try to patch the keys in Unreal.
- **Do not shorten the hamstring ramp back.** The thigh/pelvis blend runs 11 cm down the back of the
  thigh (`K_COXA 0.6`). With the original 18.6 cm, the volume keys swung that skin into a large
  hanging sack under the glute.
- **The groin is the known remaining weak spot.** In the extreme squat its retention is 0.68 (min
  0.48). The volume target in front of the hip is plain linear skinning by design, because DQS there
  swelled the top of the thigh into a lip. Do not "fix" it by switching Unreal to dual-quaternion
  skinning. That breaks every key (section 1), since they were solved for linear skinning.

## 7. Done means

- In Unreal, playing `c08_low_hold_gun_turn180_l` and `aerobic-dance_315220`, the per-frame morph
  weights and twist values match `Sophia_corretivos_referencia.csv` to about ±0.01 in weight and
  ±1° in twist.
- Visually against Blender (same frame, with keys): gun frames 1/50/84 and aerobic frame 228. The
  Blender renders are in `D:\UnrealWorld\Art\sophia_checks\corretivos_clip\AB_clip.png`: the top row is
  without keys, the bottom row is with keys. The bottom row is the reference.
