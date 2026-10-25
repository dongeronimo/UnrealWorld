# -*- coding: utf-8 -*-
"""Fishnet so nas pernas, passo 2 (Python do sistema, numpy + scipy + PIL):
  python fishnet_pernas_compor.py CAMPOS.npz PELE.png REDE SAIDA.png [CORTE_M] [FAIXA_M]
REDE: o fishnet antigo (.png; distorce no pe) ou a rede gerada por fishnet_rede_campos.py (.npz com
'alfa', a tinta da rede e da barra; cor COR_FIO, a mediana dos fios do antigo). Com o .npz,
CORTE e FAIXA nao valem (a barra vem pronta) e entra a zona pubica.
Pele limpa (Sophia_vag.png) em todo lugar; a rede do fishnet antigo abaixo do anel t >= CORTE + FAIXA,
onde a pele e de perna (peso >= 0,5) ou fica a mais de MEIO do meio do corpo: o gluteo tem peso de
pelvis, e so com o peso a faixa sumia atras e a rede comecava no vinco do gluteo; a faixa do meio
(vulva, perineo, rego) continua fora: MEIO na frente, MEIO_TRAS atras. Pele de braco nunca
(as maos pendem ao lado da coxa e pegavam a faixa). entre CORTE e CORTE + FAIXA, a faixa escura do topo da meia. Pixels fora de
qualquer triangulo (margem entre ilhas) copiam a classe do pixel coberto mais perto, para o
mipmap nao trazer pele para dentro da rede nem rede para fora dela.
"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage
a = sys.argv[1:]
campos, pele, rede, saida = a[:4]
CORTE = float(a[4]) if len(a) > 4 else .05
FAIXA = float(a[5]) if len(a) > 5 else .02
MEIO = float(a[6]) if len(a) > 6 else .06          # na frente: os pelos pubianos
MEIO_TRAS = float(a[7]) if len(a) > 7 else .02     # atras: so o rego
f = np.load(campos); L, T, X, Y, A = f['leg'], f['t'], f['x'], f['y'], f['braco']
coberto = L >= 0
classe = np.zeros(L.shape, np.uint8)                      # 0 pele, 1 rede, 2 faixa
perna = coberto & (A < .5) & ((L >= .5) | (X >= np.where(Y > 0, MEIO_TRAS, MEIO)))
classe[perna & (T >= CORTE + FAIXA)] = 1
classe[perna & (T >= CORTE) & (T < CORTE + FAIXA)] = 2
idx = ndimage.distance_transform_edt(~coberto, return_distances=False, return_indices=True)
classe = classe[idx[0], idx[1]]
P = np.asarray(Image.open(pele).convert('RGB'))
out = P.copy()
if rede.endswith('.npz'):
    # rede gerada (fishnet_rede_campos.py): o 'alfa' ja traz a barra do topo e o corte; aqui so
    # a mascara de perna e a zona pubica. Pele de perna chega ate a vulva e o anus (as coxas se
    # tocam no meio ate z ~0,74), e a barra antiga passava por cima: fora tudo a menos de
    # PUB_X do meio acima de PUB_Z, com 5 mm de transicao.
    PUB_X, PUB_Z, SUAVE = .035, .70, .006
    COR_FIO = np.array([30, 27, 29], float)
    Zc = f['z']
    fora_pub = np.maximum(np.clip((X - PUB_X) / SUAVE, 0, 1), np.clip((PUB_Z - Zc) / SUAVE, 0, 1))
    al = np.load(rede)['alfa'] * perna * fora_pub
    al = al[idx[0], idx[1]]  # margem entre ilhas: o valor do texel coberto mais perto
    out = (P * (1 - al[..., None]) + COR_FIO * al[..., None]).astype(np.uint8)
    Image.fromarray(out).save(saida)
    print('FISHNET', saida, 'tinta em %.1f%% da textura (rede gerada; zona pubica |x| < %.2f m acima de z %.2f m)'
          % (100 * (al > .5).mean(), PUB_X, PUB_Z))
    sys.exit()
R = np.asarray(Image.open(rede).convert('RGB'))
fio = np.abs(R.astype(int) - P.astype(int)).sum(-1) > 90  # onde a rede antiga difere da pele: os fios
cor = np.median(R[fio & (classe == 1)], axis=0).astype(np.uint8)
out[classe == 1] = R[classe == 1]
out[classe == 2] = cor
Image.fromarray(out).save(saida)
print('FISHNET', saida, 'rede %.1f%%, faixa %.2f%% da textura, cor da faixa %s, corte %.3f m, faixa %.3f m'
      % (100 * (classe == 1).mean(), 100 * (classe == 2).mean(), tuple(cor), CORTE, FAIXA))
