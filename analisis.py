import re, glob, pickle, unicodedata
import pandas as pd, numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
from pyproj import Transformer
from dateutil.relativedelta import relativedelta

HOY = pd.Timestamp('2026-11-26')
# DÍAS A CUBRIR: actualizar en cada corrida
DIAS = [pd.Timestamp('2026-11-27'), pd.Timestamp('2026-11-30'), pd.Timestamp('2026-12-01'), pd.Timestamp('2026-12-02')]
ZONA_CUAD = {'Verde':2,'Azul':3,'Amarilla':4,'Roja':5}
CUAD_ZONA = {v:k for k,v in ZONA_CUAD.items()}
tr = Transformer.from_crs(4326, 32619, always_xy=True)
def xy(lon, lat): return tr.transform(lon, lat)

# --- zonas
Z = {}
for f in glob.glob('/mnt/project/*.kml'):
    t = open(f, encoding='utf-8').read()
    polys = []
    for pm in re.findall(r'<Polygon>(.*?)</Polygon>', t, re.S):
        ob = re.search(r'<outerBoundaryIs>.*?<coordinates>(.*?)</coordinates>', pm, re.S).group(1)
        holes = re.findall(r'<innerBoundaryIs>.*?<coordinates>(.*?)</coordinates>', pm, re.S)
        P = lambda s: [tuple(map(float, p.split(',')[:2])) for p in s.split()]
        polys.append(Polygon(P(ob), [P(h) for h in holes]).buffer(0))
    name = f.split('Zona_')[1].split('_')[0]
    Z[name] = unary_union(polys)
from shapely.ops import transform as stransform
import warnings; warnings.filterwarnings('ignore')
ZM = {k: stransform(lambda x, y, z=None: tr.transform(x, y), g) for k, g in Z.items()}

def zona_de(lon, lat):
    if pd.isna(lon) or pd.isna(lat): return None, None
    p = Point(xy(lon, lat))
    for k, g in ZM.items():
        if g.covers(p): return k, 0.0
    d = {k: g.distance(p) for k, g in ZM.items()}
    k = min(d, key=d.get)
    return None, (k, d[k])

def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z0-9 ]', ' ', s)

# --- clientes
c = pd.read_excel('/mnt/user-data/uploads/2026_11_26_-_1_-_Clientes.xlsx')
c['lat'] = pd.to_numeric(c.Latitude, errors='coerce'); c['lon'] = pd.to_numeric(c.Longitude, errors='coerce')
c.loc[(c.lat.abs()<0.5)|(c.lon.abs()<0.5),['lat','lon']] = np.nan
for col in ['Fecha de Instalación', 'Fecha de último mantenimiento', 'Fecha de proximo mantenimiento']:
    c[col] = pd.to_datetime(c[col], errors='coerce')
c['freq'] = pd.to_numeric(c['Frecuencia mantenimiento (meses)'], errors='coerce')
def due(r):
    base = r['Fecha de último mantenimiento'] if pd.notna(r['Fecha de último mantenimiento']) else r['Fecha de Instalación']
    if pd.isna(base) or pd.isna(r.freq): return pd.NaT
    return base + relativedelta(months=int(r.freq))
c['vence'] = c.apply(due, axis=1)
c['dias_venc'] = (HOY - c['vence']).dt.days
c['nombre'] = c['Nombre juridico'].astype(str)
c['inact'] = c['Inactivo'].astype(str).str.upper().isin(['TRUE', 'SI', 'SÍ', '1'])
c['elig_ind'] = c['Indicador mantenimiento'].isin(['Vencido', 'Proximo a Vencerse'])
zz = c.apply(lambda r: zona_de(r.lon, r.lat), axis=1)
c['zona'] = [a for a, b in zz]; c['zona_cerca'] = [b for a, b in zz]
c['x'] = [xy(lo, la)[0] if pd.notna(lo) else np.nan for lo, la in zip(c.lon, c.lat)]
c['y'] = [xy(lo, la)[1] if pd.notna(lo) else np.nan for lo, la in zip(c.lon, c.lat)]

