"""Generates a character's post-process Control Rig from the recipes Blender exported, headless or in the editor.

    UnrealEditor-Cmd.exe UnrealWorld.uproject -run=pythonscript -script="Tools/gerar_control_rig.py RECIPES.json /Game/Path/Mesh /Game/Path/CR_Name"

RECIPES.json comes from gurps tools/blender/exportar_receitas.py: the table pele['corretivos'], which is
the only source of the recipes. Blender runs them as drivers; this script builds the same maths as
Control Rig nodes, so what plays in Unreal after aim offsets and foot IK matches what Blender shows.
Never hand-edit the generated graph: change the Blender script, export, and run this again. It clears
the rig's Forwards Solve graph and rebuilds it, so the asset (and the Anim Blueprint node pointing
at it) keeps its path.

Recipes built so far:
  torcao  bone local rotation = its initial local rotation * (fraction * twist of `fonte` about local Y,
          measured from `fonte`'s initial pose). Blender: torcao_coxa.py (SWING_TWIST_Y, LOCAL_SPACE).
Shape-key recipes (rows without 'tipo') are skipped and listed: they come next.

Node structs and pins checked against the UE 5.7 source (RigUnit_GetTransform.h, RigUnit_SetTransform.h,
RigVMFunction_MathQuaternion.h/.cpp): Make Relative is Parent^-1 * Global, To Swing & Twist projects the
vector part on the axis (same as Blender's swing-twist), To Axis And Angle returns radians in [-pi, pi].
The Dot against +Y puts the angle on the +Y convention, because To Axis And Angle may answer
"-a about -Y" for "+a about +Y".
"""
import json
import sys

import unreal

Y = "(X=0.000000,Y=1.000000,Z=0.000000)"
S_GET = "/Script/ControlRig.RigUnit_GetTransform"
S_SET_ROT = "/Script/ControlRig.RigUnit_SetRotation"
S_REL = "/Script/RigVM.RigVMFunction_MathQuaternionMakeRelative"
S_SWING = "/Script/RigVM.RigVMFunction_MathQuaternionSwingTwist"
S_AXANG = "/Script/RigVM.RigVMFunction_MathQuaternionToAxisAndAngle"
S_FROM = "/Script/RigVM.RigVMFunction_MathQuaternionFromAxisAndAngle"
S_QMUL = "/Script/RigVM.RigVMFunction_MathQuaternionMul"
S_DOT = "/Script/RigVM.RigVMFunction_MathVectorDot"
S_FMUL = "/Script/RigVM.RigVMFunction_MathFloatMul"
S_BEGIN = "/Script/ControlRig.RigUnit_BeginExecution"

assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)


def bone(name):
    return '(Type=Bone,Name="%s")' % name


class Graph:
    def __init__(self, bp):
        self.bp = bp
        self.c = bp.get_controller_by_name("RigVMModel")
        if self.c is None:
            raise RuntimeError("no RigVMModel graph in " + bp.get_path_name())
        self.n = 0
        self.last_exec = None

    def node(self, struct, x, y, **defaults):
        self.n += 1
        node = self.c.add_unit_node_from_struct_path(struct, "Execute", unreal.Vector2D(x, y), "n%03d" % self.n)
        if node is None:
            raise RuntimeError("could not add " + struct)
        name = node.get_name()
        for pin, value in defaults.items():
            if not self.c.set_pin_default_value("%s.%s" % (name, pin), value, True, False):
                raise RuntimeError("could not set %s.%s = %s" % (name, pin, value))
        return name

    def link(self, a, b):
        if not self.c.add_link(a, b, False):
            raise RuntimeError("could not link %s -> %s" % (a, b))

    def exec_pin(self, name):
        node = self.c.get_graph().find_node_by_name(name)
        for p in node.get_pins():
            if p.is_execute_context():
                return "%s.%s" % (name, p.get_name())
        raise RuntimeError("no execute pin on " + name)

    def chain(self, name):
        self.link(self.last_exec, self.exec_pin(name))
        self.last_exec = self.exec_pin(name)

    def clear(self):
        """Removes every node except the Forwards Solve event; returns the event's execute pin."""
        graph = self.c.get_graph()
        begin = None
        for node in list(graph.get_nodes()):
            if isinstance(node, unreal.RigVMUnitNode) and node.get_script_struct().get_name() == "RigUnit_BeginExecution":
                begin = node.get_name()
            else:
                self.c.remove_node(node, False)
        if begin is None:
            begin = self.c.add_unit_node_from_struct_path(S_BEGIN, "Execute", unreal.Vector2D(-400, 0), "Begin").get_name()
        self.last_exec = self.exec_pin(begin)


