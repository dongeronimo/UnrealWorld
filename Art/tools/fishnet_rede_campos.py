# -*- coding: utf-8 -*-
"""Rede do fishnet, passo B (Python do sistema: numpy + scipy):
  python fishnet_rede_campos.py GEOM.npz SAIDA.npz [N] [LARGURA_MM] [CORTE_M]
Saida: 'alfa' (4096x4096, de cima para baixo) = cobertura do fio em cada texel do UV Channel0;
compor com fishnet_pernas_compor.py no lugar do fishnet antigo.

Duas coordenadas por perna, numa copia da malha subdividida 4x4 (aresta ~4 mm; a malha da perna
tem aresta de ~1 cm e os fios saiam quebrados nas arestas):
  U = distancia geodesica na pele desde o topo da meia (anel t = CORTE abaixo da junta do
      quadril), pelo metodo do calor (Crane et al. 2013, Laplaciano cotangente). E o que conserta
      o pe: a distancia cresce do tornozelo para os dedos e para o calcanhar pela pele, onde a
      projecao num eixo (reto ou curvo) espremia o peito do pe e inchava o calcanhar.
  V = angulo em volta do eixo curvo de fishnet_rede.py (referencial sem giro), em celulas:
      N em volta. E periodico, entao os fios dao a volta como helices, sem costura.
Fios: U+V e U-V inteiros, com U em celulas = integral de dU / D(U), D = circunferencia local / N
(minimo 1,1 cm): a rede estica com a perna, como a meia de verdade e o fishnet antigo. Largura
fisica do fio; borda antialiasada pelo gradiente de cada triangulo no espaco do texel.
Acima da rede, a barra (topo da meia), desenhada aqui como formas com distancia com sinal e
antialiasada: bainha, um vao translucido, renda com ilhos em losango e borda em recortes com um
ilho cada; a rede comeca sob os recortes. O fishnet antigo pintava a barra como uma faixa de cor
por texel (pela classe), serrilhada e descontinua entre ilhas UV.

Descartado (2026-10-16): V como distancia geodesica desde uma linha da frente. O calor arredonda
a distancia perto da fonte (|x| vira ~sqrt(x^2+c^2)), e com o sinal trocado de um lado a canela
ganhava uma risca escura. E t = h^2 (o do artigo) para U: o calor cai como exp(-d^2/4t) e zera
em double a 0,77 m da fonte, o pe inteiro saia com a mesma distancia; t vem de dmax.
"""
import sys, math, numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import factorized

a = sys.argv[1:]
g = np.load(a[0]); out = a[1]
N = float(a[2]) if len(a) > 2 else 20
LARG = (float(a[3]) if len(a) > 3 else 1.4) / 1000
CORTE = float(a[4]) if len(a) > 4 else .085   # 2026-10-16: 5 cm subia ate a vulva; dois dedos abaixo
K = 2                                            # recortes da barra por celula da rede
S = 4096
co, tv, tuv = g['co'], g['tv'], g['tuv']
legw, armw, lado, theta, tt, princ = g['legw'], g['armw'], g['lado'], g['theta'], g['t'], g['principal']


