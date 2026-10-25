"""Sophia's wound overlay: the 0 HP look plus a per-texel reveal threshold, so one HP scalar drives it.

python sophia_feridas.py feridas/body.npz feridas/        (body.npz from sophia_feridas_dump.py)

Outputs (4096, body UV 'Channel0'):
  Sophia_Feridas_Tint.png    RGB multiply tint, white = untouched (sRGB). Multiply, not lerp, so the
                             baked fishnet and the redhead alt stay under the wounds with no extra copy.
  Sophia_Feridas_Mask.png    R reveal: HP fraction at which the texel starts to show (linear)
                             G wetness (blood, open cuts: lower roughness)
                             B height, 0.5 = flat (only the source of the normal map)
  Sophia_Feridas_Normal.png  tangent normal from the height, OpenGL (Unreal: flip green)
  Sophia_Body_Feridas_0HP.png main body texture at 0 HP, for eyeballing only

Shader: vis = saturate((reveal - HP) / SOFT); albedo *= lerp(1, tint, vis).
Every wound is placed and grown in 3D (rest pose), so UV seams do not cut them.
Each wound reveals from its centre outwards, so it grows as HP drops instead of popping in.
To retune: edit the WOUNDS section at the bottom and run again.
"""
import numpy as np, sys, time
from PIL import Image
from scipy.spatial import cKDTree
from scipy import ndimage

DUMP, OUT = sys.argv[1], sys.argv[2].rstrip('/\\') + '/'
BASE = sys.argv[3] if len(sys.argv) > 3 else 'D:/UnrealWorld/Art/Sophia_Body_Fishnet_rede_unhas.png'
N = 4096
SOFT = 0.06            # must match the material
SIZE = 1.5             # wounds are drawn bigger than life so they read at game-camera distance
T0 = time.time()
def log(*a): print('[%5.1fs]' % (time.time() - T0), *a, flush=True)

d = np.load(DUMP); co = d['co']; nr = d['nr']; tri = d['tri']; tuv = d['tuv']
B = dict(zip(d['bnames'], d['bpos'])); bone = lambda n: B[n + '|h']

# ---------------------------------------------------------------- raster: texel -> triangle + barycentric
P2 = tuv * N; P2[:, :, 1] = N - P2[:, :, 1]
TID = np.full((N, N), -1, np.int32); BAR = np.zeros((N, N, 3), np.float32)
A3 = 0.5 * np.linalg.norm(np.cross(co[tri[:, 1]] - co[tri[:, 0]], co[tri[:, 2]] - co[tri[:, 0]]), axis=1)
e1 = P2[:, 1] - P2[:, 0]; e2 = P2[:, 2] - P2[:, 0]; A2 = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
PXM = np.sqrt(A2 / np.maximum(A3, 1e-12))      # texels per metre, per triangle
for t in range(len(tri)):
    p = P2[t]
    x0, y0 = np.maximum(np.floor(p.min(0)).astype(int) - 1, 0); x1, y1 = np.minimum(np.ceil(p.max(0)).astype(int) + 1, N - 1)
    if x1 < x0 or y1 < y0: continue
    xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
    a, b, c = p; v0 = b - a; v1 = c - a; den = v0[0] * v1[1] - v1[0] * v0[1]
    if abs(den) < 1e-9: continue
    wx = xs - a[0]; wy = ys - a[1]
    l1 = (wx * v1[1] - v1[0] * wy) / den; l2 = (v0[0] * wy - wx * v0[1]) / den; l0 = 1 - l1 - l2
    e = -0.6 * np.sqrt(v0 @ v0 + v1 @ v1) / abs(den)
    m = (l0 >= e) & (l1 >= e) & (l2 >= e)
    sl = (slice(y0, y1 + 1), slice(x0, x1 + 1))
    TID[sl][m] = t; BAR[sl][m] = np.clip(np.stack([l0, l1, l2], -1)[m], 0, 1)