def twist_angle(g, fonte, y):
    """Signed twist of `fonte` about local +Y, from its initial pose, in radians. Returns the output pin."""
    now = g.node(S_GET, 0, y, Item=bone(fonte), Space="LocalSpace", bInitial="False")
    rest = g.node(S_GET, 0, y + 200, Item=bone(fonte), Space="LocalSpace", bInitial="True")
    rel = g.node(S_REL, 300, y)
    g.link(now + ".Transform.Rotation", rel + ".Global")
    g.link(rest + ".Transform.Rotation", rel + ".Parent")
    sw = g.node(S_SWING, 550, y, TwistAxis=Y)
    g.link(rel + ".Local", sw + ".Input")
    aa = g.node(S_AXANG, 800, y)
    g.link(sw + ".Twist", aa + ".Value")
    dot = g.node(S_DOT, 1050, y + 120, B=Y)
    g.link(aa + ".Axis", dot + ".A")
    ang = g.node(S_FMUL, 1250, y)
    g.link(aa + ".Angle", ang + ".A")
    g.link(dot + ".Result", ang + ".B")
    return ang + ".Result"


def apply_twist(g, osso, angle_pin, fraction, x, y):
    k = g.node(S_FMUL, x, y, B="%.6f" % fraction)
    g.link(angle_pin, k + ".A")
    q = g.node(S_FROM, x + 200, y, Axis=Y)
    g.link(k + ".Result", q + ".Angle")
    rest = g.node(S_GET, x + 200, y + 200, Item=bone(osso), Space="LocalSpace", bInitial="True")
    mul = g.node(S_QMUL, x + 450, y)
    g.link(rest + ".Transform.Rotation", mul + ".A")
    g.link(q + ".Result", mul + ".B")
    # bPropagateToChildren: Twist02 is Twist01's child and must ride along, as in Blender
    st = g.node(S_SET_ROT, x + 700, y, Item=bone(osso), Space="LocalSpace", bInitial="False",
                Weight="1.000000", bPropagateToChildren="True")
    g.link(mul + ".Result", st + ".Value")
    g.chain(st)


def main(recipes_path, mesh_path, cr_path):
    with open(recipes_path, encoding="utf-8") as f:
        rows = json.load(f)["linhas"]
    mesh = assets.load_asset(mesh_path)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError("not a skeletal mesh: " + mesh_path)

    bp = assets.load_asset(cr_path) if assets.does_asset_exist(cr_path) else None
    if bp is None:
        bp = unreal.ControlRigBlueprintFactory.create_new_control_rig_asset(cr_path)
        if bp is None:
            raise RuntimeError("could not create " + cr_path)
    unreal.log("gerar_control_rig: asset %s" % bp.get_path_name())
    hc = bp.get_hierarchy_controller()
    hc.import_bones_from_skeletal_mesh(mesh, "None", True, True, False, False, False)
    unreal.log("gerar_control_rig: bones imported")
    hc.import_curves_from_skeletal_mesh(mesh, "None", False, False, False)
    unreal.log("gerar_control_rig: curves imported")
    bp.set_preview_mesh(mesh, True)
    unreal.log("gerar_control_rig: preview mesh set")

    g = Graph(bp)
    g.clear()
    twists = [r for r in rows if r.get("tipo") == "torcao"]
    skipped = [r["chave"] for r in rows if r.get("tipo") != "torcao"]
    by_source = {}
    for r in twists:
        if r["eixo"] != "twist_y_local":
            raise RuntimeError("unsupported axis %s in %s" % (r["eixo"], r["chave"]))
        by_source.setdefault(r["fonte"], []).append(r)
    y = 0
    for fonte, rs in by_source.items():
        angle = twist_angle(g, fonte, y)
        # parent before child: Twist01 before Twist02 (both read their own initial pose, so the order
        # only matters for the propagation to children)
        rs.sort(key=lambda r: r["osso"])
        for i, r in enumerate(rs):
            apply_twist(g, r["osso"], angle, r["fracao_local"], 1500 + 1100 * i, y)
        y += 500
    bp.recompile_vm()
    assets.save_loaded_asset(bp)
    unreal.log("gerar_control_rig: %s, %d twist recipes from %d sources, %d nodes; skipped %d shape-key rows"
               % (cr_path, len(twists), len(by_source), g.n, len(skipped)))


args = [a for a in sys.argv[1:] if not a.startswith("-")]
if len(args) < 3:
    raise RuntimeError("usage: gerar_control_rig.py RECIPES.json /Game/Path/Mesh /Game/Path/CR_Name")
main(args[0], args[1], args[2])