def geodesica(V, F, fonte, dmax):
    """Metodo do calor numa malha (V, F); fonte = mascara dos vertices de distancia zero.
    dmax: a maior distancia que se quer medir. Com t = h^2 (o do artigo) o calor cai como
    exp(-d^2/4t) e a 0,77 m da fonte e zero em double: o pe inteiro saia com a mesma distancia.
    t = dmax^2/400 deixa exp(-100) no ponto mais longe; o preco e suavizar perto da fonte."""
    n = len(V)
    e0, e1, e2 = V[F[:, 2]] - V[F[:, 1]], V[F[:, 0]] - V[F[:, 2]], V[F[:, 1]] - V[F[:, 0]]
    nrm = np.cross(e2, -e1); area2 = np.linalg.norm(nrm, axis=1); area2 = np.maximum(area2, 1e-14)
    cot = lambda u, v: (u * v).sum(1) / area2
    c0, c1, c2 = cot(-e2, e1), cot(-e0, e2), cot(-e1, e0)   # angulo em cada canto
    I = np.concatenate([F[:, 1], F[:, 2], F[:, 2], F[:, 0], F[:, 0], F[:, 1]])
    J = np.concatenate([F[:, 2], F[:, 1], F[:, 0], F[:, 2], F[:, 1], F[:, 0]])
    W = np.concatenate([c0, c0, c1, c1, c2, c2]) * .5
    L = sp.coo_matrix((W, (I, J)), (n, n)).tocsr(); L = sp.diags(np.asarray(L.sum(1)).ravel()) - L
    M = np.bincount(F.ravel(), np.repeat(area2 / 6, 3), n)
    h = np.mean(np.linalg.norm(e0, axis=1)); t = max(h * h, dmax * dmax / 400)
    u = factorized((sp.diags(M) + t * L).tocsc())(fonte.astype(float))
    # gradiente por face, normalizado e com sinal trocado
    N_ = nrm / area2[:, None]
    gu = (np.cross(N_, e0) * u[F[:, 0], None] + np.cross(N_, e1) * u[F[:, 1], None] + np.cross(N_, e2) * u[F[:, 2], None]) / area2[:, None]
    X = -gu / np.maximum(np.linalg.norm(gu, axis=1, keepdims=True), 1e-14)
    div = np.zeros(n)
    p0, p1, p2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    for (a_, b_, c_, ca, cb) in ((p0, p1, p2, c2, c1), (p1, p2, p0, c0, c2), (p2, p0, p1, c1, c0)):
        # div no vertice a: 1/2 [cot(angulo em c)(b-a).X + cot(angulo em b)(c-a).X]
        val = .5 * (ca * ((b_ - a_) * X).sum(1) + cb * ((c_ - a_) * X).sum(1))
        idx = F[:, 0] if a_ is p0 else F[:, 1] if a_ is p1 else F[:, 2]
        div += np.bincount(idx, val, n)
    phi = factorized((L + sp.eye(n) * 1e-9).tocsc())(div)
    phi = -phi if np.median(phi[fonte]) > np.median(phi) else phi
    return phi - phi[fonte].min()


def subdividir(F, n):
    """Cada triangulo vira n*n; devolve os triangulos novos, de que pai vem cada um com as
    baricentricas dos cantos, e cada vertice novo como combinacao (ids, pesos) dos originais.
    Os vertices de aresta sao compartilhados entre os triangulos vizinhos."""
    chave, comb, tris, pai, bar = {}, [], [], [], []

    def vert(vs, b):
        nz = [(int(v), round(w * n)) for v, w in zip(vs, b) if w > 1e-9]
        k = tuple(sorted(nz))
        if k not in chave:
            chave[k] = len(comb); comb.append(([v for v, _ in nz], [w / n for _, w in nz]))
        return chave[k]
    for t, vs in enumerate(F):
        idx = {}
        for i in range(n + 1):
            for j in range(n + 1 - i):
                b = (i / n, j / n, (n - i - j) / n); idx[i, j] = (vert(vs, b), b)
        for i in range(n):
            for j in range(n - i):
                cs = [(i, j), (i + 1, j), (i, j + 1)]
                tris.append([idx[c][0] for c in cs]); pai.append(t); bar.append([idx[c][1] for c in cs])
                if i + j < n - 1:
                    cs = [(i + 1, j), (i + 1, j + 1), (i, j + 1)]
                    tris.append([idx[c][0] for c in cs]); pai.append(t); bar.append([idx[c][1] for c in cs])
    return np.array(tris), np.array(pai), np.array(bar), comb


