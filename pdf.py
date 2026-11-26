import pickle, re, pandas as pd, numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, NextPageTemplate, KeepTogether, CondPageBreak)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

for w in [200, 300, 400, 500, 600, 700]:
    pdfmetrics.registerFont(TTFont(f'R{w}', f'/home/claude/fonts/Raleway-W{w}.ttf'))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
pdfmetrics.registerFont(TTFont('DJ', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
registerFontFamily('R400', normal='R400', bold='R600', italic='R400', boldItalic='R600')
registerFontFamily('R300', normal='R300', bold='R600', italic='R300', boldItalic='R600')

GRIS = colors.HexColor('#5f6368'); GRIS2 = colors.HexColor('#8a8f94'); GRIS3 = colors.HexColor('#d5d8db'); GRIS4 = colors.HexColor('#f3f4f5')
AZUL = colors.HexColor('#5b8fc4'); MORADO = colors.HexColor('#8E6BB5'); MORADO_BG = colors.HexColor('#f1ecf7')
ZCOL = {'Verde': '#6BA368', 'Azul': '#4A7FB5', 'Amarilla': '#D4A72C', 'Roja': '#C9584C'}
CUAD_ZONA = {2: 'Verde', 3: 'Azul', 4: 'Amarilla', 5: 'Roja'}
DIAS_ES = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
def fecha_larga(d): return f'{DIAS_ES[d.weekday()].capitalize()} {d.day} de {MESES[d.month-1]}'

a = pickle.load(open('/home/claude/work/asig.pkl', 'rb')); b = pickle.load(open('/home/claude/work/base.pkl', 'rb'))
L = pickle.load(open('/home/claude/work/listas.pkl', 'rb'))
res, c = a['res'], a['c']; k = b['k']; ocup = b['ocup']
DIAS = [pd.Timestamp(x) for x in ['2026-11-27', '2026-11-30', '2026-12-01', '2026-12-02']]

# ---------- estilos
def S(name, font='R400', size=8.5, lead=None, color=GRIS, **kw):
    return ParagraphStyle(name, fontName=font, fontSize=size, leading=lead or size * 1.38, textColor=color, **kw)
body = S('body', size=9, lead=13.2, spaceAfter=5)
small = S('small', size=7.5, lead=10)
tiny = S('tiny', size=6.8, lead=8.6)
cell = S('cell', size=7.2, lead=8.8)
cellb = S('cellb', font='R600', size=7.2, lead=8.8)
cellr = S('cellr', size=7.2, lead=8.8, alignment=TA_RIGHT)
cellc = S('cellc', size=7.2, lead=8.8, alignment=TA_CENTER)
hdr = S('hdr', font='R600', size=6.8, lead=8.4, color=GRIS2)
h2 = S('h2', font='R600', size=10.5, lead=14, color=GRIS, spaceBefore=8, spaceAfter=4)
def titulo(fino, grueso, size=24):
    return Paragraph(f'<font name="R200">{fino}</font> <font name="R600" color="#5b8fc4">{grueso}</font>',
                     S('t', size=size, lead=size * 1.15, spaceAfter=10))

# ---------- utilidades de texto
KEEP_UP = {'C.A', 'CA', 'S.A', 'SA', 'II', 'III', 'IV', 'VI', 'LAH', 'CC', 'UCV', 'BTU', 'BNC', 'PDVSA', 'CSC', 'GH', 'VCB', 'EY', 'TV', 'XXI',
           'S.C', 'A.C', 'S.C.A', 'MDS', 'J.T', 'DBAC', 'HCL', 'H.C.L', 'CEMO', 'RNLT', 'LPG', 'ECA', 'UNICEF', 'TFC', 'C.A.', 'S.A.', 'A.C.', 'S.C.', 'U.E.P.', 'UEP'}
MINUS = {'de', 'del', 'la', 'las', 'los', 'y', 'e', 'el', 'en', 'a'}
def tcase(s):
    out = []
    for i, w in enumerate(str(s).split()):
        u = w.upper().strip(',')
        if w.lower() in MINUS and i > 0: out.append(w.lower())
        elif u in KEEP_UP or (len(u) <= 3 and not re.search('[AEIOUÁÉÍÓÚ]', u) and u.isalpha()): out.append(w.upper())
        elif w.lower() in MINUS and i > 0: out.append(w.lower())
        elif w.startswith('(') and len(w) > 1: out.append('(' + w[1:2].upper() + w[2:].lower())
        else: out.append(w[:1].upper() + w[1:].lower())
    return ' '.join(out)
SUF = r',?\s*(C\.?\s?A\.?|S\.?\s?A\.?|S\.?C\.?|A\.?C\.?|S\.C\.A\.?)\s*$'
def limpiar(s):
    s = re.sub(r'\s+', ' ', str(s)).strip().strip(',')
    for _ in range(2): s = re.sub(SUF, '', s, flags=re.I).strip().strip(',')
    return s
def nombre_corto(n, maxlen=48):
    n = str(n)
    parts = [p.strip() for p in re.split(r',\s*(?=[^,]*$)', n)] if n.count(',') >= 1 else [n]
    # Odoo "Empresa, Sede": si hay coma tras sufijo societario, separar
    m = re.match(r'^(.*?\b(?:C\.?\s?A\.?|S\.?\s?A\.?|A\.?C\.?|S\.?C\.?|CA|INC)(?![A-Z]),?)\s*,\s*(.+)$', n, flags=re.I)
    if m:
        emp, sede = limpiar(m.group(1)), limpiar(re.sub(r'^(C\.?\s?A\.?|S\.?A\.?)\s*,\s*', '', m.group(2), flags=re.I))
        if emp.upper() in sede.upper() or sede.upper().startswith(emp.upper()[:10]) or sede.upper() in emp.upper(): out = sede if len(sede) >= len(emp) else emp
        else: out = f'{emp} · {sede}'
    elif ',' in n and not re.search(SUF, n, flags=re.I):
        emp, sede = [limpiar(x) for x in n.split(',', 1)]
        out = sede if emp.upper() in sede.upper() else (emp if sede.upper() in emp.upper() else f'{emp} · {sede}')
    else: out = limpiar(n)
    if ', ' in out:
        p1, p2 = out.split(', ', 1)
        if p1.upper() in p2.upper() or p2.upper() in p1.upper(): out = p1 if len(p1) >= len(p2) else p2
    out = tcase(out)
    return out if len(out) <= maxlen else out[:maxlen - 1].rstrip() + '…'
def equipo_corto(e):
    m = re.match(r'\[(AFS?\d+)\]\s*(.*)', str(e), flags=re.I)
    if not m: return tcase(e)
    cod, t = m.groups()
    t = t.replace('EQUIPO DISPENSADOR', 'Disp.').replace('SISTEMA DE FILTRADO-', 'Filtrado ').replace('SISTEMA DE FILTRADO', 'Sist. filtrado')
    t = tcase(t).replace('Disp.', 'Disp.').replace('(sifón)', '(sifón)')
    t = re.sub(r'\b(\d)fc\b', lambda x: x.group(1) + 'FC', t, flags=re.I)
    t = re.sub(r'(Fc|Ls|Lf)\b', lambda x: x.group(1).upper(), t)
    t = re.sub(r'-ls\b', '-LS', t, flags=re.I)
    return f'{t} [{cod.upper()}]'
SEG = {'HOGAR': 'Hogar', 'HORECA': 'Horeca', 'CORPORATIVO': 'Corp.', 'MONIN': 'Monin'}
def estado(r):
    if r['Indicador mantenimiento'] == 'Vencido':
        d = int(r.dias_venc) if pd.notna(r.dias_venc) else None
        if d is None: return 'Vencido'
        if d == 0: return 'Vence hoy'
        if d < 0: return f'Vencido* · {r.vence:%d/%m}'
        return f'Vencido · {d} d'
    return f'Próximo · {r.vence:%d/%m}' if pd.notna(r.vence) else 'Próximo'
def ultimo(r):
    if pd.notna(r['Fecha de último mantenimiento']): return f"{r['Fecha de último mantenimiento']:%d/%m/%y}"
    if pd.notna(r['Fecha de Instalación']): return f"Inst. {r['Fecha de Instalación']:%d/%m/%y}"
    return '—'
def dist_txt(m):
    return f'{m/1000:.1f} km'.replace('.', ',') if m >= 1000 else f'{int(round(m/10)*10)} m'
def fmt(x, d=1): return f'{x:.{d}f}'.replace('.', ',')

def tabla(data, widths, zebra=False, head_color=AZUL, extra=None, rep=1):
    t = Table(data, colWidths=widths, repeatRows=rep)
    st = [('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('LINEBELOW', (0, 0), (-1, 0), 1.1, head_color),
          ('TOPPADDING', (0, 0), (-1, -1), 2.6), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.6),
          ('LEFTPADDING', (0, 0), (-1, -1), 3), ('RIGHTPADDING', (0, 0), (-1, -1), 3),
          ('LINEBELOW', (0, 1), (-1, -1), 0.3, GRIS3)]
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0: st.append(('BACKGROUND', (0, i), (-1, i), GRIS4))
    if extra: st += extra
    t.setStyle(TableStyle(st)); return t
P = lambda t, s=cell: Paragraph(t, s)
H = lambda t: Paragraph(t.upper(), hdr)

# ---------- páginas
W, Hh = letter; M = 0.55 * inch
def cover(cv, doc):
    cv.saveState()
    cv.setFillColor(colors.HexColor('#a3a7ab')); p = cv.beginPath()
    p.moveTo(W - 1.25 * inch, Hh); p.lineTo(W, Hh); p.lineTo(W, Hh - 1.25 * inch); p.close(); cv.drawPath(p, fill=1, stroke=0)
    cv.drawImage('/home/claude/logo_gray_hi.png', W / 2 - 0.3 * inch, Hh - 2.05 * inch, width=0.6 * inch, height=0.6 * 81 / 55 * inch, mask='auto')
    cv.setFillColor(GRIS); cv.setFont('R400', 11)
    cv.drawCentredString(W / 2, Hh - 2.55 * inch, 'P R O P U E S T A   D E')
    cv.setFont('R200', 40); cv.drawCentredString(W / 2, Hh - 3.15 * inch, 'MANTENIMIENTOS')
    cv.setFont('R600', 15); cv.setFillColor(AZUL); cv.drawCentredString(W / 2, Hh - 3.6 * inch, 'Equipos prioritarios · Semana 48')
    cv.setFont('R300', 11); cv.setFillColor(GRIS)
    cv.drawCentredString(W / 2, Hh - 3.92 * inch, 'Viernes 27 y lunes 30 de noviembre · martes 1 y miércoles 2 de diciembre de 2026')
    # KPIs
    tot = sum(len(r['S']) for r in res.values()); ven = sum((r['S']['Indicador mantenimiento'] == 'Vencido').sum() for r in res.values())
    kp = [(str(tot), 'equipos recomendados'), (str(ven), 'vencidos'), (str(tot - ven), 'próximos a vencerse'), ('16', 'hojas · 4 cuadrillas × 4 días')]
    x0 = M + 0.2 * inch; wcol = (W - 2 * M - 0.4 * inch) / 4; y = Hh - 5.2 * inch
    for i, (v, l) in enumerate(kp):
        cx = x0 + wcol * (i + 0.5)
        cv.setFont('R200', 34); cv.setFillColor(AZUL if i == 0 else GRIS); cv.drawCentredString(cx, y, v)
        cv.setFont('R400', 8.5); cv.setFillColor(GRIS2); cv.drawCentredString(cx, y - 0.25 * inch, l)
        if i: cv.setStrokeColor(GRIS3); cv.setLineWidth(0.6); cv.line(x0 + wcol * i, y - 0.35 * inch, x0 + wcol * i, y + 0.35 * inch)
    # zonas
    y2 = Hh - 6.4 * inch
    cv.setFont('R600', 8); cv.setFillColor(GRIS2); cv.drawCentredString(W / 2, y2 + 0.32 * inch, 'ZONAS Y CUADRILLAS')
    zs = [('Verde', 2), ('Azul', 3), ('Amarilla', 4), ('Roja', 5)]
    for i, (z, q) in enumerate(zs):
        cx = x0 + wcol * (i + 0.5)
        n = sum(len(r['S']) for (d, qq), r in res.items() if qq == q)
        cv.setFillColor(colors.HexColor(ZCOL[z])); cv.circle(cx - 0.55 * inch, y2 + 0.04 * inch, 4.5, fill=1, stroke=0)
        cv.setFillColor(GRIS); cv.setFont('R500', 10); cv.drawString(cx - 0.45 * inch, y2, f'Cuadrilla {q}')
        cv.setFont('R300', 8.5); cv.setFillColor(GRIS2); cv.drawString(cx - 0.45 * inch, y2 - 0.18 * inch, f'Zona {z} · {n} equipos')
    cv.setStrokeColor(AZUL); cv.setLineWidth(0.8); cv.line(W / 2 - 0.5 * inch, 1.35 * inch, W / 2 + 0.5 * inch, 1.35 * inch)
    cv.setFont('R300', 8.5); cv.setFillColor(GRIS2)
    cv.drawCentredString(W / 2, 1.1 * inch, 'Acqua Fontana · Planificación de mantenimientos · Preparado el jueves 26 de noviembre de 2026')
    cv.drawCentredString(W / 2, 0.92 * inch, 'Fuentes: listado de clientes y Calendario del 26/11/2026 · zonas KML «Prueba 2026_08_14»')
    cv.restoreState()
def normal(cv, doc):
    cv.saveState()
    cv.drawImage('/home/claude/logo_gray_hi.png', M, Hh - 0.47 * inch, width=0.17 * inch, height=0.17 * 81 / 55 * inch, mask='auto')
    cv.setFont('R400', 7.5); cv.setFillColor(GRIS2)
    cv.drawString(M + 0.25 * inch, Hh - 0.4 * inch, 'Acqua Fontana · Equipos prioritarios · Semana 48')
    cv.drawRightString(W - M, Hh - 0.4 * inch, '27/11 – 02/12/2026')
    cv.setStrokeColor(GRIS3); cv.setLineWidth(0.5); cv.line(M, Hh - 0.5 * inch, W - M, Hh - 0.5 * inch)
    cv.drawRightString(W - M, 0.38 * inch, str(doc.page))
    cv.restoreState()
doc = BaseDocTemplate('/mnt/user-data/outputs/2026_11_26_-_Propuesta_de_mantenimientos.pdf', pagesize=letter,
                      leftMargin=M, rightMargin=M, topMargin=0.68 * inch, bottomMargin=0.55 * inch,
                      title='Acqua Fontana · Equipos prioritarios - Semana 48 (27/11 al 02/12/2026)', author='Acqua Fontana')
fr = Frame(M, 0.55 * inch, W - 2 * M, Hh - 0.68 * inch - 0.55 * inch, id='f', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate('cover', [fr], onPage=cover), PageTemplate('normal', [fr], onPage=normal)])
CW = W - 2 * M
story = [NextPageTemplate('normal'), PageBreak()]

# ---------- datos de resumen
tot = sum(len(r['S']) for r in res.values()); ven = int(sum((r['S']['Indicador mantenimiento'] == 'Vencido').sum() for r in res.values()))
llenas = [(d, q) for (d, q), r in res.items() if r['llena']]
pool = a['pool_all']; asignados = set().union(*[set(r['S'].index) for r in res.values()])
rest = {z: int(((pool.zona == z) & ~pool.index.isin(asignados)).sum()) for z in ZCOL}
edu = L['edu']; edu_eq = int((edu.venc + edu.prox).sum())
SI = res[(DIAS[2], 4)]['S']; sanig = SI[SI.dist_act < 15]
anc = res[(DIAS[3], 5)]['ancla_row']

# ---------- Lo esencial
story += [titulo('Lo', 'esencial')]
story.append(P(f'Esta propuesta reúne <b>{tot} equipos</b> en 16 hojas, una por cuadrilla y día: {ven} vencidos y {tot-ven} próximos a vencerse. '
               'Cada hoja parte de las actividades del Calendario de ese día y toma los equipos más cercanos de la zona de la cuadrilla, sin importar el atraso. '
               'Para esta corrida se aplicó el método probado el 19/11: clientes a menos de 100 m entre sí siempre en la misma hoja, cada grupo asignado al día cuyas actividades le quedan más cerca viendo toda la semana, e intercambios entre días para acortar rutas.', body))
story.append(P('<b>Ruta llena.</b> El viernes 27 las cuatro cuadrillas tienen 7 h ocupadas entre 9:00 y 17:00, y la Cuadrilla 4 también el lunes 30 y el martes 1. '
               'Aun así se hacen las recomendaciones pertinentes, para que se aprovechen si se libera tiempo o se reprograma algo.', body))
story.append(P(f'<b>Hoja sin actividades.</b> La Cuadrilla 5 no tiene actividades el miércoles 2. Su hoja parte del equipo con más días sin mantenimiento de la zona Roja, '
               f'{nombre_corto(anc.nombre)} ({int(anc.dias_venc)} días vencido), y está resaltada en <font color="#8E6BB5"><b>morado</b></font>.', body))
story.append(P('<b>Sus observaciones de esta corrida</b>', h2))
story.append(P('La actividad «M: Filas de Mariche – Intervit» se ubicó con BOPA Industrial (ID 28613), cuyo nombre comercial es «INTERVIT - FILAS DE MARICHE». Cable Norte Filas de Mariche (ID 29588) se añadió a la hoja de la Cuadrilla 5 del mismo día, el viernes 27. '
               f'Los clientes del C.C. San Ignacio que comparten ubicación con Vas Ven Chacao entraron en la hoja de la Cuadrilla 4 del martes 1 ({len(sanig)} equipos). '
               f'Los colegios y universidades quedaron fuera de las hojas y van en un listado aparte para enero: {len(edu)} clientes con {edu_eq} equipos vencidos o próximos. '
               'En el Calendario hay dos mantenimientos agendados en colegios que convendría mover a enero si es posible: Colegio Integral El Ávila (viernes 27) y Colegio Academia Merici (lunes 30).', body))
story.append(P('<b>Equipos que quedan para próximas corridas</b>', h2))
story.append(P(f'Después de armar las hojas siguen pendientes {sum(rest.values())} equipos vencidos o próximos en las zonas: '
               f'{rest["Verde"]} en Verde, {rest["Azul"]} en Azul, {rest["Amarilla"]} en Amarilla y {rest["Roja"]} en Roja. '
               'La zona Roja es la que más acumula.', body))
# distribución
story.append(P('<b>Distribución por cuadrilla y día</b>', h2))
rows = [[H('Cuadrilla'), H('Vie 27/11'), H('Lun 30/11'), H('Mar 01/12'), H('Mié 02/12'), H('Total')]]
ext = []
for i, q in enumerate([2, 3, 4, 5]):
    z = CUAD_ZONA[q]
    row = [P(f'<font name="DJ" size="8" color="{ZCOL[z]}">●</font> Cuadrilla {q} · {z}', cell)]; tq = 0
    for j, d in enumerate(DIAS):
        r = res[(d, q)]; n = len(r['S']); v = int((r['S']['Indicador mantenimiento'] == 'Vencido').sum()); tq += n
        tag = ' · <font color="#5b8fc4">ruta llena</font>' if r['llena'] else (' · <font color="#8E6BB5">sin actividades</font>' if r['ancla'] else '')
        row.append(P(f'<b>{n}</b> <font color="#8a8f94">({v} V)</font><br/><font size="6.4" color="#8a8f94">~{fmt(r["km"])} km{tag}</font>', cell))
        if r['ancla']: ext.append(('BACKGROUND', (j + 1, i + 1), (j + 1, i + 1), MORADO_BG))
    row.append(P(f'<b>{tq}</b>', cellc)); rows.append(row)
rows.append([P('<b>Total</b>', cell)] + [P(f'<b>{sum(len(res[(d,q)]["S"]) for q in [2,3,4,5])}</b>', cell) for d in DIAS] + [P(f'<b>{tot}</b>', cellc)])
story.append(tabla(rows, [1.75 * inch] + [1.2 * inch] * 4 + [0.6 * inch], extra=ext + [('LINEABOVE', (0, -1), (-1, -1), 0.8, GRIS2)]))
story.append(Spacer(1, 4))
story.append(P('V = vencidos. Los km son una referencia en línea recta del recorrido entre la primera actividad del día y los grupos de la hoja, en el orden de la tabla.', tiny))

# ---------- Contraste con el calendario
story += [PageBreak(), titulo('Contraste con el', 'calendario')]
story.append(P('El Calendario se leyó solo por Cliente ID o, si no lo tiene, por latitud y longitud. Ninguna actividad se ubicó por su nombre. '
               'Los clientes con mantenimiento (M) agendado no entran en las hojas, y tampoco los que tienen una desinstalación (DI), porque no tendría sentido mantener un equipo que se retira.', body))
# ocupación
rows = [[H('Horas ocupadas 9:00–17:00')] + [H(f'{DIAS_ES[d.weekday()][:3]} {d:%d/%m}') for d in DIAS]]
ext = []
for i, q in enumerate([2, 3, 4, 5]):
    row = [P(f'<font name="DJ" size="8" color="{ZCOL[CUAD_ZONA[q]]}">●</font> Cuadrilla {q}', cell)]
    for j, d in enumerate(DIAS):
        h = ocup[(d, q)]
        row.append(P(f'<b>{fmt(h,0)} h</b>' + (' · ruta llena' if h >= 7 else (' · sin actividades' if h == 0 else f' · {fmt(8-h,0)} h libres')), cell))
        if h >= 7: ext.append(('TEXTCOLOR', (j + 1, i + 1), (j + 1, i + 1), AZUL))
    rows.append(row)
story.append(tabla(rows, [1.5 * inch] + [1.5 * inch] * 4, extra=ext))
story.append(Spacer(1, 8))
# actividades
def ubic_txt(r):
    if r.metodo == 'Cliente ID':
        z = r.zona_act; zc = CUAD_ZONA[r.cuad]
        t = f'ID {int(r.cid)}'
        return t + (f' · <font color="#C9584C">zona {z}</font>' if z and z != zc else '')
    if r.metodo == 'Coordenadas':
        z = r.zona_act; zc = CUAD_ZONA[r.cuad]
        return 'Coordenadas' + (f' · <font color="#C9584C">zona {z}</font>' if z and z != zc else '')
    return '<font color="#C9584C">Sin ubicar</font>'
rows = [[H('Día'), H('Hora'), H('Cuad.'), H('Actividad'), H('Ubicación'), H('En la propuesta')]]
kk = k[k.fecha.isin(DIAS)].sort_values(['fecha', 'cuad', 'INICIO'])
for _, r in kk.iterrows():
    cid = int(r.cid) if pd.notna(r.cid) else None
    g = c[c['Cliente ID'] == cid] if cid else c.iloc[0:0]
    if r.es_m: obs = 'Fuera de las hojas (M agendado)'
    elif r.cod and 'DI' in str(r.cod).split('/') and cid: obs = 'Fuera de las hojas (desinstalación)'
    elif cid and len(g) and not (g.elig_ind & ~g.inact).any(): obs = 'Punto de partida (sin equipos pendientes)'
    elif cid and len(g) and g.excl.iloc[0] == 'grande': obs = 'Cliente grande: listado aparte'
    elif cid and len(g) and g.excl.iloc[0] == 'edu': obs = 'Colegio: listado para enero'
    elif cid and any(cid in set(res[(r.fecha, q)]['S']['Cliente ID']) for q in [2, 3, 4, 5]): obs = 'Sus equipos pendientes están en la hoja del día'
    elif r.metodo == 'Sin ubicar': obs = 'No sirve de punto de partida'
    else: obs = 'Punto de partida de la hoja'
    if r['corr']: obs = 'Ubicada con BOPA Industrial (ID 28613) · M agendado'
    rows.append([P(f'{DIAS_ES[r.fecha.weekday()][:3]} {r.fecha:%d/%m}'), P(f'{r.INICIO:%H:%M}–{r.FIN:%H:%M}'), P(str(r.cuad), cellc),
                 P(tcase(r.desc.strip()) if False else r.desc.strip()), P(ubic_txt(r)), P(obs)])
story.append(tabla(rows, [0.6 * inch, 0.72 * inch, 0.38 * inch, 2.55 * inch, 1.25 * inch, 1.9 * inch], zebra=True, extra=[('TOPPADDING', (0, 1), (-1, -1), 1.6), ('BOTTOMPADDING', (0, 1), (-1, -1), 1.6)]))
story.append(P('El sábado 28 (desinstalación del concierto en el Caracas Country Club, Cuadrilla 4) no se cubre en esta propuesta.', tiny))
# observaciones
story.append(P('<b>Observaciones</b>', h2))
mc = L['mcli']
obs = [
 '<b>Filas de Mariche (Cuadrilla 5, viernes 27).</b> Por su indicación, la actividad «Intervit» corresponde a BOPA Industrial (ID 28613), que tiene un equipo vencido hace 71 días y queda fuera de las hojas por tener el mantenimiento agendado. '
 'Cable Norte Filas de Mariche (ID 29588), a unos 2 km, se añadió a la hoja de ese día. Su equipo vence el 15/12 y quedó al final del recorrido, cerca de la visita de las 15:00.',
 '<b>Lino Pérez (Cuadrilla 2, viernes 27).</b> El Cliente ID 26853 corresponde en el listado a «Albert Gamez, La Castellana», que además queda en la zona Amarilla. Conviene confirmar el ID antes de la visita.',
 '<b>Banesco Bello Monte (Cuadrilla 3, viernes 27).</b> Ocupa 6 h. Sus 9 equipos vencen el 28/11 y el 08/12, así que la visita es una buena oportunidad para hacer los mantenimientos. Banesco va en el listado de clientes grandes, ahora en la zona Azul.',
 '<b>Fernando Plaz (Cuadrilla 4, martes 1).</b> La desinstalación en La Lagunita queda en la zona Roja. La hoja de ese día se armó alrededor de las demás actividades de la Cuadrilla 4.',
 '<b>Cuadrilla 2, miércoles 2.</b> Las dos actividades (Torre BNC · Socado y Campo Alegre · Georgette Nadima Daoud) quedan en la zona Amarilla, muy cerca del límite. La hoja toma los equipos de la zona Verde más próximos a ellas.',
 '<b>Miguel Monteiro (Cuadrilla 3, lunes 30).</b> No tiene Cliente ID ni coordenadas. Su nombre se parece al cliente Miguel Monteiro (ID 28546), que en el listado queda en la zona Roja; no se usó para ubicarla.',
 '<b>Visitas que coinciden con equipos pendientes.</b> Inversiones Chudi (instalación, Cuadrilla 2, viernes 27) y Arizona Gastronómica Beta (RI, Cuadrilla 3, lunes 30) tienen equipos vencidos o próximos, y están en la hoja de ese día para resolverlos en la misma visita.',
 '<b>Colegios en el Calendario.</b> Además de los dos mantenimientos mencionados en «Lo esencial», hay una visita CC al Instituto Universitario de Diseño (viernes 27) y una CE en la Escuela Campo Alegre (miércoles 2). La Escuela tiene 32 equipos vencidos o próximos; si la visita se hace, puede servir para revisar cuándo conviene programarlos en enero.',
]
for o in obs: story.append(P(o, body))
story.append(P('<b>Clientes con mantenimiento agendado</b>', h2))
rows = [[H('Cliente'), H('ID'), H('Agenda'), H('Equipos'), H('Pendientes'), H('Mayor atraso')]]
mc['_o'] = mc.cal.str.extract(r'(\d\d)/(\d\d)').apply(lambda x: x[1] + x[0], axis=1)
for cid, r in mc.sort_values(['_o', 'cal']).iterrows():
    rows.append([P(nombre_corto(r.nombre, 55)), P(str(cid)), P(r.cal), P(str(r.activos), cellc), P(f'{r.venc} V · {r.prox} P', cellc),
                 P(f'{r.maxv} d' if r.maxv and r.maxv > 0 else '—', cellc)])
story.append(tabla(rows, [2.7 * inch, 0.55 * inch, 1.15 * inch, 0.7 * inch, 1.0 * inch, 0.9 * inch], zebra=True, extra=[('TOPPADDING', (0, 1), (-1, -1), 1.8), ('BOTTOMPADDING', (0, 1), (-1, -1), 1.8)]))
story.append(P('V = vencidos · P = próximos a vencerse. Verifique que el mantenimiento agendado cubra todos los equipos pendientes del cliente.', tiny))

# ---------- hojas
import sys; sys.path.insert(0, '/home/claude/work')
for d in DIAS:
    for q in [2, 3, 4, 5]:
        r = res[(d, q)]; Sx = r['S'].reset_index(drop=True); z = CUAD_ZONA[q]; zc = ZCOL[z]
        A = k[(k.fecha == d) & (k.cuad == q)].sort_values('INICIO').reset_index(drop=True)
        story.append(PageBreak())
        story.append(Paragraph(f'<font name="R200">{fecha_larga(d)}</font>  <font name="R600" color="{zc}">Cuadrilla {q}</font> '
                               f'<font name="R300" size="12" color="#8a8f94">· Zona {z}</font>', S('ht', size=19, lead=23, spaceAfter=2)))
        v = int((Sx['Indicador mantenimiento'] == 'Vencido').sum())
        story.append(P(f'{len(Sx)} equipos · {v} vencidos · {len(Sx)-v} próximos · {Sx["Cliente ID"].nunique()} clientes · recorrido de referencia ~{fmt(r["km"])} km · '
                       f'{fmt(r["ocup"],0)} h ocupadas en el Calendario', S('st', size=8.2, color=GRIS2, spaceAfter=5)))
        if r['llena']:
            story.append(tabla([[P('<b>Ruta llena.</b> El Calendario ya ocupa 7 h o más entre 9:00 y 17:00. Aun así se hacen las recomendaciones pertinentes, para aprovecharlas si se libera tiempo.', small)]],
                               [CW], head_color=AZUL, extra=[('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eef3f9')), ('LINEBELOW', (0, 0), (-1, 0), 0, AZUL), ('LINEBEFORE', (0, 0), (0, 0), 2, AZUL)]))
            story.append(Spacer(1, 5))
        if r['ancla']:
            ar = r['ancla_row']
            story.append(tabla([[P(f'<b>Sin actividades en el Calendario.</b> La hoja parte del equipo con más días sin mantenimiento de la zona: {nombre_corto(ar.nombre)} ({int(ar.dias_venc)} días vencido), resaltado en morado.', small)]],
                               [CW], extra=[('BACKGROUND', (0, 0), (-1, -1), MORADO_BG), ('LINEBELOW', (0, 0), (-1, 0), 0, MORADO), ('LINEBEFORE', (0, 0), (0, 0), 2, MORADO)]))
            story.append(Spacer(1, 5))
        if len(A):
            from mapas import draw_map
            arow = []
            # recomputar fuera de mapa
            Sx_ = r['S']
            for i, ar in A.iterrows():
                fuera = ''
                if pd.notna(ar.lat):
                    dm = np.min(np.hypot((Sx_.lat - ar.lat) * 111.3, (Sx_.lon - ar.lon) * 109.4))
                    if dm > 2.5: fuera = ' · fuera del mapa'
                else: fuera = ' · sin ubicar'
                if pd.notna(ar.lat) and ar.zona_act and ar.zona_act != z: fuera += f' · zona {ar.zona_act}'
                arow.append(f'<font name="R600">{chr(65+i)}</font> {ar.INICIO:%H:%M} {ar.desc.strip()}<font color="#8a8f94">{fuera}</font>')
            half = (len(arow) + 1) // 2
            story.append(tabla([[P('<br/>'.join(arow[:half]), tiny), P('<br/>'.join(arow[half:]), tiny)]], [CW / 2, CW / 2],
                               extra=[('LINEBELOW', (0, 0), (-1, 0), 0, GRIS3), ('BACKGROUND', (0, 0), (-1, -1), GRIS4)]))
            story.append(Spacer(1, 4))
        story.append(Image(f'/home/claude/work/maps/{d:%m%d}_{q}.png', width=CW, height=CW * 3.55 / 7.4))
        story.append(Spacer(1, 5))
        rows = [[H('#'), H('Cliente'), H('ID'), H('Seg.'), H('Equipo'), H('Últ. mant.'), H('Estado'), H('Dist.')]]
        ext = []
        for i, e in Sx.iterrows():
            isanc = r['ancla'] and e['g'] == r['ancla_row']['g']
            est = estado(e); ven_ = e['Indicador mantenimiento'] == 'Vencido'
            rows.append([P(f'<font color="{"#8E6BB5" if isanc else zc}"><b>{i+1}</b></font>', cellc), P(nombre_corto(e.nombre, 44)), P(str(e['Cliente ID'])),
                         P(SEG.get(e.Segmento, e.Segmento)), P(equipo_corto(e.Equipo)), P(ultimo(e)),
                         P(f'<b>{est}</b>' if ven_ else est), P(dist_txt(e.dist_act), cellr)])
            if isanc: ext.append(('BACKGROUND', (0, i + 1), (-1, i + 1), MORADO_BG))
        story.append(tabla(rows, [0.27 * inch, 2.2 * inch, 0.45 * inch, 0.45 * inch, 1.95 * inch, 0.68 * inch, 0.9 * inch, 0.5 * inch], zebra=False, head_color=colors.HexColor(zc), extra=ext))
        I = r['inact']
        foot = [f'Dist. = distancia a la actividad más cercana del día{" (o al equipo de partida)" if r["ancla"] else ""}. Los números del mapa siguen el orden de la tabla.']
        if len(I):
            items = '; '.join(f'{nombre_corto(x.nombre, 40)} ({equipo_corto(x.Equipo)}, {estado(x).lower()})' for _, x in I.iterrows())
            foot.insert(0, f'<b>Inactivos viables cerca de esta ruta</b> (círculos vacíos en el mapa): {items}.')
        for f_ in foot: story.append(Spacer(1, 3)); story.append(P(f_, tiny))