valid = TID >= 0
VY, VX = np.nonzero(valid); TV = TID[VY, VX]; BV = BAR[VY, VX]; BV /= BV.sum(1, keepdims=True)
POS = np.einsum('kj,kjc->kc', BV, co[tri[TV]])
NRM = np.einsum('kj,kjc->kc', BV, nr[tri[TV]]); NRM /= np.linalg.norm(NRM, axis=1, keepdims=True) + 1e-12
HAIR = np.einsum('kj,kj->k', BV, d['hair'][tri[TV]])
K = len(POS); log('texels', K)
tree = cKDTree(POS)

# keep: no wounds on hair (hair, brows and skin share the texture) or on the painted eyes
keep = 1 - np.clip(HAIR * 3, 0, 1)
for s in 'LR':
    e = bone('CC_Base_%s_Eye' % s); q = (POS - (e + [0, -0.012, 0.001])) / [0.0125, 0.012, 0.0065]
    keep *= np.clip((np.linalg.norm(q, axis=1) - 1) / 0.35, 0, 1)

# ---------------------------------------------------------------- outputs, per valid texel
TINT = np.ones((K, 3)); REV = np.zeros(K); DOM = np.zeros(K); WET = np.zeros(K); HGT = np.zeros(K)

def apply(idx, a, col, rev, wet=0.0, h=0.0):
    """Multiply-composite one layer. The texel's reveal follows its strongest layer."""
    a = np.clip(a * keep[idx], 0, 1); col = np.broadcast_to(np.asarray(col, float), (len(idx), 3))
    rev = np.broadcast_to(np.asarray(rev, float), (len(idx),))
    TINT[idx] *= 1 - a[:, None] * (1 - col)
    w = a > DOM[idx]; REV[idx[w]] = rev[w]; DOM[idx[w]] = a[w]
    WET[idx] = np.maximum(WET[idx], a * wet); HGT[idx] += a * h

# ---------------------------------------------------------------- 3D value noise
_r = np.random.default_rng(1234); PERM = np.tile(_r.permutation(256), 2); GR = _r.random(256)
def vnoise(p):
    i = np.floor(p).astype(np.int64); f = p - i; u = f * f * (3 - 2 * f)
    def h(dx, dy, dz): return GR[PERM[PERM[PERM[(i[:, 0] + dx) & 255] + ((i[:, 1] + dy) & 255)] + ((i[:, 2] + dz) & 255)]]
    x00 = h(0,0,0)*(1-u[:,0]) + h(1,0,0)*u[:,0]; x10 = h(0,1,0)*(1-u[:,0]) + h(1,1,0)*u[:,0]
    x01 = h(0,0,1)*(1-u[:,0]) + h(1,0,1)*u[:,0]; x11 = h(0,1,1)*(1-u[:,0]) + h(1,1,1)*u[:,0]
    return (x00*(1-u[:,1]) + x10*u[:,1])*(1-u[:,2]) + (x01*(1-u[:,1]) + x11*u[:,1])*u[:,2]
def fbm(p, f, oct=3):
    s = 0; a = 0.5; t = 0
    for o in range(oct): s += a * vnoise(p * f * 2 ** o + 17.3 * o); t += a; a *= 0.5
    return s / t
def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)

# ---------------------------------------------------------------- surface queries (rest-pose mesh)
V0 = co[tri[:, 0]]; E1 = co[tri[:, 1]] - V0; E2 = co[tri[:, 2]] - V0
SKIN = d['hair'][tri].max(1) < 0.15     # rays ignore hair cards, or face wounds land on the hair framing it
def ray(o, dv):
    o = np.asarray(o, float); dv = np.asarray(dv, float); dv = dv / np.linalg.norm(dv)
    h = np.cross(dv, E2); a = (E1 * h).sum(1); ok = np.abs(a) > 1e-14
    f = 1 / np.where(ok, a, 1); s = o - V0; u = f * (s * h).sum(1); q = np.cross(s, E1)
    v = f * (q @ dv); t = f * (E2 * q).sum(1)
    m = ok & SKIN & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-7)
    if not m.any(): return None
    i = np.argmin(np.where(m, t, np.inf)); b = np.array([1 - u[i] - v[i], u[i], v[i]])
    n = b @ nr[tri[i]]; return o + t[i] * dv, n / np.linalg.norm(n)