SUB = 4
FT, UVT, UT, VT, WT, DT = [], [], [], [], [], []   # triangulos finos: 3D, UV, U, V, W (m abaixo do topo), celula (m)
for k, nome in ((1, 'L'), (0, 'R')):
    reg = princ & (lado == k) & (armw < .5) & ((legw >= .2) | (tt >= 0))
    tsel = np.where(reg[tv].all(1))[0]; F = tv[tsel]
    tris, pai, bar, comb = subdividir(F, SUB)
    nv = len(comb)
    Wm = sp.lil_matrix((nv, len(co)))
    for i, (vs, ws) in enumerate(comb):
        for v_, w_ in zip(vs, ws): Wm[i, v_] = w_
    Wm = Wm.tocsr()
    Vs = Wm @ co; tts = Wm @ tt; lws = Wm @ legw
    z = Wm @ np.exp(1j * theta); ths = np.angle(z)  # angulo pela media complexa (sem pular em +-pi)
    h = np.mean(np.linalg.norm(Vs[tris[:, 1]] - Vs[tris[:, 0]], axis=1))
    topo = np.abs(tts - CORTE) < h * .75
    u = geodesica(Vs, tris, topo, .9) + CORTE
    # V: o angulo em volta do eixo curvo, em celulas (N em volta, periodico: os fios dao a volta
    # como helices, sem costura). A distancia geodesica desde uma linha da frente foi tentada e
    # descartada: o calor arredonda a distancia perto da fonte e a canela ganhava uma risca.
    v = ths * N / (2 * math.pi)
    # circunferencia de cada faixa de 1 cm de U: 2*pi * raio medio em volta do centro da faixa
    m = lws >= .5
    bins = np.arange(0, u[m].max() + .01, .01); kb = np.clip(np.digitize(u, bins) - 1, 0, len(bins) - 1)
    circ = np.full(len(bins), np.nan)
    for i in range(len(bins)):
        q = Vs[m & (kb == i)]
        if len(q) > 20: circ[i] = 2 * math.pi * np.linalg.norm(q - q.mean(0), axis=1).mean()
    ok = ~np.isnan(circ); circ = np.interp(np.arange(len(bins)), np.where(ok)[0], circ[ok])
    circ = np.convolve(np.pad(circ, 4, mode='edge'), np.ones(9) / 9, 'valid')
    dcel = np.maximum(circ / N, .011)
    # U em celulas: integral de dU / D(U) (dividir U pelo D local quebraria os fios onde D muda)
    ucel = np.concatenate([[0], np.cumsum(.01 / dcel[:-1])])
    FT.append(Vs[tris]); UT.append(np.interp(u, bins, ucel)[tris]); VT.append(v[tris])
    # W: a barra mede-se pelo plano do eixo da coxa (exato), nao pela geodesica (que o calor
    # arredonda perto do anel de origem)
    WT.append((tts - CORTE)[tris]); DT.append(dcel[kb][tris])
    pu = tuv[tsel][pai]                     # UV dos cantos do pai
    UVT.append(np.einsum('tcb,tbd->tcd', bar, pu))
    print('  perna %s: %d vertices finos (aresta %.1f mm); U ate %.2f m; circunferencia %.0f..%.0f cm; celula %.1f..%.1f cm' % (
        nome, nv, h * 1000, u[m].max(), circ.min() * 100, circ.max() * 100, dcel.min() * 100, dcel.max() * 100), flush=True)
FT, UVT, UT, VT, WT, DT = map(np.concatenate, (FT, UVT, UT, VT, WT, DT))


def grad(P2, f):
    e1, e2 = P2[1] - P2[0], P2[2] - P2[0]; df1, df2 = f[1] - f[0], f[2] - f[0]
    G = np.array([[e1 @ e1, e1 @ e2], [e1 @ e2, e2 @ e2]]); det = np.linalg.det(G)
    if abs(det) < 1e-20: return None
    ab = np.linalg.solve(G, [df1, df2]); return ab[0] * e1 + ab[1] * e2


# barra (o topo da meia), de cima para baixo, em metros abaixo do topo:
BAINHA, VAO, RENDA, ARCO = .004, .0012, .018, .007
OLHO_D, OLHO_R = .0026, .0014     # losango (meia diagonal) na renda; ilhos redondos nos recortes


def cobre(sd, pix):
    """Cobertura antialiasada de uma forma com distancia com sinal sd (negativa dentro), em metros."""
    return np.clip(.5 - sd / pix, 0, 1)


