# The AccuRig skeleton in Unreal

Every character rigged in AccuRig (Ratoman, Sophia, and whoever comes next) gets the same 101-bone
Reallusion **`CC_Base_*`** skeleton. This file is the shared reference for its hierarchy and for the
IK Rig that goes on top of it, so each character guide only has to add what is unusual about that body.

Written 2026-10-23 for **UE 5.7**. The hierarchy below was read from Ratoman's .blend
(`Art/ratoman_brute_unreal/Ratoman_Brute_unreal_cm.blend`), not from memory. Before trusting it on a
new character, check that character's Skeleton Tree in Unreal.

---

## 1. The hierarchy

Fingers, toes and the face are cut down to their first bone. `CC_Extra_*` bones are Ratoman's own
additions and are not part of the base rig.

```
RL_BoneRoot
└─ CC_Base_Hip                      ← moves the whole body: the retarget pelvis
   ├─ CC_Base_Pelvis                ← parents ONLY the legs
   │  ├─ CC_Base_L_Thigh
   │  │  ├─ CC_Base_L_Calf
   │  │  │  ├─ CC_Base_L_Foot
   │  │  │  │  └─ CC_Base_L_ToeBase → L_IndexToe1, L_MidToe1, L_RingToe1, L_PinkyToe1
   │  │  │  ├─ CC_Base_L_CalfTwist01 → CalfTwist02
   │  │  │  └─ CC_Base_L_KneeShareBone
   │  │  └─ CC_Base_L_ThighTwist01 → ThighTwist02
   │  └─ CC_Base_R_Thigh …           (mirror)
   ├─ CC_Base_Waist                 ← first spine bone
   │  └─ CC_Base_Spine01
   │     └─ CC_Base_Spine02         ← neck, clavicles and ribs branch here
   │        ├─ CC_Base_NeckTwist01 → CC_Base_NeckTwist02
   │        │  └─ CC_Base_Head
   │        │     └─ CC_Base_FacialBone → CC_Base_JawRoot, eyes, teeth, tongue
   │        ├─ CC_Base_L_Clavicle
   │        │  └─ CC_Base_L_Upperarm
   │        │     ├─ CC_Base_L_Forearm
   │        │     │  ├─ CC_Base_L_Hand → L_Thumb1, L_Index1, L_Mid1, L_Ring1, L_Pinky1 (each …1→2→3)
   │        │     │  ├─ CC_Base_L_ForearmTwist01 → ForearmTwist02
   │        │     │  └─ CC_Base_L_ElbowShareBone
   │        │     └─ CC_Base_L_UpperarmTwist01 → UpperarmTwist02
   │        ├─ CC_Base_R_Clavicle …  (mirror)
   │        └─ CC_Base_L/R_RibsTwist → CC_Base_L/R_Breast
   └─ CC_Extra_Tail01 …             (Ratoman only)
```

### The traps

- **`CC_Base_Pelvis` is not the pelvis.** It is a sibling of `CC_Base_Waist`, both under `CC_Base_Hip`.
  It carries only the thighs. A chain like `Pelvis → Spine02` is invalid, because an IK Rig chain has to
  follow a single parent→child path and Pelvis is not an ancestor of the spine.
- **`CC_Base_Hip` is the bone that moves the body**, the one that Manny's `pelvis` maps to.
- **Names have no underscore before the number:** `Spine01`, `NeckTwist02`, `Thumb1`.
- **The twist bones sit beside the main chain, not inside it.** `Hand` hangs from `Forearm`, and
  `ForearmTwist01` is its sibling. `Upperarm → Hand` and `Thigh → Foot` therefore skip them on
  their own.
- **`NeckTwist01/02` are the real neck**, despite the name. Unlike the limb twists, they lie on the
  path to the head.
- **ShareBones** (`KneeShareBone`, `ElbowShareBone`) and **`RibsTwist`/`Breast`** are helper bones for
  deformation. Nothing should retarget onto them.

---

## 2. IK Rig

**Retarget pelvis:** `CC_Base_Hip`. Before 5.6 this was called "Retarget Root".

| Chain | Start | End | Note |
|---|---|---|---|
| Spine | `CC_Base_Waist` | `CC_Base_Spine02` | 3 bones; Manny has 5, and the retargeter spreads them |
| Neck | `CC_Base_NeckTwist01` | `CC_Base_NeckTwist02` | |
| Head | `CC_Base_Head` | `CC_Base_Head` | |
| LeftClavicle | `CC_Base_L_Clavicle` | `CC_Base_L_Clavicle` | |
| LeftArm | `CC_Base_L_Upperarm` | `CC_Base_L_Hand` | twist bones stay out on their own |
| LeftLeg | `CC_Base_L_Thigh` | `CC_Base_L_Foot` | add `ToeBase` as its own chain if the source has toes |
| LeftThumb … LeftPinky | `CC_Base_L_Thumb1` | `CC_Base_L_Thumb3` | one chain per finger, if the source has fingers |
| …the same on the right | | | |

**IK goals:** on `CC_Base_L/R_Foot` and `CC_Base_L/R_Hand`.

**Leave unmapped:**
- `CC_Base_Pelvis`. It stays at rest under Hip and only carries the thighs.
- The twist bones (`UpperarmTwist`, `ForearmTwist`, `ThighTwist`, `CalfTwist`). A Control Rig drives
  them from the main bones (see `Ratoman_Brute_Unreal.md` §5).
- ShareBones, `RibsTwist`, `Breast`.
- The face: `FacialBone`, `JawRoot`, eyes, teeth, tongue.
- Any `CC_Extra_*` bones (tails, ears, whiskers). They get their own motion.

The auto-chain creation and "map all (fuzzy)" will match `Twist`, `Share`, `Tail` and `Ear` to
something on the source. Start from the auto result, then fix it against this table by hand.

### Retarget pose

AccuRig binds the mesh in an **A-pose**, which becomes the reference pose in Unreal (AccuRig's
`0_T-Pose` action is not exported).
- **Manny as the source:** Manny is also in an A-pose, but at a different angle. Use **Auto Align**
  on the arms in the target's retarget pose.
- **A T-pose source** (Mixamo and others): add the **Copy Base Pose** op, or build a retarget pose that
  brings one to the other.

---

## Per-character notes

| Character | Guide | What's different |
|---|---|---|
| Ratoman | [`Ratoman_Brute_Unreal.md`](Ratoman_Brute_Unreal.md) | tail under Hip; ears and whiskers under Head; long arms and claws; 2.0 m and hunched |
| Sophia | [`Sophia_Unreal.md`](Sophia_Unreal.md) | accessories parented to `CC_Base_Head` |