# ---------- listados aparte
story += [PageBreak(), titulo('Horeca y Corporativos con', '3 o más equipos', 20)]
story.append(P('Estos clientes no entran en las hojas. Aquí van los que tienen equipos vencidos o que vencen antes de que termine diciembre, ordenados por zona y por la proporción de equipos activos pendientes. '
               'Solo se incluyen los que tienen más del 50 % de sus equipos en esa situación.', body))
gi = L['g_in']
rows = [[H('Cliente'), H('ID'), H('Seg.'), H('Zona'), H('Equipos'), H('Pendientes'), H('%'), H('Mayor atraso'), H('Calendario')]]
for cid, r in gi.iterrows():
    rows.append([P(nombre_corto(r.nombre, 50)), P(str(cid)), P(SEG.get(r.seg, r.seg)), P(f'<font name="DJ" size="8" color="{ZCOL[r.zona]}">●</font> {r.zona}'),
                 P(f'{r.activos}' + (f' (+{r.inact} inact.)' if r.inact else ''), cellc), P(f'{r.venc} V · {r.prox} P', cellc), P(f'{r.pct*100:.0f}', cellc),
                 P(f'{r.maxv} d' if r.maxv and r.maxv > 0 else '—', cellc), P(r.cal)])
story.append(tabla(rows, [2.1 * inch, 0.45 * inch, 0.48 * inch, 0.75 * inch, 0.62 * inch, 0.85 * inch, 0.35 * inch, 0.7 * inch, 1.1 * inch], zebra=True))
go = L['g_out']
story.append(Spacer(1, 6))
story.append(P('<b>Para tener en cuenta (50 % o menos de equipos pendientes):</b> ' + '; '.join(
    f'{nombre_corto(r.nombre, 50)} ({r.venc + r.prox} de {r.activos}, zona {r.zona})' for cid, r in go.iterrows()) + '.', small))
