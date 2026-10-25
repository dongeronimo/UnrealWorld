# Sophia's wounds: one HP scalar shows cuts and bruises

Made 2026-10-24. She takes damage in stages. A single material parameter, `HP` (0..1), reveals a
pre-made "0 HP" layer of bruises, scrapes, cuts and blood. Each wound grows from its centre as HP
drops, and blood trails run further down the body. Nothing is per hit and nothing is per location.

## Files

| file | what |
|---|---|
| `feridas/Sophia_Feridas_Tint.png` | RGB **multiply** tint, white = untouched |
| `feridas/Sophia_Feridas_Mask.png` | R = reveal (HP at which the texel starts to show), G = wetness, B = height (only the source of the normal map) |
| `feridas/Sophia_Feridas_Normal.png` | tangent-space normal for the cuts and swelling, **OpenGL** (green up) |
| `feridas/Sophia_Body_Feridas_0HP.png` | the body texture at 0 HP. For looking at only, do not import |
| `feridas/preview/montagem_*.png` | renders at HP 100/75/50/25/0: front, back, face (both sides), legs, clothed |
| `feridas/preview/sophia_feridas_preview.blend` | the same material in Blender, with an `HP` value node to scrub by hand |
| `tools/sophia_feridas_dump.py` | Blender: dumps the rest-pose body (positions, normals, UVs, hair weights, bones) to `feridas/body.npz` |
| `tools/sophia_feridas.py` | numpy: places and draws every wound in 3D and writes the three textures. **The wound list is at the bottom. Retune there** |
| `tools/sophia_feridas_preview.py`, `tools/sophia_feridas_montagem.py` | the preview renders and the contact sheets |

Rebuild after a change:

```
cd D:/UnrealWorld/Art
blender -b sophia_ruiva_preview.blend --python tools/sophia_feridas_dump.py -- feridas/body.npz   # only if the body mesh or UVs change
python tools/sophia_feridas.py feridas/body.npz feridas/
blender -b sophia_ruiva_preview.blend --python tools/sophia_feridas_preview.py -- D:/UnrealWorld/Art/feridas D:/UnrealWorld/Art/feridas/preview
python tools/sophia_feridas_montagem.py feridas/preview frente,costas,rosto,rosto_esq,pernas,vestida
```

## Why it is built this way

- **The overlay multiplies. It is not a second body texture.** Her skin is pale, so every wound darkens
  it. A multiply keeps the baked fishnet black under the blood and works unchanged on the redhead alt
  (`Sophia_Body_Redhead.png`) and on any later body texture. A full "0 HP" copy of the albedo would
  need one copy per alt.
- **The wounds are drawn in 3D, on the rest-pose mesh, not painted in UV space.** A cut crossing a UV
  seam continues on the other island, and blood runs along −Z on the body instead of "down" in the
  texture.
- **The face wounds sit on her right side and the centre of her face.** Her left cheek, her left
  temple and her whole back above the waist are under the hair, so wounds there are never seen. The
  generator also ignores hair cards when it looks for skin.
- **The wounds are drawn about 1.5 times life size** (`SIZE` in the script), so they read at game
  camera distance.
- **Pacing** (the `rev` value of each wound):

  | HP | what shows |
  |---|---|
  | 0.85 | grime, knuckles |
  | 0.7 | bruises on the cheek, shins and forearms |
  | 0.55 | split lip, scrapes |
  | 0.4 | brow cut, the cut on the left forearm, the cut on the left thigh |
  | 0.25 | nosebleed, belly and flank cuts, the deep cut on the right thigh |
  | 0.15 | the last cuts |

  The tone ceiling is an action film, not horror.

## Import

| texture | sRGB | compression |
|---|---|---|
| `Sophia_Feridas_Tint` | on | BC7 (DXT1 bands the soft bruises) |
| `Sophia_Feridas_Mask` | **off** | BC7, or Masks if memory is tight (reveal drops to 5 bits, about 3% HP steps) |
| `Sophia_Feridas_Normal` | off | Normalmap, **Flip Green Channel checked** (the file is OpenGL) |

All three use the body UV (UV0). Keep mips on. The gutters are already filled, so mips do not pull
white into the edges.

## Body material

Add these nodes to the Body material from §2 of `Sophia_Unreal.md`. The WPO mask node stays as it is.

```
HP        = ScalarParameter "HP"        (default 1)
Soft      = ScalarParameter "WoundSoft" (default 0.06; the Blender preview uses 0.06 too)
mask      = TextureSample(Sophia_Feridas_Mask)
vis       = saturate((mask.r - HP) / Soft)
tint      = TextureSample(Sophia_Feridas_Tint).rgb
BaseColor = Body.rgb * lerp(1, tint, vis)
Roughness = lerp(SkinRoughness (0.5), 0.12, mask.g * vis)     // wet blood and open cuts shine
Normal    = lerp(float3(0,0,1), TextureSample(Sophia_Feridas_Normal), vis)
```

- With the body textures this adds three samples and a handful of ALU, which is cheap enough for the mobile path.
- Every material instance of the body (the redhead alt included) inherits this logic unchanged.
- **Only the body gets wounds.** The shirt, skirt and jacket stay clean. Clothes would use the same
  scheme with one Tint/Mask pair per garment. That's a separate job.

## Driving it from health

- Make one **Dynamic Material Instance** on the body slot at BeginPlay (and on any alt material you swap to).
- On damage, set `HP = Health / MaxHealth`. **Interpolate it over about 0.3–0.5 s** (FInterpTo in Tick,
  or a Timeline), so the wounds bloom in rather than snapping on.
- Use the same value for the wounded locomotion swap (the Grruzam wounded walk) and the pained face
  baseline, with the same thresholds, so the material, the animation and the face agree.
- Healing runs the scalar back up. Wounds close in reverse order, from the edges in.

## Known limits

- **Every fight shows the same wounds in the same order.** A later fix is to offset the reveal by a
  low-frequency noise seeded per fight. Leave it until it bothers someone in play.
- **Blood ignores pose.** The trails run down in the rest pose. With her arms raised, the drips on
  her forearm point the wrong way. This is rarely visible on the legs and face, and noticeable on the arms.
- **Facial expressions stretch the face texture.** The split lip and nosebleed have only been checked
  on the neutral face, not under expressions.
- **The knees are already pink in the base texture**, so at 100% they can read as faintly scraped. That was a
  deliberate earlier choice (2026-10-23), and these wounds build on it.
- Untested in Unreal so far. Everything above was checked in Blender (EEVEE) with the same maths.