notas_datos = []
# AJUSTE PUNTUAL 2026-11-26 (borrar en la próxima corrida): Banesco (8274) pertenece a la zona Azul (ubicación por corregir en Odoo)
c.loc[c['Cliente ID'] == 8274, 'zona'] = 'Azul'
# correcciones de borde: fuera de polígono a <= 300 m -> zona más cercana
corr_borde = []
for i, r in c[c.zona.isna() & c.zona_cerca.notna()].iterrows():
    k, d = r.zona_cerca
    if d <= 300 and not any(p in norm(r.nombre) for p in ['ALTOS MIRANDINOS','LOS TEQUES','SAN ANTONIO','GUARENAS']):
        c.at[i, 'zona'] = k; corr_borde.append((r['Cliente ID'], r.nombre, k, round(d)))
# ciudad/estado contradictorio con coordenadas
FUERA = ['CARABOBO', 'ARAGUA', 'ANZO', 'LARA', 'BOL', 'PORTUGUESA', 'MONAGAS', 'FALC', 'NUEVA ESPARTA', 'VARGAS']
CIUDADES_FUERA = ['VALENCIA', 'MARACAY', 'LECHERIA', 'MATURIN', 'BARQUISIMETO', 'CIUDAD BOLIVAR', 'LA GUAIRA']
mal_geo = []
for cid, g in c.groupby('Cliente ID'):
    r = g.iloc[0]
    est = str(r['Estado']).upper(); ciu = str(r['Ciudad']).upper()
    if isinstance(r.zona,str) and (any(e in norm(est) for e in FUERA) or any(e in norm(ciu) for e in CIUDADES_FUERA)):
        mal_geo.append((cid, r.nombre, r['Ciudad'], r['Estado'], r.zona, len(g), int(g.elig_ind.sum())))
    elif not isinstance(r.zona,str) and pd.notna(r.lat) and ('CARACAS' in ciu) and r.zona_cerca and r.zona_cerca[1] > 5000:
        mal_geo.append((cid, r.nombre, r['Ciudad'], r['Estado'], 'fuera (%.0f km)' % (r.zona_cerca[1]/1000), len(g), int(g.elig_ind.sum())))

# --- conteos por cliente
cnt = c.groupby('Cliente ID').size()
c['n_cli'] = c['Cliente ID'].map(cnt)
PROPIOS = [8712, 9615]
RX_EDU = r'\b(COLEGIO|UNIVERSIDAD|UNIDAD EDUCATIVA|U E P|UEP|ESCUELA|INSTITUTO UNIVERSITARIO|INSTITUTO DE DISENO|INSTITUTO ESCUELA|INSTITUTO ANDES|INSTITUTOS EDUCACIONALES|ACADEMIA|CENTRO ESCOLAR|LICEO|PREESCOLAR|UCV|UCAB|UNIMET|USB|UNIVERSITARIA|EDUCANDO|GUARDERIA|MATERNAL)\b'
NO_EDU = ['SEGUROS UNIVERSITAS', 'COMIDA DE COLEGIO', 'CARBONE', 'INSTITUTO NACIONAL', 'GASTRONOMICO']
def es_edu(n):
    nn = norm(n)
    if any(x in nn for x in NO_EDU): return False
    return re.search(RX_EDU, nn) is not None
c['edu'] = c.nombre.map(es_edu)
c['propio'] = c['Cliente ID'].isin(PROPIOS)
c['grande'] = c.Segmento.isin(['HORECA', 'CORPORATIVO']) & (c.n_cli >= 3)