gf = L['g_fuera']
story.append(Spacer(1, 4))
story.append(P(f'<b>Fuera de las zonas:</b> {len(gf)} clientes grandes con equipos pendientes quedan fuera de los polígonos (otras ciudades, periferia o sin coordenadas), por ejemplo ' +
               ', '.join(nombre_corto(r.nombre, 60) for _, r in gf.head(4).iterrows()) + '. No se incluyen en la propuesta.', small))
# propios
story.append(CondPageBreak(2.2 * inch))
story.append(Spacer(1, 10)); story.append(titulo('Clientes con', 'mantenimiento propio', 20))
rows = [[H('Cliente'), H('ID'), H('Zona'), H('Equipos'), H('Pendientes'), H('Mayor atraso')]]
for cid, r in L['propios'].iterrows():
    rows.append([P(nombre_corto(r.nombre, 50)), P(str(cid)), P(r.zona or '—'), P(str(r.activos), cellc), P(f'{r.venc} V · {r.prox} P', cellc), P(f'{r.maxv} d' if r.maxv and r.maxv > 0 else '—', cellc)])
story.append(tabla(rows, [2.8 * inch, 0.6 * inch, 0.9 * inch, 0.8 * inch, 1.1 * inch, 1.0 * inch], zebra=True))
story.append(P('Hacen sus propios mantenimientos, por lo que no entran en las hojas. Sus registros en Odoo aparecen vencidos porque no se cargan esas intervenciones.', tiny))
# colegios
story += [PageBreak(), titulo('Colegios y universidades', 'para enero', 20)]
story.append(P('Por indicación de esta corrida, los colegios y universidades se dejan fuera de las hojas para programarlos cuando reinicien actividades en enero, siempre que sea posible. '
               'Se identificaron por el nombre, porque el listado no trae un campo de tipo de cliente; Seguros Universitas, Instituto Nacional de Deportes, Miguel’s Comida de Colegio y el Instituto Nacional de los Espacios Acuáticos no se consideraron centros educativos.', body))
