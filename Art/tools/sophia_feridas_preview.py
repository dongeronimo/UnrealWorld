"""Blender: render Sophia at several HP values with the wound overlay, same logic as the Unreal material.
blender -b sophia_ruiva_preview.blend --python sophia_feridas_preview.py -- FERIDAS_DIR OUT_DIR [BODY_PNG] [HP,HP,..]
Leaves a .blend in OUT_DIR whose body material has an 'HP' value node, for scrubbing by hand."""
import bpy, sys, os, math
from mathutils import Vector
argv = sys.argv[sys.argv.index('--') + 1:]
FER, OUT = argv[0], argv[1]
BODY = argv[2] if len(argv) > 2 and argv[2] else 'D:/UnrealWorld/Art/Sophia_Body_Fishnet_rede_unhas.png'
HPS = [float(x) for x in argv[3].split(',')] if len(argv) > 3 else [1.0, 0.75, 0.5, 0.25, 0.0]
SOFT = 0.06
os.makedirs(OUT, exist_ok=True)
sc = bpy.context.scene
body = bpy.data.objects['Body_Rigged']; arm = body.parent
arm.data.pose_position = 'REST'

m = body.data.materials[0]; nt = m.node_tree; N = nt.nodes; L = nt.links
img = next(n for n in N if n.type == 'TEX_IMAGE'); bsdf = next(n for n in N if n.type == 'BSDF_PRINCIPLED')
img.image = bpy.data.images.load(BODY, check_existing=True)
uvn = N.new('ShaderNodeUVMap'); uvn.uv_map = 'Channel0'
def tex(name, cs):
    t = N.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(FER, name), check_existing=True)
    t.image.colorspace_settings.name = cs; L.new(uvn.outputs['UV'], t.inputs['Vector']); return t
tint = tex('Sophia_Feridas_Tint.png', 'sRGB'); mask = tex('Sophia_Feridas_Mask.png', 'Non-Color'); nrm = tex('Sophia_Feridas_Normal.png', 'Non-Color')
L.new(uvn.outputs['UV'], img.inputs['Vector'])
hp = N.new('ShaderNodeValue'); hp.name = hp.label = 'HP'; hp.outputs[0].default_value = 1.0
sep = N.new('ShaderNodeSeparateColor'); L.new(mask.outputs['Color'], sep.inputs['Color'])
sub = N.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; L.new(sep.outputs['Red'], sub.inputs[0]); L.new(hp.outputs[0], sub.inputs[1])
div = N.new('ShaderNodeMath'); div.operation = 'DIVIDE'; div.use_clamp = True; L.new(sub.outputs[0], div.inputs[0]); div.inputs[1].default_value = SOFT
mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs['A'].default_value = (1, 1, 1, 1)
L.new(div.outputs[0], mix.inputs['Factor']); L.new(tint.outputs['Color'], mix.inputs['B'])
mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1
L.new(img.outputs['Color'], mul.inputs['A']); L.new(mix.outputs['Result'], mul.inputs['B'])
L.new(mul.outputs['Result'], bsdf.inputs['Base Color'])
wet = N.new('ShaderNodeMath'); wet.operation = 'MULTIPLY'; L.new(sep.outputs['Green'], wet.inputs[0]); L.new(div.outputs[0], wet.inputs[1])
rough = N.new('ShaderNodeMapRange'); rough.inputs['To Min'].default_value = 0.5; rough.inputs['To Max'].default_value = 0.12
L.new(wet.outputs[0], rough.inputs['Value']); L.new(rough.outputs['Result'], bsdf.inputs['Roughness'])
nmap = N.new('ShaderNodeNormalMap'); nmap.uv_map = 'Channel0'
L.new(nrm.outputs['Color'], nmap.inputs['Color']); L.new(div.outputs[0], nmap.inputs['Strength'])
L.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])

sc.render.engine = 'BLENDER_EEVEE_NEXT'
sc.eevee.taa_render_samples = 32
sc.render.film_transparent = False
sc.view_settings.view_transform = 'AgX'
if not any(o.type == 'LIGHT' and not o.hide_render for o in sc.objects):
    for name, rot, e in (('key', (55, 0, -30), 3.5), ('fill', (60, 0, 140), 1.5), ('rim', (70, 0, 200), 2.0)):
        ld = bpy.data.lights.new(name, 'SUN'); ld.energy = e
        lo = bpy.data.objects.new(name, ld); sc.collection.objects.link(lo); lo.rotation_euler = [math.radians(a) for a in rot]
if sc.world is None: sc.world = bpy.data.worlds.new('W')
sc.world.use_nodes = True; bg = sc.world.node_tree.nodes.get('Background')
if bg: bg.inputs['Color'].default_value = (0.25, 0.25, 0.27, 1); bg.inputs['Strength'].default_value = 0.6

cd = bpy.data.cameras.new('FerCam'); cam = bpy.data.objects.new('FerCam', cd); sc.collection.objects.link(cam); sc.camera = cam
def aim(pos, tgt, lens):
    cam.location = Vector(pos); cam.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler(); cd.lens = lens
CLOTH = ['Shirt', 'Skirt', 'Belt', 'Holster', 'Katana', 'Katana_Sheat', 'Pistol', 'Jacket', 'Boots', 'Choker']
def outfit(clothed):
    for nm in CLOTH:
        o = bpy.data.objects.get(nm)
        if o: o.hide_render = not clothed if nm != 'Jacket' else True
    for nm in ('Upper_Bikini', 'Lower_Bikini'):
        o = bpy.data.objects.get(nm)
        if o: o.hide_render = clothed if nm == 'Upper_Bikini' else False
VIEWS = {  # name: (camera pos, target, lens, w, h, clothed)
    'frente':  ((0, -3.2, 0.78), (0, 0, 0.76), 50, 360, 720, False),
    'costas':  ((0, 3.2, 0.78), (0, 0, 0.76), 50, 360, 720, False),
    'rosto':   ((0.12, -0.55, 1.39), (0, 0, 1.375), 85, 360, 360, False),
    'rosto_esq': ((0.45, -0.4, 1.40), (0, 0, 1.375), 85, 360, 360, False),
    'pernas':  ((0.25, -1.3, 0.55), (0, 0, 0.5), 60, 360, 480, False),
    'vestida': ((0, -3.2, 0.78), (0, 0, 0.76), 50, 360, 720, True),
}
for v, (pos, tgt, lens, w, h, cl) in VIEWS.items():
    outfit(cl); aim(pos, tgt, lens); sc.render.resolution_x = w; sc.render.resolution_y = h; sc.render.resolution_percentage = 100
    for x in HPS:
        hp.outputs[0].default_value = x
        sc.render.filepath = os.path.join(OUT, '%s_hp%03d.png' % (v, round(x * 100)))
        bpy.ops.render.render(write_still=True)
hp.outputs[0].default_value = 0.0; outfit(False)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'sophia_feridas_preview.blend'), copy=True)
print('PREVIEW DONE')
