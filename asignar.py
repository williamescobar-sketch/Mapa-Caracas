import pickle, numpy as np, pandas as pd
b = pickle.load(open('/home/claude/work/base.pkl', 'rb'))
c, k, M_IDS, ocup = b['c'], b['k'], b['M_IDS'], b['ocup']
DIAS = [pd.Timestamp(x) for x in ['2026-11-27', '2026-11-30', '2026-12-01', '2026-12-02']]
ZONA_CUAD = {'Verde': 2, 'Azul': 3, 'Amarilla': 4, 'Roja': 5}
CAP = 16

c['excl'] = ''
c.loc[c.propio, 'excl'] = 'propio'
c.loc[(c.excl == '') & c.edu, 'excl'] = 'edu'  # AJUSTE PUNTUAL 2026-11-26: colegios fuera (solo esta corrida)
c.loc[(c.excl == '') & c.grande, 'excl'] = 'grande'
c.loc[(c.excl == '') & c['Cliente ID'].isin(M_IDS), 'excl'] = 'calendario_M'
# AJUSTE PUNTUAL 2026-11-26: clientes con desinstalación (DI) fuera de las hojas
DI_IDS = set(int(x) for x in k[k.cod.fillna('').str.split('/').map(lambda l: 'DI' in l) & k.cid.notna()].cid)
c.loc[(c.excl == '') & c['Cliente ID'].isin(DI_IDS), 'excl'] = 'calendario_DI'
c['cuad'] = c.zona.map(ZONA_CUAD)
pool_all = c[c.elig_ind & ~c.inact & c.zona.notna() & (c.excl == '')].copy()

def clusters(df, r=100):
    idx = list(df.index); X = df[['x', 'y']].values; n = len(idx)
    par = list(range(n))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    D = np.hypot(X[:, None, 0] - X[None, :, 0], X[:, None, 1] - X[None, :, 1])
    for i in range(n):
        for j in np.where(D[i, i+1:] < r)[0] + i + 1: par[f(i)] = f(j)
    lab = [f(i) for i in range(n)]
    return pd.Series(lab, index=idx)