# --- calendario
k = pd.read_excel('/mnt/user-data/uploads/2026_11_26_-_2_-_Calendario.xlsx')
k.columns = [s.strip() for s in k.columns]
k['fecha'] = k.INICIO.dt.normalize()
k['cuad'] = k['Cuadrilla'].str.extract(r'(\d)').astype(int)
k['desc'] = k.DESCRIPCION.astype(str).str.replace('🟢', '', regex=False).str.strip()
k['cod'] = k.desc.str.extract(r'^([A-Za-z/]+)\s*:')[0].str.upper()
k['cid'] = k['Cliente ID']
k['corr'] = ''
# AJUSTE PUNTUAL 2026-11-26 (borrar en la próxima corrida): actividad Intervit = BOPA Industrial
m = k.desc.str.contains('FILAS DE MARICHE - INTERVIT', case=False)
k.loc[m, 'cid'] = 28613; k.loc[m, 'corr'] = 'Ubicada con BOPA Industrial (ID 28613), según indicación'
first = c.groupby('Cliente ID').first()
def ubic(r):
    if pd.notna(r.cid) and int(r.cid) in first.index:
        f = first.loc[int(r.cid)]
        return f.lat, f.lon, 'Cliente ID', f.nombre
    if pd.notna(r.Latitud): return r.Latitud, r.Longitud, 'Coordenadas', None
    return np.nan, np.nan, 'Sin ubicar', None
u = k.apply(ubic, axis=1)
k['lat'] = [a[0] for a in u]; k['lon'] = [a[1] for a in u]; k['metodo'] = [a[2] for a in u]; k['cliente'] = [a[3] for a in u]
k['zona_act'] = [zona_de(lo, la)[0] if pd.notna(la) else None for lo, la in zip(k.lon, k.lat)]
k['zona_cerca'] = [zona_de(lo, la)[1] if pd.notna(la) else None for lo, la in zip(k.lon, k.lat)]
k.loc[k.cid == 8274, 'zona_act'] = 'Azul'
k['x'] = [xy(lo, la)[0] if pd.notna(la) else np.nan for lo, la in zip(k.lon, k.lat)]
k['y'] = [xy(lo, la)[1] if pd.notna(la) else np.nan for lo, la in zip(k.lon, k.lat)]
# parecido por nombre para sin ubicar
def parecidos(desc):
    part = desc.split('-', 1)[-1] if '-' in desc else desc
    toks = [t for t in norm(part).split() if len(t) > 3]
    if not toks: return []
    res = []
    for cid, f in first.iterrows():
        nn = norm(f.nombre) + ' ' + norm(f['Nombre comercial'])
        if all(t in nn.split() for t in toks): res.append((cid, f.nombre))
    return res[:3]
k['parecidos'] = [parecidos(d) if m == 'Sin ubicar' else [] for d, m in zip(k.desc, k.metodo)]
k['es_m'] = k.cod.fillna('').str.split('/').map(lambda l: 'M' in l)
M_IDS = set(int(x) for x in k[k.es_m & k.cid.notna()].cid)

# ocupación
def horas(g):
    iv = sorted([(max(a.hour + a.minute/60, 9), min(b.hour + b.minute/60, 17)) for a, b in zip(g.INICIO, g.FIN)])
    tot = 0; cur = None
    for a, b in iv:
        if b <= a: continue
        if cur is None: cur = [a, b]
        elif a <= cur[1]: cur[1] = max(cur[1], b)
        else: tot += cur[1] - cur[0]; cur = [a, b]
    if cur: tot += cur[1] - cur[0]
    return tot
ocup = {(d, cq): horas(k[(k.fecha == d) & (k.cuad == cq)]) for d in DIAS for cq in [2, 3, 4, 5]}

pickle.dump(dict(c=c, k=k, Z=Z, ZM=ZM, M_IDS=M_IDS, ocup=ocup, corr_borde=corr_borde, mal_geo=mal_geo), open('/home/claude/work/base.pkl', 'wb'))
print('zonas', {kk: round(g.area/1e6, 1) for kk, g in ZM.items()})
print(c.zona.value_counts(dropna=False))
print('borde', corr_borde); print('malgeo', mal_geo)
print(k[['fecha', 'cuad', 'desc', 'cod', 'metodo', 'cliente', 'zona_act', 'es_m']].to_string())
print('M ids', M_IDS)
print({(d.strftime('%d/%m'), q): v for (d, q), v in ocup.items()})
print(k[k.metodo == 'Sin ubicar'][['desc', 'parecidos']])
print('edu', c[c.edu].groupby(['Cliente ID', 'nombre']).size())