def surf(anchor, out):
    """Outermost surface point seen from `anchor + out`, looking back along -out."""
    out = np.asarray(out, float); out = out / np.linalg.norm(out)
    r = ray(np.asarray(anchor, float) + out * 0.4, -out)
    if r is None: raise RuntimeError('no surface at %s %s' % (anchor, out))
    return r
def march(p, n, dirv, length, step=0.0015, wobble=0.0, seed=0, gravity=False):
    """Walk along the surface. gravity=True follows -Z and stops where blood would drip off or pool."""
    rng = np.random.default_rng(seed); pts = [p]; ns = [n]; L = 0
    ph, fq = rng.uniform(0, 6.3), rng.uniform(60, 110)
    dirv = None if dirv is None else np.asarray(dirv, float)
    while L < length:
        g = np.array([0, 0, -1.]) if gravity else dirv
        t = g - (g @ n) * n; tl = np.linalg.norm(t)
        if gravity and L > 0.008 and (n[2] < -0.55 or tl < 0.35): break
        if tl < 1e-6: t = np.cross(n, [1, 0, 0]); tl = np.linalg.norm(t)
        t /= tl
        if gravity: t = t + 0.2 * np.sin(L * fq + ph) * np.cross(n, t); t /= np.linalg.norm(t)
        if wobble:
            th = rng.normal(0, wobble); t = t * np.cos(th) + np.cross(n, t) * np.sin(th)
        r = ray(p + t * step + n * 0.004, -n)
        if r is None or np.linalg.norm(r[0] - p) > step * 3: break
        p, n = r; pts.append(p); ns.append(n); L += step
    return np.array(pts), np.array(ns)

def near(c, R):
    return np.array(tree.query_ball_point(c, R), dtype=np.int64)
def poly_dist(pts, ns, reach):
    """Texels near a surface polyline: (idx, distance, arc parameter 0..1). Gated by normals, so a
    wound on one lip or finger does not print through onto the facing one."""
    c = pts.mean(0); R = np.linalg.norm(pts - c, axis=1).max() + reach
    idx = near(c, R)
    if len(idx) == 0: return idx, np.zeros(0), np.zeros(0)
    P = POS[idx]; A = pts[:-1]; Bp = pts[1:]; AB = Bp - A; ll = (AB * AB).sum(1) + 1e-12
    seg = np.cumsum(np.r_[0, np.sqrt(ll)]); tot = seg[-1] + 1e-12
    best = np.full(len(idx), np.inf); par = np.zeros(len(idx)); bn = np.zeros((len(idx), 3))
    for j in range(len(A)):
        t = np.clip(((P - A[j]) @ AB[j]) / ll[j], 0, 1); q = A[j] + t[:, None] * AB[j]
        dd = np.linalg.norm(P - q, axis=1); w = dd < best
        best[w] = dd[w]; par[w] = (seg[j] + t[w] * np.sqrt(ll[j])) / tot; bn[w] = ns[j]
    g = (NRM[idx] * bn).sum(1) > 0.25
    m = (best < reach) & g
    return idx[m], best[m], par[m]

# ---------------------------------------------------------------- wound types
# colours are multiply tints on pale skin
BRUISE_C = np.array([0.40, 0.24, 0.40]); BRUISE_E = np.array([0.78, 0.50, 0.56])
BLOOD = np.array([0.42, 0.035, 0.045]); BLOOD_DRY = np.array([0.30, 0.04, 0.04])
CUT_CORE = np.array([0.26, 0.02, 0.03]); CUT_RIM = np.array([0.93, 0.66, 0.68])
RAW = np.array([0.80, 0.40, 0.40])
STATS = []

