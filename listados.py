import pickle, pandas as pd, numpy as np
a = pickle.load(open('/home/claude/work/asig.pkl', 'rb')); b = pickle.load(open('/home/claude/work/base.pkl', 'rb'))
c = a['c']; k = b['k']; M_IDS = b['M_IDS']
ZONA_CUAD = {'Verde': 2, 'Azul': 3, 'Amarilla': 4, 'Roja': 5}
FIN_DIC = pd.Timestamp('2026-12-31')
c['vence_dic'] = c.vence <= FIN_DIC
def resumen(g):
    g = g.assign(**{'Cliente ID': g.name})
    act = g[~g.inact]
    r = dict(cid=g['Cliente ID'].iloc[0], nombre=g.nombre.iloc[0], seg=g.Segmento.iloc[0], zona=g.zona.dropna().iloc[0] if g.zona.notna().any() else None,
             total=len(g), activos=len(act), inact=int(g.inact.sum()),
             venc=int((act['Indicador mantenimiento'] == 'Vencido').sum()), prox=int((act.vence_dic & (act['Indicador mantenimiento'] != 'Vencido')).sum()),
             maxv=int(act.dias_venc.max()) if len(act) and act.dias_venc.notna().any() else None,
             cal=', '.join(sorted(set(k[k.cid == g['Cliente ID'].iloc[0]].apply(lambda r: f"{r.cod} {r.fecha:%d/%m} C{r.cuad}", axis=1)))) if (k.cid == g['Cliente ID'].iloc[0]).any() else '')
    r['pct'] = (r['venc'] + r['prox']) / r['activos'] if r['activos'] else 0
    return pd.Series(r)
G = c[(c.excl == 'grande')]
grandes = G.groupby('Cliente ID').apply(resumen)
grandes = grandes[(grandes.venc + grandes.prox) > 0]
grandes['en_zona'] = grandes.zona.notna()
gz = grandes[grandes.en_zona]
g_in = gz[gz.pct > 0.5].sort_values(['zona', 'pct'], ascending=[True, False])
g_out = gz[gz.pct <= 0.5].sort_values(['zona', 'pct'], ascending=[True, False])
g_fuera = grandes[~grandes.en_zona]
propios = c[c.propio].groupby('Cliente ID').apply(resumen)
E = c[c.excl == 'edu']
edu = E.groupby('Cliente ID').apply(resumen)
edu = edu[(edu.venc + edu.prox) > 0].sort_values(['zona', 'venc'], ascending=[True, False])
# calendario con M bloqueado (clientes excluidos de hojas)
mcli = c[c['Cliente ID'].isin(M_IDS)].groupby('Cliente ID').apply(resumen)
pickle.dump(dict(g_in=g_in, g_out=g_out, g_fuera=g_fuera, propios=propios, edu=edu, mcli=mcli), open('/home/claude/work/listas.pkl', 'wb'))
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 45)
cols = ['nombre', 'seg', 'zona', 'total', 'activos', 'venc', 'prox', 'pct', 'maxv', 'cal']
print('IN', len(g_in)); print(g_in[cols].to_string())
print('OUT', len(g_out)); print(g_out[cols].to_string())
print('FUERA', len(g_fuera)); print(g_fuera[cols].to_string())
print(propios[cols].to_string()); print('EDU'); print(edu[cols].to_string()); print(mcli[cols].to_string())
