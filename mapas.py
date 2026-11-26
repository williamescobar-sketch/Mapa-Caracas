import pickle, numpy as np, pandas as pd, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from pyproj import Transformer
for w in [300,400,600]: fm.fontManager.addfont(f'/home/claude/fonts/Raleway-W{w}.ttf')
plt.rcParams['font.family']='Raleway-W400'
osm=pickle.load(open('/home/claude/work/osm.pkl','rb')); b=pickle.load(open('/home/claude/work/base.pkl','rb'))
a=pickle.load(open('/home/claude/work/asig.pkl','rb')); res=a['res']; k=b['k']; Z=b['Z']
ZCOL={'Verde':'#6BA368','Azul':'#4A7FB5','Amarilla':'#D4A72C','Roja':'#C9584C'}
CUAD_ZONA={2:'Verde',3:'Azul',4:'Amarilla',5:'Roja'}
MORADO='#8E6BB5'
RW={'motorway':1.6,'trunk':1.5,'primary':1.2,'secondary':1.0,'tertiary':0.8}
RC={'motorway':'#9aa0a6','trunk':'#9aa0a6','primary':'#a6acb2','secondary':'#adb2b8','tertiary':'#b4b9be'}
# road arrays with bboxes
roads=[(hw,nm,c,(c[:,0].min(),c[:,0].max(),c[:,1].min(),c[:,1].max())) for hw,nm,c in osm['roads']]
def draw_map(key, out, W=7.4, H=3.55):
    d,q=key; r=res[key]; S=r['S']; zona=CUAD_ZONA[q]; col=ZCOL[zona]
    A=k[(k.fecha==d)&(k.cuad==q)].sort_values('INICIO').reset_index(drop=True)
    A['letra']=[chr(65+i) for i in range(len(A))]
    Ap=A[A.lat.notna()].copy()
    if len(Ap):
        dmin=[np.min(np.hypot((S.lat-la)*111.3,(S.lon-lo)*109.4)) for la,lo in zip(Ap.lat,Ap.lon)]
        Ap['dentro']=np.array(dmin)<=2.5
    else: Ap['dentro']=[]
    A['fuera_mapa']=A.index.isin(Ap.index[~Ap['dentro']]) if len(Ap) else False
    Ap=Ap[Ap['dentro'].astype(bool).values] if len(Ap) else Ap
    lons=list(S.lon)+list(Ap.lon); lats=list(S.lat)+list(Ap.lat)
    x0,x1=min(lons),max(lons); y0,y1=min(lats),max(lats)
    pad=max(x1-x0,y1-y0)*0.12+0.004
    x0-=pad;x1+=pad;y0-=pad;y1+=pad
    # aspect (lon degrees ~ 0.984 lat degree at 10.5)
    asp=W/H; f=np.cos(np.radians(10.48))
    wx=(x1-x0)*f; hy=y1-y0
    if wx/hy<asp:
        extra=(hy*asp/f-(x1-x0))/2; x0-=extra; x1+=extra
    else:
        extra=((x1-x0)*f/asp-hy)/2; y0-=extra; y1+=extra
    fig=plt.figure(figsize=(W,H),dpi=200); ax=fig.add_axes([0,0,1,1]); ax.set_xlim(x0,x1); ax.set_ylim(y0,y1)
    ax.set_aspect(1/f); ax.axis('off'); fig.patch.set_facecolor('white')
    for p in osm['parks']:
        if p[:,0].max()<x0 or p[:,0].min()>x1 or p[:,1].max()<y0 or p[:,1].min()>y1: continue
        ax.fill(p[:,0],p[:,1],color='#edf1ea',lw=0,zorder=0)
    span=x1-x0
    labels=[]
    for hw,nm,c,(a0,a1,b0,b1) in roads:
        if a1<x0 or a0>x1 or b1<y0 or b0>y1: continue
        base=hw.replace('_link','')
        lw=RW.get(base,0.45)*(0.9 if span<0.06 else 0.6); cc=RC.get(base,'#c9cdd1')
        ax.plot(c[:,0],c[:,1],color=cc,lw=lw,zorder=1,solid_capstyle='round')
        if base in ('primary','secondary','trunk','motorway') and nm and len(c)>2:
            L=np.hypot(np.diff(c[:,0]),np.diff(c[:,1])).sum()
            if L>span*0.12: labels.append((L,nm,c))
    # zone polygons
    for zn,g in Z.items():
        for poly in getattr(g,'geoms',[g]):
            xs,ys=poly.exterior.xy
            if zn==zona:
                ax.fill(xs,ys,color=col,alpha=0.07,lw=0,zorder=2); ax.plot(xs,ys,color=col,lw=1.6,alpha=0.85,zorder=3)
            else:
                ax.plot(xs,ys,color='#9a9a9a',lw=0.8,ls=(0,(3,2)),alpha=0.7,zorder=3)
    # labels of streets (few)
    used=[]
    for L,nm,c in sorted(labels,key=lambda t:-t[0])[:7]:
        if nm in used: continue
        m=len(c)//2; xm,ym=c[m]
        if not(x0<xm<x1 and y0<ym<y1): continue
        dx=c[min(m+1,len(c)-1),0]-c[m-1,0]; dy=(c[min(m+1,len(c)-1),1]-c[m-1,1])
        ang=np.degrees(np.arctan2(dy,dx*f)); ang=ang-180 if ang>90 else (ang+180 if ang<-90 else ang)
        ax.text(xm,ym,nm,fontsize=4.6,color='#8a9096',rotation=ang,ha='center',va='center',zorder=4,family='Raleway-W400')
        used.append(nm)
    # route
    start=[(Ap.lon.iloc[0],Ap.lat.iloc[0])] if len(Ap) else []
    S2=S.reset_index(drop=True); S2['n']=np.arange(1,len(S2)+1)
    locs=S2.groupby('g',sort=False).agg(ns=('n',list),lat=('lat','mean'),lon=('lon','mean')).reset_index()
    path=start+list(zip(locs.lon,locs.lat))
    if len(path)>1:
        ax.plot([p[0] for p in path],[p[1] for p in path],color='#6f7880',lw=0.8,ls=(0,(2,1.5)),zorder=5,alpha=0.8)
    # activities
    placed=[]
    for _,row in Ap.iterrows():
        near=np.min(np.hypot((locs.lat-row.lat)*111300,(locs.lon-row.lon)*109400)) if len(locs) else 1e9
        lx,ly=row.lon,row.lat
        k2=sum(1 for p in placed if np.hypot((p[0]-row.lon)*109400,(p[1]-row.lat)*111300)<120)
        if near<150 or k2:
            off=(x1-x0)*0.022; lx=row.lon-off*(1+0.9*k2); ly=row.lat+off*0.55/f
            ax.plot([row.lon,lx],[row.lat,ly],color='#4d5359',lw=0.6,zorder=11)
            ax.scatter(row.lon,row.lat,s=6,color='#4d5359',zorder=11)
        placed.append((row.lon,row.lat))
        ax.scatter(lx,ly,marker='s',s=70,color='#4d5359',edgecolor='white',lw=0.8,zorder=12)
        ax.text(lx,ly,row.letra,color='white',fontsize=5.5,ha='center',va='center',zorder=13,family='Raleway-W600')
    # equipment clusters
    anc = r['ancla_row'] if r['ancla'] else None
    for _,l in locs.iterrows():
        isanc = anc is not None and l.g==anc.g
        cc = MORADO if isanc else col
        ns=l.ns; lab=str(ns[0]) if len(ns)==1 else (f'{ns[0]}–{ns[-1]}' if ns[-1]-ns[0]==len(ns)-1 else ','.join(map(str,ns)))
        sz=95 if len(lab)<=2 else 95+len(lab)*22
        ax.scatter(l.lon,l.lat,s=sz,color=cc,edgecolor='white',lw=0.9,zorder=9)
        ax.text(l.lon,l.lat,lab,color='white',fontsize=5.2 if len(lab)<=2 else 4.4,ha='center',va='center',zorder=10,family='Raleway-W600')
    # inactive hollow
    I=r['inact']
    for _,l in I.drop_duplicates(['lat','lon']).iterrows():
        ax.scatter(l.lon,l.lat,s=40,facecolor='white',edgecolor=col,lw=1.0,zorder=6)
    # scale bar ~ 500 m / 1 km
    km_deg=1/(111.32*f); L=1.0 if span>0.05 else 0.5
    sx=x0+(x1-x0)*0.03; sy=y0+(y1-y0)*0.05
    ax.plot([sx,sx+L*km_deg],[sy,sy],color='#555',lw=1.2,zorder=11)
    ax.text(sx+L*km_deg/2,sy+(y1-y0)*0.02,('1 km' if L==1 else '500 m'),fontsize=5,ha='center',color='#555',zorder=11)
    ax.text(x1-(x1-x0)*0.005,y0+(y1-y0)*0.012,'© colaboradores de OpenStreetMap',fontsize=4,ha='right',color='#8a8a8a',zorder=11)
    for s in ['top','bottom','left','right']: pass
    fig.savefig(out,dpi=200,facecolor='white'); plt.close(fig)
    return A
if __name__=='__main__':
    import os; os.makedirs('/home/claude/work/maps',exist_ok=True)
    for key in res:
        d,q=key; draw_map(key,f'/home/claude/work/maps/{d:%m%d}_{q}.png')
    print('ok')