def bruise(name, p, n, r, rev, strength=0.95, centre=BRUISE_C, edge=BRUISE_E, seed=0, ring=0.0):
    r *= SIZE; ring *= SIZE
    idx = near(p, r * 1.5)
    D = POS[idx] - p; dist = np.linalg.norm(D, axis=1)
    nz = fbm(POS[idx] + seed, 90.0)
    q = dist / r * (0.8 + 0.5 * nz)
    a = strength * (1 - ss(0.25, 1.0, q)) * ss(0.0, 0.5, NRM[idx] @ n)
    if ring: a *= ss(0, ring, dist)      # black eye: darkest around the socket, not on it
    a *= 0.75 + 0.5 * fbm(POS[idx] + seed + 5, 260.0)
    t = np.clip(q, 0, 1)[:, None]; col = centre * (1 - t) + edge * t
    apply(idx, a, col, rev - 0.14 * np.clip(q, 0, 1)); STATS.append((name, int((a > 0.05).sum())))

def scrape(name, p, n, size, dirv, rev, strength=0.9, seed=0):
    """Abrasion: streaks along dirv, raw skin with pin-point blood."""
    size = (size[0] * SIZE, size[1] * SIZE)
    idx = near(p, max(size) * 1.4)
    t = np.asarray(dirv, float); t = t - (t @ n) * n; t /= np.linalg.norm(t); b = np.cross(n, t)
    D = POS[idx] - p; u = D @ t / size[0]; v = D @ b / size[1]
    q = np.sqrt(u * u + v * v) * (0.8 + 0.45 * fbm(POS[idx] + seed, 110.0))
    streak = vnoise(np.stack([u * 3.0, v * 55.0, np.full_like(u, seed * 1.7)], 1))
    a = strength * (1 - ss(0.35, 1.0, q)) * (0.45 + 0.55 * streak) * ss(0.0, 0.5, NRM[idx] @ n)
    apply(idx, a, RAW, rev - 0.12 * np.clip(q, 0, 1), wet=0.25, h=-0.00008)
    dots = ss(0.72, 0.85, vnoise(POS[idx] * 1400 + seed)) * (1 - ss(0.2, 0.8, q)) * (0.4 + 0.6 * streak)
    apply(idx, dots * 0.9, BLOOD, rev - 0.06 - 0.12 * np.clip(q, 0, 1), wet=0.7, h=0.00005)
    STATS.append((name, int((a > 0.05).sum())))

def drip(name, p, n, length, rev, width=0.0016, seed=0, span=0.22):
    width *= SIZE; length *= SIZE
    pts, ns = march(p, n, None, length, wobble=0.12, seed=seed, gravity=True)
    if len(pts) < 3: STATS.append((name, 0)); return
    idx, dist, s = poly_dist(pts, ns, width * 2.5)
    hw = width * (1.5 - 0.8 * s) * (0.6 + 0.8 * vnoise(np.c_[s * 9, np.full_like(s, seed + 0.5), s]))
    a = 1 - ss(0.55, 1.0, dist / hw)
    apply(idx, a, BLOOD * (1 - s[:, None] * 0.25) + BLOOD_DRY * s[:, None] * 0.25,
          rev - span * s, wet=0.85, h=0.00012)
    # the drop where it stopped
    e = pts[-1]; i2 = near(e, width * 2.2); dd = np.linalg.norm(POS[i2] - e, axis=1)
    apply(i2, (1 - ss(0.6, 1.0, dd / (width * 1.5))) * ss(0, 0.5, NRM[i2] @ ns[-1]), BLOOD, rev - span, wet=0.9, h=0.00015)
    STATS.append((name, len(idx)))

