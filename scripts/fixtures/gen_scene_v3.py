# Generator fixture scen v3 (scene_good_v3 / scene_bad_v3). Uruchamiany recznie
# przez konfiguratora; fixtures sa commitowane, generator dla powtarzalnosci.
import importlib.util, math
from pathlib import Path

FX = Path(__file__).resolve().parent

def load(rel):
    p = FX / rel
    spec = importlib.util.spec_from_file_location("fx_" + p.stem + p.parent.name, p)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

terr = load("parts_good_v3/terrain.py")
house = load("parts_good_v3/house.py")
wall = load("parts_good_v3/wall.py")
chapel = load("parts_good_v3/chapel.py")
bridge = load("parts_good_v3/bridge.py")
barrel = load("parts_good_v3/prop_barrel.py")
crate = load("parts_good_v3/prop_crate.py")
bush = load("parts_good_v3/bush.py")
pier = load("parts_good_v2/pier.py")
boat = load("parts_good_v2/boat.py")
tree = load("parts_good_v2/tree.py")
rocks = load("parts_good_v2/rocks.py")

A, B = terr.A, terr.B
tg = terr.build()[0]
TV = tg["vertices"]

def nearest_y(x, z):
    return min(TV, key=lambda v: (v[0]-x)**2 + (v[2]-z)**2)[1]

def tr(groups, dx, dy, dz, rot90=False, rename=None):
    out = []
    for i, g in enumerate(groups):
        vs = []
        for (x, y, z) in g["vertices"]:
            if rot90: x, z = z, x
            vs.append((x+dx, y+dy, z+dz))
        nm = rename if rename and len(groups) == 1 else ((rename or g["name"]) + ("" if len(groups)==1 else "_%d" % (i+1)))
        out.append({"name": nm, "vertices": vs, "faces": g["faces"], "colors": g["colors"]})
    return out

def ell(r, phi_deg):
    a = math.radians(phi_deg)
    return (A*r*math.cos(a), B*r*math.sin(a))

def crossing(name, cx, cz, y0, y1, hw, colors):
    mats = list(colors)
    vs = [(cx-hw,y0,cz),(cx+hw,y0,cz),(cx+hw,y1,cz),(cx-hw,y1,cz),
          (cx,y0,cz-hw),(cx,y0,cz+hw),(cx,y1,cz+hw),(cx,y1,cz-hw)]
    fs = [(mats[0],(0,1,2,3)),(mats[-1],(4,5,6,7))]
    return [{"name": name, "vertices": vs, "faces": fs, "colors": colors}]

