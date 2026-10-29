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
  chaves  one curve per Blender shape-key driver (the 'chaves' list): the driver's own expression,
          compiled to float nodes (+ - * /, min, max, clamp), over swing-twist channels of local bones
          (ROT_X/ROT_Z = 2 asin of the swing quaternion's x/z, ROT_Y = the twist angle, all from the
          bone's initial pose, radians: Blender's SWING_TWIST_Y, measured) and constants (a SINGLE_PROP like the muscle strength, exported as
          its value). Set Curve Value writes the curve the morph target of the same name reads.

Blender to Unreal flips Y (FBX import), and conjugating by that mirror negates the swing's X and Z
components and keeps the twist about Y: SINAL below. The parity test is what proves it.

Node structs and pins checked against the UE 5.7 source (RigUnit_GetTransform.h, RigUnit_SetTransform.h,
RigVMFunction_MathQuaternion.h/.cpp): Make Relative is Parent^-1 * Global, To Swing & Twist projects the
vector part on the axis (same as Blender's swing-twist), To Axis And Angle returns radians in [-pi, pi].
The Dot against +Y puts the angle on the +Y convention, because To Axis And Angle may answer
"-a about -Y" for "+a about +Y".
"""
import ast
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
S_SET_CURVE = "/Script/ControlRig.RigUnit_SetCurveValue"
S_FADD = "/Script/RigVM.RigVMFunction_MathFloatAdd"
S_FSUB = "/Script/RigVM.RigVMFunction_MathFloatSub"
S_FDIV = "/Script/RigVM.RigVMFunction_MathFloatDiv"
S_FMIN = "/Script/RigVM.RigVMFunction_MathFloatMin"
S_FMAX = "/Script/RigVM.RigVMFunction_MathFloatMax"
S_FCLAMP = "/Script/RigVM.RigVMFunction_MathFloatClamp"
S_FSIN = "/Script/RigVM.RigVMFunction_MathFloatSin"
S_FASIN = "/Script/RigVM.RigVMFunction_MathFloatAsin"
X = "(X=1.000000,Y=0.000000,Z=0.000000)"
Z = "(X=0.000000,Y=0.000000,Z=1.000000)"
SINAL = {"ROT_X": -1.0, "ROT_Z": -1.0, "ROT_Y": 1.0}

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
        node = self.c.add_unit_node_from_struct_path(struct, "Execute", unreal.Vector2D(x, y), "n%04d" % self.n)
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


class Canais:
    """Swing-twist channels of local bones, built once per bone and shared by every curve."""
    def __init__(self, g):
        self.g, self.rel, self.pin, self.y = g, {}, {}, 0

    def _rel(self, osso):
        if osso not in self.rel:
            y = self.y = self.y + 400
            now = self.g.node(S_GET, 0, 20000 + y, Item=bone(osso), Space="LocalSpace", bInitial="False")
            rest = self.g.node(S_GET, 0, 20200 + y, Item=bone(osso), Space="LocalSpace", bInitial="True")
            rel = self.g.node(S_REL, 300, 20000 + y)
            self.g.link(now + ".Transform.Rotation", rel + ".Global")
            self.g.link(rest + ".Transform.Rotation", rel + ".Parent")
            sw = self.g.node(S_SWING, 550, 20000 + y, TwistAxis=Y)
            self.g.link(rel + ".Local", sw + ".Input")
            self.rel[osso] = (sw, y)
        return self.rel[osso]

    def canal(self, osso, canal):
        k = (osso, canal)
        if k in self.pin:
            return self.pin[k]
        sw, y = self._rel(osso)
        parte, eixo = ("Twist", Y) if canal == "ROT_Y" else ("Swing", X if canal == "ROT_X" else Z)
        aa = self.g.node(S_AXANG, 800, 20000 + y + (0 if canal == "ROT_X" else 120))
        self.g.link(sw + "." + parte, aa + ".Value")
        dot = self.g.node(S_DOT, 1050, 20000 + y, B=eixo)
        self.g.link(aa + ".Axis", dot + ".A")
        if canal == "ROT_Y":
            # the twist: Blender gives the angle itself (signed by the Dot)
            ang = self.g.node(S_FMUL, 1250, 20000 + y)
            self.g.link(aa + ".Angle", ang + ".A")
            self.g.link(dot + ".Result", ang + ".B")
        else:
            # the swing: Blender gives 2 asin(q.x) / 2 asin(q.z) of the swing quaternion, not the
            # axis-angle component (measured: swing (90, 45) deg reads 1.518 / 0.703, not 1.571 / 0.785).
            # q.x = sin(angle / 2) * axis.x, and To Axis And Angle answers with w >= 0 (angle in [-pi, pi])
            meio = self.g.node(S_FMUL, 1050, 20000 + y + 60, B="0.500000")
            self.g.link(aa + ".Angle", meio + ".A")
            sen = self.g.node(S_FSIN, 1200, 20000 + y + 60)
            self.g.link(meio + ".Result", sen + ".Value")
            comp = self.g.node(S_FMUL, 1350, 20000 + y)
            self.g.link(sen + ".Result", comp + ".A")
            self.g.link(dot + ".Result", comp + ".B")
            asen = self.g.node(S_FASIN, 1500, 20000 + y)
            self.g.link(comp + ".Result", asen + ".Value")
            ang = self.g.node(S_FMUL, 1650, 20000 + y, B="2.000000")
            self.g.link(asen + ".Result", ang + ".A")
        if SINAL[canal] != 1.0:
            m = self.g.node(S_FMUL, 1450, 20000 + y, B="%.1f" % SINAL[canal])
            self.g.link(ang + ".Result", m + ".A")
            ang = m
        self.pin[k] = ang + ".Result"
        return self.pin[k]


def compilar(g, expr, variaveis, canais, x, y):
    """The driver expression as float nodes. Returns an output pin, or a float when it is constant."""
    def val(n):
        if isinstance(n, ast.Constant):
            return float(n.value)
        if isinstance(n, ast.Name):
            v = variaveis[n.id]
            return v["valor"] if "valor" in v else canais.canal(v["osso"], v["canal"])
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            a = val(n.operand)
            return -a if isinstance(a, float) else op(S_FMUL, a, -1.0)
        if isinstance(n, ast.BinOp):
            s_ = {ast.Add: S_FADD, ast.Sub: S_FSUB, ast.Mult: S_FMUL, ast.Div: S_FDIV}[type(n.op)]
            a, b = val(n.left), val(n.right)
            if isinstance(a, float) and isinstance(b, float):
                return {S_FADD: a + b, S_FSUB: a - b, S_FMUL: a * b, S_FDIV: a / b}[s_]
            return op(s_, a, b)
        if isinstance(n, ast.Call) and n.func.id in ("min", "max"):
            r = val(n.args[0])
            for arg in n.args[1:]:
                r = op(S_FMIN if n.func.id == "min" else S_FMAX, r, val(arg))
            return r
        if isinstance(n, ast.Call) and n.func.id == "clamp":
            v, lo, hi = (val(a) for a in n.args)
            c = g.node(S_FCLAMP, x, y)
            for pin, a in (("Value", v), ("Minimum", lo), ("Maximum", hi)):
                feed(a, c + "." + pin)
            return c + ".Result"
        raise RuntimeError("expression not supported: %s" % ast.dump(n))

    def feed(a, pin):
        if isinstance(a, float):
            if not g.c.set_pin_default_value(pin, "%.6f" % a, True, False):
                raise RuntimeError("could not set " + pin)
        else:
            g.link(a, pin)

    def op(s_, a, b):
        n = g.node(s_, x, y)
        feed(a, n + ".A"); feed(b, n + ".B")
        return n + ".Result"

    return val(ast.parse(expr, mode="eval").body)


def main(recipes_path, mesh_path, cr_path):
    with open(recipes_path, encoding="utf-8") as f:
        receitas = json.load(f)
    rows = receitas["linhas"]
    curvas = receitas.get("chaves", [])
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
    # curvas: a hierarquia precisa ter a curva para o Set Curve Value escrever nela
    h = hc.get_hierarchy()
    tem = {str(k.name) for k in h.get_all_keys(True) if k.type == unreal.RigElementType.CURVE}
    novas = [c["chave"] for c in curvas if c["chave"] not in tem]
    for n in novas:
        hc.add_curve(n, 0.0, False, False)
    canais = Canais(g)
    for i, c in enumerate(curvas):
        v = compilar(g, c["expr"], c["var"], canais, 2000, 20000 + 200 * i)
        st = g.node(S_SET_CURVE, 2600, 20000 + 200 * i, Curve=c["chave"])
        if isinstance(v, float):
            g.c.set_pin_default_value(st + ".Value", "%.6f" % v, True, False)
        else:
            g.link(v, st + ".Value")
        g.chain(st)
    bp.recompile_vm()
    assets.save_loaded_asset(bp)
    unreal.log("gerar_control_rig: %s, %d twist recipes from %d sources, %d curves (%d added to the hierarchy), %d nodes"
               % (cr_path, len(twists), len(by_source), len(curvas), len(novas), g.n))


args = [a for a in sys.argv[1:] if not a.startswith("-")]
if len(args) < 3:
    raise RuntimeError("usage: gerar_control_rig.py RECIPES.json /Game/Path/Mesh /Game/Path/CR_Name")
main(args[0], args[1], args[2])