def cut(name, p, n, dirv, length, rev, width=0.0011, bleed=(), seed=0, drip_len=0.08):
    """A slash along dirv on the surface, centred on p; bleed = arc positions (0..1) that run blood."""
    width *= SIZE * 1.8; length *= SIZE
    a_, an = march(p, n, -np.asarray(dirv, float), length / 2, step=0.001)
    b_, bn = march(p, n, dirv, length / 2, step=0.001)
    pts = np.r_[a_[::-1], b_[1:]]; ns = np.r_[an[::-1], bn[1:]]
    idx, dist, s = poly_dist(pts, ns, width * 4.5)
    prof = np.sin(np.pi * np.clip(s, 0, 1)) ** 0.6
    jag = 0.8 + 0.4 * vnoise(np.c_[s * 25, np.full_like(s, seed), dist * 0])
    hw = width * prof * jag + 1e-6
    core = 1 - ss(0.6, 1.0, dist / hw)
    rim = (1 - ss(1.0, 3.6, dist / hw)) * (1 - core) * prof
    grow = rev - 0.10 * np.abs(2 * s - 1)          # opens from the middle out to the ends
    apply(idx, rim * 0.8, CUT_RIM, grow, h=0.00012)
    i2, d2, s2 = poly_dist(pts, ns, width * 9)
    haze = (1 - ss(0.0, 1.0, d2 / (width * 9))) * np.sin(np.pi * s2) ** 0.5 * ss(0.3, 0.8, fbm(POS[i2] + seed, 160.0))
    apply(i2, haze * 0.45, BLOOD, rev - 0.06 - 0.12 * d2 / (width * 9), wet=0.4)
    apply(idx, core, CUT_CORE, grow, wet=1.0, h=-0.0005)
    for k, sb in enumerate(bleed):
        j = min(int(sb * (len(pts) - 1)), len(pts) - 1)
        drip(name + '/drip%d' % k, pts[j], ns[j], drip_len * 1.5, rev - 0.04, seed=seed * 7 + k, width=width / SIZE)
    STATS.append((name, len(idx)))

def grime(rev_hi=0.92, rev_lo=0.45):
    """Dirt and sweat over the skin: broad, faint, first thing to show."""
    idx = np.arange(K)
    nz = fbm(POS, 9.0, 4); low = ss(0.75, 0.15, POS[:, 2])           # more on the shins and feet
    hands = sum(np.exp(-np.sum((POS - bone('CC_Base_%s_Mid1' % s)) ** 2, 1) / 0.05 ** 2) for s in 'LR')
    a = (0.10 + 0.25 * low + 0.25 * np.clip(hands, 0, 1)) * ss(0.35, 0.75, nz)
    a *= 0.6 + 0.4 * fbm(POS + 3, 70.0)
    apply(idx, a, np.array([0.80, 0.74, 0.68]), rev_hi - (rev_hi - rev_lo) * (1 - nz), wet=0.0)

# ---------------------------------------------------------------- WOUNDS
# Front is -Y, Sophia's left is +X. Reveal r = HP fraction at which a wound starts showing:
# 0.85 grime and knuckles, 0.7 bruises, 0.55 lip and scrapes, 0.4 brow cut and leg cuts,
# 0.25 nosebleed and deep cuts, 0.15 the last of it. Ceiling: action film, not horror.
FWD = (0, -1, 0); BACK = (0, 1, 0); UP = (0, 0, 1); DOWN = (0, 0, -1)
grime()
for s, sx in (('L', 1), ('R', -1)):
    for f in ('Index', 'Mid', 'Ring', 'Pinky'):
        k = bone('CC_Base_%s_%s1' % (s, f))
        p, n = surf(k, (sx, 0, 0.15))
        bruise('knuckle_%s_%s' % (s, f), p, n, 0.009, 0.86 if f in ('Index', 'Mid') else 0.74, 0.75, seed=sum(map(ord, s + f)) % 97)
    scrape('knuckles_%s' % s, *surf(bone('CC_Base_%s_Mid1' % s) + [0, 0, 0.006], (sx, 0, 0.15)), (0.012, 0.022), UP, 0.62, 0.6, seed=3 if s == 'L' else 4)

p, n = surf((0.032, 0, 1.380), (0.3, -1, 0)); bruise('cheek_L', p, n, 0.015, 0.72, seed=11)   # her left side is under the hair
p, n = surf((-0.026, 0, 1.393), FWD); bruise('black_eye_R', p, n, 0.024, 0.38, 0.95, seed=12, ring=0.014,
                                            centre=np.array([0.40, 0.27, 0.42]))