res = {}
for zona, q in ZONA_CUAD.items():
    P = pool_all[pool_all.zona == zona].copy()
    P['g'] = clusters(P)
    G = P.groupby('g').agg(x=('x', 'mean'), y=('y', 'mean'), n=('x', 'size'), maxv=('dias_venc', 'max'))
    acts = {}; ancla = {}
    for d in DIAS:
        a = k[(k.fecha == d) & (k.cuad == q) & k.x.notna()]
        acts[d] = a[['x', 'y']].values
    # capacidades: hojas cortas al final de la semana
    N = len(P); caps = {}
    rest = N
    for d in DIAS:
        caps[d] = min(CAP, rest); rest -= caps[d]
    # anclas para días sin actividades: equipo con más días vencido
    for d in DIAS:
        if len(acts[d]) == 0:
            used = set()
            cand = G.sort_values('maxv', ascending=False)
            gsel = cand.index[0]
            ancla[d] = gsel
    assign = {d: [] for d in DIAS}; cnt = {d: 0 for d in DIAS}
    free = set(G.index)
    for d, g in ancla.items():
        assign[d].append(g); cnt[d] += G.n[g]; free.discard(g)
    # AJUSTE PUNTUAL 2026-11-26 (vaciar en la próxima corrida): equipos forzados a un día
    FORZ = {29588: pd.Timestamp('2026-11-27')}
    forz_g = {}
    for cid, d in FORZ.items():
        gs = P[P['Cliente ID'] == cid].g.unique()
        for g in gs:
            if g in free: assign[d].append(g); cnt[d] += G.n[g]; free.discard(g); forz_g[g] = d
    def pts(d):
        p = list(acts[d]) + [(G.x[g], G.y[g]) for g in assign[d]]
        return np.array(p)
    while free:
        best = None
        for d in DIAS:
            if cnt[d] >= caps[d]: continue
            p = pts(d)
            if len(p) == 0: continue
            fl = np.array(list(free))
            dd = np.min(np.hypot(G.x[fl].values[:, None] - p[None, :, 0], G.y[fl].values[:, None] - p[None, :, 1]), axis=1)
            order = np.argsort(dd)
            for o in order:
                g = fl[o]
                if cnt[d] + G.n[g] <= caps[d] + 3 or cnt[d] == 0:
                    if best is None or dd[o] < best[0]: best = (dd[o], d, g)
                    break
        if best is None: break
        _, d, g = best
        assign[d].append(g); cnt[d] += G.n[g]; free.discard(g)
    # intercambios entre días para acortar (costo = distancia al punto más cercano del día, sin contarse a sí mismo)
    def cost_g(g, d, lst):
        p = list(acts[d]) + [(G.x[h], G.y[h]) for h in lst if h != g]
        if not p: return 0
        p = np.array(p); return np.min(np.hypot(p[:, 0] - G.x[g], p[:, 1] - G.y[g]))
    improved = True; it = 0
    while improved and it < 30:
        improved = False; it += 1
        for i, d1 in enumerate(DIAS):
            for d2 in DIAS[i+1:]:
                for g1 in list(assign[d1]):
                    if g1 in ancla.values() or g1 in forz_g: continue
                    for g2 in list(assign[d2]):
                        if g2 in ancla.values() or g2 in forz_g: continue
                        if g1 not in assign[d1]: break
                        n1 = cnt[d1] - G.n[g1] + G.n[g2]; n2 = cnt[d2] - G.n[g2] + G.n[g1]
                        if n1 > caps[d1] + 3 or n2 > caps[d2] + 3 or n1 < caps[d1] - 3 or n2 < caps[d2] - 3: continue
                        before = cost_g(g1, d1, assign[d1]) + cost_g(g2, d2, assign[d2])
                        l1 = [h for h in assign[d1] if h != g1] + [g2]; l2 = [h for h in assign[d2] if h != g2] + [g1]
                        after = cost_g(g2, d1, l1) + cost_g(g1, d2, l2)
                        if after < before - 50:
                            assign[d1], assign[d2] = l1, l2; cnt[d1], cnt[d2] = n1, n2; improved = True
    # orden de ruta: vecino más cercano desde la primera actividad del día
    for d in DIAS:
        a = k[(k.fecha == d) & (k.cuad == q) & k.x.notna()].sort_values('INICIO')
        start = (a.x.iloc[0], a.y.iloc[0]) if len(a) else (G.x[ancla[d]], G.y[ancla[d]])
        rem = list(assign[d]); order = []; cur = start
        while rem:
            j = min(rem, key=lambda g: np.hypot(G.x[g] - cur[0], G.y[g] - cur[1]))
            order.append(j); rem.remove(j); cur = (G.x[j], G.y[j])
        rows = []
        for g in order:
            sub = P[P.g == g].sort_values(['nombre', 'dias_venc'], ascending=[True, False])
            rows.append(sub)
        S = pd.concat(rows) if rows else P.iloc[0:0]
        # distancia a actividad más cercana
        ap = acts[d] if len(acts[d]) else np.array([[G.x[ancla[d]], G.y[ancla[d]]]])
        S['dist_act'] = np.min(np.hypot(S.x.values[:, None] - ap[None, :, 0], S.y.values[:, None] - ap[None, :, 1]), axis=1)
        # ruta km
        path = [start] + [(G.x[g], G.y[g]) for g in order]
        km = sum(np.hypot(path[i+1][0] - path[i][0], path[i+1][1] - path[i][1]) for i in range(len(path) - 1)) / 1000
        res[(d, q)] = dict(S=S, km=km, ancla=d in ancla, ancla_row=P[P.g == ancla[d]].iloc[0] if d in ancla else None,
                           ocup=ocup[(d, q)], llena=ocup[(d, q)] >= 7, free_left=len(free))
    print(zona, 'pool', N, 'sin asignar', len(free), {d.strftime('%d/%m'): cnt[d] for d in DIAS})

# inactivos viables cerca de cada hoja
inact = c[c.elig_ind & c.inact & c.zona.notna() & (c.excl == '')]
for (d, q), r in res.items():
    S = r['S']; zona = [z for z, qq in ZONA_CUAD.items() if qq == q][0]
    I = inact[inact.zona == zona]
    a = k[(k.fecha == d) & (k.cuad == q) & k.x.notna()][['x', 'y']].values
    P2 = np.vstack([S[['x', 'y']].values, a]) if len(a) else S[['x', 'y']].values
    if len(I) and len(P2):
        dd = np.min(np.hypot(I.x.values[:, None] - P2[None, :, 0], I.y.values[:, None] - P2[None, :, 1]), axis=1)
        r['inact'] = I[dd < 400].assign(dist=dd[dd < 400])
    else: r['inact'] = I.iloc[0:0]
# evitar repetir un inactivo en varias hojas: dejarlo en la más cercana
seen = {}
for key, r in res.items():
    for i, row in r['inact'].iterrows():
        if i not in seen or row.dist < seen[i][1]: seen[i] = (key, row.dist)
for key, r in res.items():
    r['inact'] = r['inact'][[seen[i][0] == key for i in r['inact'].index]]

pickle.dump(dict(res=res, c=c, pool_all=pool_all), open('/home/claude/work/asig.pkl', 'wb'))
for (d, q), r in sorted(res.items(), key=lambda t: (t[0][1], t[0][0])):
    S = r['S']
    print(d.strftime('%d/%m'), q, len(S), 'clientes', S['Cliente ID'].nunique(), 'km %.1f' % r['km'], 'max %.0f m' % S.dist_act.max(), 'V', (S['Indicador mantenimiento'] == 'Vencido').sum(), 'llena' if r['llena'] else '', 'ANCLA' if r['ancla'] else '', 'inact', len(r['inact']))