rows = [[H('Cliente'), H('ID'), H('Zona'), H('Equipos'), H('Pendientes'), H('Mayor atraso'), H('Calendario')]]
for cid, r in edu.iterrows():
    rows.append([P(nombre_corto(r.nombre, 55)), P(str(cid)), P(f'<font name="DJ" size="8" color="{ZCOL[r.zona]}">●</font> {r.zona}' if r.zona else '—'), P(str(r.activos), cellc),
                 P(f'{r.venc} V · {r.prox} P', cellc), P(f'{int(r.maxv)} d' if pd.notna(r.maxv) and r.maxv > 0 else '—', cellc), P(r.cal)])
story.append(tabla(rows, [2.7 * inch, 0.5 * inch, 0.85 * inch, 0.65 * inch, 0.95 * inch, 0.85 * inch, 0.9 * inch], zebra=True))
story.append(P('Los equipos «próximos» de esta lista vencen en diciembre; si se programan en enero, quedarían vencidos unas semanas.', tiny))

# ---------- notas sobre los datos
story += [PageBreak(), titulo('Notas sobre los', 'datos')]
cc_ = c.groupby('Cliente ID').first()
sin_coord = c[c.lat.isna() & c.elig_ind & ~c.inact]
venc_neg = sum(((r['S']['Indicador mantenimiento'] == 'Vencido') & (r['S'].dias_venc < 0)).sum() for r in res.values())
venc_neg_all = int(((c['Indicador mantenimiento'] == 'Vencido') & (c.dias_venc < 0)).sum())
mg = b['mal_geo']
mg_zona = [m for m in mg if not str(m[4]).startswith('fuera')]
mg_fuera = [m for m in mg if str(m[4]).startswith('fuera') and m[6] > 0]
ccs = c[c.lat.isna() & c.elig_ind & ~c.inact & (c.Ciudad.astype(str).str.upper().isin(['CARACAS', '(BLANK)', 'BARUTA', 'EL HATILLO', 'MIRANDA'])) & c.Estado.astype(str).str.upper().str.contains('MIRANDA|DISTRITO|BLANK')]
ccs = ccs[ccs.Segmento.isin(['HOGAR', 'HORECA', 'CORPORATIVO'])]
sc_cli, sc_eq = ccs['Cliente ID'].nunique(), len(ccs); sc_names = list(ccs.groupby('Cliente ID').first().nombre)
notas = [
 f'<b>Listado de clientes.</b> {len(c)} equipos de {c["Cliente ID"].nunique()} clientes; {int(c.elig_ind.sum())} vencidos o próximos a vencerse según Odoo y {int(c.inact.sum())} inactivos. '
 'Los días vencidos se calculan como hoy (26/11) menos la fecha del último mantenimiento (o de instalación) más la frecuencia del equipo, porque Odoo pone la fecha de hoy como próximo mantenimiento de los vencidos.',
 f'<b>Sin coordenadas.</b> {sc_cli} clientes de Caracas con {sc_eq} equipos activos vencidos o próximos tienen latitud y longitud en 0 o en blanco, y no se pueden ubicar en una zona. '
 'Entre ellos: ' + '; '.join(nombre_corto(n, 60) for n in sc_names) + '.',
 f'<b>Periferia y otras ciudades.</b> {int((c.elig_ind & ~c.inact & c.lat.notna() & c.zona.isna()).sum())} equipos activos vencidos o próximos quedan fuera de los polígonos (Los Teques, San Antonio de los Altos, Altos Mirandinos, Guarenas, litoral y otras ciudades) y no entran por ahora.',
 '<b>Ciudad o estado que no coincide con las coordenadas.</b> Los clientes de la tabla siguiente tienen en Odoo una ciudad o un estado distinto del lugar donde caen sus coordenadas. '
 'Para asignar la zona se tomaron las coordenadas; los que caen fuera de las zonas no entran. Conviene corregir el dato que esté mal en Odoo.',
 '<b>Banesco (ID 8274).</b> Sus coordenadas caen en la zona Amarilla, a unos 50 m del límite con la Azul. Por su indicación, en esta propuesta se asignó a la zona Azul, junto con Banesco Seguros y Todoticket, que comparten edificio y ya estaban en la Azul. La ubicación se corregirá en Odoo.',
 '<b>Límite Baruta – El Hatillo.</b> En esa franja los equipos se agrupan por cuadrilla según el polígono, no por municipio.',
 '<b>Cliente sin datos.</b> Hay una fila sin nombre ni segmento (ID 31704) y una de «Mercadeo Acqua Fontana» con segmento Monin; ninguna entra en las hojas.',
 '<b>Asociación Civil Benéfico-Docente San Agustín (ID 8249).</b> Por el nombre podría ser un colegio. Quedó en el listado de clientes grandes; si lo es, aplicaría para enero.',
 '<b>Mapa base.</b> Calles de OpenStreetMap (© colaboradores de OpenStreetMap). El extracto actual no cubre todo el oeste de la zona Amarilla, aunque ninguna hoja de esta semana llega a esa parte.',
]
for n in notas:
    story.append(P(n, body))
    if n.startswith('<b>Ciudad o estado'):
        rows = [[H('Cliente'), H('ID'), H('En Odoo'), H('Coordenadas'), H('Pendientes')]]
        for m in mg_zona + mg_fuera:
            donde = f'Zona {m[4]}' if not str(m[4]).startswith('fuera') else m[4].replace('fuera (', 'Fuera de las zonas, a ').replace(')', '')
            rows.append([P(nombre_corto(m[1], 55)), P(str(m[0])), P(f'{tcase(str(m[2]))} · {tcase(str(m[3]).replace(" (VE)", ""))}'), P(donde), P(str(m[6]), cellc)])
        story.append(tabla(rows, [2.6 * inch, 0.55 * inch, 1.9 * inch, 1.65 * inch, 0.7 * inch], zebra=True)); story.append(Spacer(1, 6))
doc.build(story)
print('PDF ok')