p, n = surf((0.016, 0, 1.432), (0.1, -1, 0.2)); cut('brow_L', p, n, (1, 0.1, 0.6), 0.014, 0.42, width=0.0009, bleed=(0.7,), seed=13, drip_len=0.07)
p, n = surf((-0.009, 0, 1.351), FWD); bruise('lip_swell', p, n, 0.008, 0.58, 0.6, seed=14)
cut('lip_split', p, n, (0.25, 0, 1), 0.006, 0.56, width=0.0007, bleed=(0.1,), seed=15, drip_len=0.045)
p, n = surf((0.005, 0, 1.366), FWD); drip('nosebleed', p, n, 0.06, 0.26, width=0.0017, seed=16)
p, n = surf((-0.05, 0, 1.372), (-0.6, -1, 0)); cut('cheek_R', p, n, (1, 0, -0.6), 0.022, 0.18, width=0.0008, bleed=(0.85,), seed=17, drip_len=0.05)
p, n = surf((0.0, 0, 1.322), FWD); scrape('chin', p, n, (0.010, 0.007), (1, 0, 0), 0.30, 0.7, seed=18)

p, n = surf((-0.075, 0, 1.215), FWD); scrape('collarbone_R', p, n, (0.025, 0.012), (1, 0, -0.3), 0.50, seed=19)
p, n = surf((0.04, 0, 1.275), (0.6, -1, 0)); bruise('neck_L', p, n, 0.015, 0.45, 0.6, seed=20)
p, n = surf((0.125, 0.0, 1.07), (1, 0, 0)); bruise('ribs_L', p, n, 0.035, 0.66, seed=21)
p, n = surf((-0.06, 0, 0.99), (-0.4, -1, 0)); cut('flank_R', p, n, (1, 0, 0.3), 0.06, 0.24, bleed=(0.3, 0.75), seed=22, drip_len=0.09)
p, n = surf((0.08, 0, 1.15), BACK); bruise('shoulderblade_L', p, n, 0.04, 0.6, 0.7, seed=23)
p, n = surf((0.045, 0, 1.0), FWD); bruise('belly_L', p, n, 0.03, 0.52, 0.8, seed=24)
p, n = surf((-0.03, 0, 1.06), FWD); cut('belly_R', p, n, (1, 0, -0.5), 0.05, 0.30, bleed=(0.5,), seed=25, drip_len=0.08)
p, n = surf((0.165, 0, 1.17), (0.4, -1, 0)); scrape('shoulder_L', p, n, (0.025, 0.02), DOWN, 0.46, seed=26)
p, n = surf(bone('CC_Base_R_Upperarm') * 0.4 + bone('CC_Base_R_Forearm') * 0.6, (-0.3, -1, 0)); bruise('upperarm_R', p, n, 0.025, 0.64, seed=27)

for s, sx in (('L', 1), ('R', -1)):
    el = bone('CC_Base_%s_Forearm' % s); hd = bone('CC_Base_%s_Hand' % s); m = el * 0.55 + hd * 0.45
    p, n = surf(m, (sx, -0.7, 0)); bruise('forearm_%s' % s, p, n, 0.03, 0.70 if s == 'R' else 0.6, seed=30 + sx)
    p, n = surf(el + [0, 0, -0.01], BACK); scrape('elbow_%s' % s, p, n, (0.02, 0.015), DOWN, 0.55 if s == 'L' else 0.35, seed=32 + sx)
p, n = surf(bone('CC_Base_L_Forearm') * 0.3 + bone('CC_Base_L_Hand') * 0.7, (0.3, -1, 0))
cut('forearm_cut_L', p, n, (1, 0, 0.5), 0.045, 0.40, bleed=(0.5,), seed=34, drip_len=0.07)
p, n = surf(bone('CC_Base_R_Upperarm') * 0.5 + bone('CC_Base_R_Forearm') * 0.5, (-1, 0, 0))
cut('arm_cut_R', p, n, (0, -1, 0.5), 0.05, 0.16, bleed=(0.4,), seed=35, drip_len=0.08)

