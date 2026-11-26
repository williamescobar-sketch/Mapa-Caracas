import sqlite3, struct, pickle, numpy as np
from shapely import wkb
from shapely.geometry import box
G='/home/claude/Mapa-Caracas-main/planet_-67.046,10.371_-66.703,10.574.gpkg'
con=sqlite3.connect(G)
def geom(blob):
    flags=blob[3]; env=(flags>>1)&7
    off=8+{0:0,1:32,2:48,3:48,4:64}[env]
    return wkb.loads(bytes(blob[off:]))
KEEP={'motorway','trunk','primary','secondary','tertiary','residential','unclassified','living_street',
      'motorway_link','trunk_link','primary_link','secondary_link','tertiary_link'}
roads=[]
for gb,name,hw in con.execute("select geom,name,highway from lines where highway is not null"):
    if hw not in KEEP: continue
    g=geom(gb); roads.append((hw,name,np.array(g.coords)))
parks=[]
for gb,lei,oth in con.execute("select geom,leisure,landuse from multipolygons where leisure in ('park','nature_reserve') or landuse in ('grass','forest','recreation_ground')"):
    try:
        g=geom(gb)
        for p in getattr(g,'geoms',[g]):
            if p.area>2e-6: parks.append(np.array(p.exterior.coords))
    except Exception: pass
print(len(roads),len(parks))
pickle.dump(dict(roads=roads,parks=parks),open('/home/claude/work/osm.pkl','wb'))