def barra(w, a, d, pix):
    """Tinta da barra e o fundo dela (onde a rede comeca). w: m abaixo do topo; a: celulas em
    volta; d: celula (m). Bainha solida, um vao translucido, renda com uma fileira de ilhos em
    losango (dois por recorte) e a borda de baixo em recortes (meia-lua), cada um com um ilho."""
    p = (a * K) % 1 - .5; sw = d / K                       # fase e largura do recorte
    fundo = RENDA + ARCO * np.sqrt(np.clip(1 - (2 * p) ** 2, 0, 1))
    tinta = cobre(np.maximum(-w, w - fundo), pix)
    tinta *= 1 - .55 * cobre(np.abs(w - (BAINHA + VAO / 2)) - VAO / 2, pix)
    p2 = (a * K * 2) % 1 - .5; cy = (BAINHA + VAO + RENDA) / 2
    tinta *= 1 - cobre((np.abs(p2 * sw / 2) + np.abs(w - cy) - OLHO_D) / math.sqrt(2), pix)
    tinta *= 1 - cobre(np.hypot(p * sw, w - (RENDA + OLHO_R * 2)) - OLHO_R, pix)
    return tinta, fundo


ALFA = np.zeros((S, S), np.float32)
for P3, pu, u3, v3, w3, d3 in zip(FT, UVT * S, UT, VT, WT, DT):
    v3 = v3 - N * np.round((v3 - v3[0]) / N)  # desembrulha o angulo dentro do triangulo
    x0, x1 = max(0, int(pu[:, 0].min())), min(S, int(np.ceil(pu[:, 0].max())) + 1)
    y0, y1 = max(0, int(pu[:, 1].min())), min(S, int(np.ceil(pu[:, 1].max())) + 1)
    if x0 >= x1 or y0 >= y1: continue
    a_, bb, c_ = pu; den = (bb[1] - c_[1]) * (a_[0] - c_[0]) + (c_[0] - bb[0]) * (a_[1] - c_[1])
    if abs(den) < 1e-12: continue
    yy, xx = np.mgrid[y0:y1, x0:x1] + .5
    wa = ((bb[1] - c_[1]) * (xx - c_[0]) + (c_[0] - bb[0]) * (yy - c_[1])) / den
    wb = ((c_[1] - a_[1]) * (xx - c_[0]) + (a_[0] - c_[0]) * (yy - c_[1])) / den
    wc = 1 - wa - wb
    dentro = (wa >= -1e-4) & (wb >= -1e-4) & (wc >= -1e-4)
    if not dentro.any(): continue
    A_ = np.zeros(dentro.shape)
    # metros por texel: raiz da razao das areas 3D e UV do triangulo
    a3 = np.linalg.norm(np.cross(P3[1] - P3[0], P3[2] - P3[0]))
    pix = math.sqrt(a3 / max(abs(den), 1e-12))
    W_ = wa * w3[0] + wb * w3[1] + wc * w3[2]
    if W_[dentro].max() < -pix: continue                    # acima do topo da meia
    Av = wa * v3[0] + wb * v3[1] + wc * v3[2]; Dv = wa * d3[0] + wb * d3[1] + wc * d3[2]
    tinta_b, fundo = barra(W_, Av, Dv, pix)
    for f in (u3 + v3, u3 - v3):
        gt = grad(pu, f); g3 = grad(P3, f)
        if gt is None or g3 is None: continue
        nt, n3 = np.linalg.norm(gt), np.linalg.norm(g3)
        if n3 < 1e-9: continue
        val = wa * f[0] + wb * f[1] + wc * f[2]
        dfis = np.abs(val - np.round(val)) / n3
        A_ = np.maximum(A_, np.clip((LARG / 2 - dfis) / max(nt / n3, 1e-9) + .5, 0, 1))
    A_ = np.maximum(A_ * cobre(fundo - W_, pix), tinta_b)   # a rede so abaixo dos recortes
    blk = ALFA[y0:y1, x0:x1]; blk[dentro] = np.maximum(blk[dentro], A_[dentro])
np.savez_compressed(out, alfa=ALFA[::-1])
print('FISHNET_REDE', out, 'N %.0f, fio %.1f mm; texels com fio %d' % (N, LARG * 1000, int((ALFA > .5).sum())))