for s, sx in (('L', 1), ('R', -1)):
    kn = bone('CC_Base_%s_Calf' % s); ft = bone('CC_Base_%s_Foot' % s)
    p, n = surf(kn + [0, 0, 0.012], FWD); scrape('knee_%s' % s, p, n, (0.03, 0.026), DOWN, 0.84 if s == 'L' else 0.52, seed=40 + sx)
    p, n = surf(kn * 0.55 + ft * 0.45, FWD); bruise('shin_%s' % s, p, n, 0.03, 0.70 if s == 'R' else 0.5, seed=42 + sx)
    p, n = surf(kn * 0.3 + ft * 0.7, (sx * 0.3, -1, 0)); scrape('shin_scrape_%s' % s, p, n, (0.035, 0.012), DOWN, 0.33, 0.7, seed=44 + sx)
p, n = surf((0.09, 0, 0.64), (1, -0.4, 0)); cut('thigh_L', p, n, (0.2, -1, -0.8), 0.07, 0.42, bleed=(0.35, 0.8), seed=46, drip_len=0.12)
p, n = surf((-0.08, 0, 0.70), FWD); bruise('thigh_R', p, n, 0.04, 0.62, seed=47)
p, n = surf((-0.085, 0, 0.58), FWD); cut('thigh_R', p, n, (1, 0, 0.35), 0.08, 0.20, width=0.0014, bleed=(0.3, 0.8), seed=48, drip_len=0.16)
p, n = surf((-0.10, 0, 0.30), BACK); bruise('calf_back_R', p, n, 0.035, 0.58, seed=50)   # the back is hair-covered above the waist
p, n = surf((0.08, 0, 0.68), BACK); scrape('thigh_back_L', p, n, (0.04, 0.02), (0.3, 0, -1), 0.36, seed=51)
p, n = surf((0.12, 0.06, 0.30), (1, 0, 0)); cut('calf_L', p, n, (0, 1, 0.3), 0.04, 0.13, bleed=(0.5,), seed=49, drip_len=0.06)

for nm, c in STATS: print('  %-22s %7d texels' % (nm, c))
log('wounds done')

# ---------------------------------------------------------------- write
REV = np.clip(REV, SOFT + 0.01, 0.97) * (DOM > 0.003)
def img(vals, fill):
    o = np.empty((N, N) + vals.shape[1:], np.float32); o[...] = fill; o[VY, VX] = vals; return o
_, (iy, ix) = ndimage.distance_transform_edt(~valid, return_indices=True)
def dil(a): return a[iy, ix]      # fill the UV gutters so mips and filtering do not pull in white
tint = dil(img(TINT, 1.0)); mask = dil(np.dstack([img(REV, 0), img(WET, 0), img(HGT, 0)]))
pxm = dil(img(PXM[TV], 1.0))
H = ndimage.gaussian_filter(mask[..., 2], 0.7)
gy, gx = np.gradient(H)                         # height per texel -> slope via texels per metre
dhu = gx * pxm; dhv = -gy * pxm                 # image y runs against V
NS = 0.6
nm = np.dstack([-dhu * NS, -dhv * NS, np.ones_like(H)]); nm /= np.linalg.norm(nm, axis=2, keepdims=True)
def save(a, path, srgb_rgb=False):
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB').save(path); log('saved', path)
save(tint, OUT + 'Sophia_Feridas_Tint.png')
save(np.dstack([mask[..., 0], mask[..., 1], np.clip(0.5 + mask[..., 2] / 0.001, 0, 1)]), OUT + 'Sophia_Feridas_Mask.png')
save(nm * 0.5 + 0.5, OUT + 'Sophia_Feridas_Normal.png')
base = np.asarray(Image.open(BASE).convert('RGB')).astype(np.float32) / 255
save(base * tint, OUT + 'Sophia_Body_Feridas_0HP.png')
h = np.histogram(REV[DOM > 0.05], bins=[0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1])[0]
print('texels first showing per HP band (0-10% .. 90-100%):', h)