def build_scene(with_chapel=True, with_beach_boat=True):
    G = []
    G += tr([tg], 0,0,0, rename="terrain")
    G.append({"name":"water","vertices":[(-50,0,-40),(50,0,-40),(50,0,40),(-50,0,40)],
              "faces":[("sea",(0,1,2,3))],"colors":{"sea":(0.16,0.28,0.48)}})
    G += crossing("lighthouse_tower", 0, 0, 8.9, 35.0, 1.5,
                  {"lh_white":(0.92,0.92,0.9),"lh_red":(0.75,0.2,0.18)})
    archs = ["timber","stone","two_story"]
    spots = [(0.45,70),(0.45,95),(0.45,120),(0.45,148),(0.45,176),(0.45,204),
             (0.66,100),(0.66,125),(0.66,150)]
    for k,(r,phi) in enumerate(spots):
        a = archs[k % 3]
        x,z = ell(r,phi)
        ty = nearest_y(x,z)
        w = 5.6 + 0.2*(k % 4)
        G += tr(house.build(archetype=a, width=w), x, ty, z,
                rename="house_%d_%s" % (k+1, a))
    for k,(r,phi) in enumerate([(0.5,40),(0.5,225)]):
        x,z = ell(r,phi)
        G += tr(wall.build(), x, nearest_y(x,z), z, rename="wall_%d" % (k+1))
    x,z = ell(0.6,210)
    G += tr(wall.build(), x, nearest_y(x,z), z, rename="stair_1")
    if with_chapel:
        tx,tz = terr.TURNIA
        G += tr(chapel.build(), tx, nearest_y(tx,tz), tz, rename="chapel_1")
        G += tr(bridge.build(), 21.5, 4.5, -5.0, rename="bridge_1")
        wx,wz = 19.0, -4.0
        G += tr(wall.build(length=6.0), wx, nearest_y(wx,wz), wz, rename="wall_3")
    for k,px in enumerate((-6.0, 8.0)):
        G += tr(pier.build(), px, 0, -39.5, rot90=True, rename="pier_%d" % (k+1))
    for k in range(4):
        x = -4.5 + 3.0*k
        z = -24.6
        G += tr(barrel.build(), x, nearest_y(x,z), z, rename="barrel_%d" % (k+1))
    for k in range(3):
        x = -3.0 + 3.0*k
        z = -23.2
        G += tr(crate.build(), x, nearest_y(x,z), z, rename="crate_%d" % (k+1))
    for k in range(8):
        r,phi = (0.5, 60+18*k)
        x,z = ell(r,phi)
        x += 2.5
        G += tr(bush.build(scale=0.8+0.07*k), x, nearest_y(x,z), z, rename="bush_%d" % (k+1))
    G += tr(boat.build(), -3.0, 0, -33.0, rename="boat_1")
    G += tr(boat.build(length=4.0), 25.0, 0, 35.0, rename="boat_2")
    if with_beach_boat:
        G += tr(boat.build(length=3.2), 3.0, nearest_y(3.0,-25.0)+0.3, -25.0, rename="boat_3")
    for k in range(6):
        r,phi = 0.62, 20+12*k
        x,z = ell(r,phi)
        G += tr(tree.build(height=4.0+0.35*k), x, nearest_y(x,z), z, rename="tree_%d" % (k+1))
    rgs = rocks.build(count=10, seed=5)
    for k,rg in enumerate(rgs):
        if k < 8:
            x,z = ell(1.06, 36*k)
            y = -0.5
        else:
            x,z = ell(0.52, 250+20*k)
            y = nearest_y(x,z)
        G += tr([rg], x, y, z, rename="rock_%d" % (k+1))
    ax,az = -6.0, -25.0
    bx,bz = 0.0, -2.2
    pverts, pfaces = [], []
    n = 18
    for i in range(n):
        t0,t1 = i/n,(i+1)/n
        x0,z0 = ax+(bx-ax)*t0, az+(bz-az)*t0
        x1,z1 = ax+(bx-ax)*t1, az+(bz-az)*t1
        ux,uz = (bz-az),-(bx-ax)
        ul = math.hypot(ux,uz); ux,uz = ux/ul*0.5, uz/ul*0.5
        b = len(pverts)
        pverts += [(x0-ux, nearest_y(x0-ux,z0-uz)+0.1, z0-uz),
                   (x0+ux, nearest_y(x0+ux,z0+uz)+0.1, z0+uz),
                   (x1+ux, nearest_y(x1+ux,z1+uz)+0.1, z1+uz),
                   (x1-ux, nearest_y(x1-ux,z1-uz)+0.1, z1-uz)]
        pfaces.append(("path_%d" % (i%2), (b,b+1,b+2,b+3)))
    G.append({"name":"path_1","vertices":pverts,"faces":pfaces,
              "colors":{"path_0":(0.62,0.58,0.50),"path_1":(0.58,0.54,0.47)}})
    return G

def write_obj(path, groups, mtlname):
    mats = {}
    lines = ["mtllib %s" % mtlname]
    off = 1
    for g in groups:
        ns = {}
        for m,rgb in g["colors"].items():
            nm = "%s_%s" % (g["name"], m); ns[m]=nm; mats[nm]=rgb
        lines.append("o "+g["name"])
        for v in g["vertices"]:
            lines.append("v %.4f %.4f %.4f" % v)
        cur=None
        for m,idxs in g["faces"]:
            if ns[m]!=cur:
                cur=ns[m]; lines.append("usemtl "+cur)
            lines.append("f "+" ".join(str(off+i) for i in idxs))
        off += len(g["vertices"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    mtl = []
    for nm, rgb in mats.items():
        mtl += ["newmtl " + nm, "Kd %.3f %.3f %.3f" % rgb, ""]
    (path.parent / mtlname).write_text("\n".join(mtl), encoding="utf-8")

if __name__ == "__main__":
    write_obj(FX/"scene_good_v3.obj", build_scene(), "scene_good_v3.mtl")
    write_obj(FX/"scene_bad_v3.obj", build_scene(with_chapel=False, with_beach_boat=False), "scene_bad_v3.mtl")
    print("scene v3 fixtures written")
