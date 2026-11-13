# -*- coding: utf-8 -*-
"""Re-fit the hero camera on the saved scene for several lens/az/el values.

  blender -b enemy_crawler.blend --python tune_camera.py
Prints the projected feature bboxes and their error against the reference.
"""
import bpy, math, sys
from mathutils import Vector

RES = 1254
REF = {
    "whole":     (30, 1200, 223, 1152),
    "blue":      (689, 954, 330, 478),
    "visor":     (816, 1150, 654, 748),
    "bandL":     (89, 644, 520, 723),
    "cowl_head": (690, 1170, 459, 870),
    "legBLband": (56, 186, 778, 845),
    "legFLband": (387, 544, 882, 955),
    "legFRband": (1047, 1161, 888, 944),
}
GROUPS = {
    "whole": [("all", None)],
    "hull": [("obj", "GEO-crawler-hull")],
    "cowl": [("obj", "GEO-crawler-cowl")],
    "visor": [("obj", "GEO-crawler-visor")],
    "bandL": [("obj", "DECAL-band-L")],
    "blue": [("obj", "DECAL-blue-1"), ("obj", "DECAL-blue-2")],
    "legBLband": [("leg", ("BL", 8, 16))],
    "legFLband": [("leg", ("FL", 8, 16))],
    "legFRband": [("leg", ("FR", 8, 16))],
    "legBRband": [("leg", ("BR", 8, 16))],
}


def gather(objs, spec):
    pts = []
    for kind, arg in spec:
        if kind == "all":
            for ob in bpy.data.collections["COL_Crawler"].objects:
                mw = ob.matrix_world
                pts += [mw @ v.co for v in ob.data.vertices]
        elif kind == "obj":
            ob = bpy.data.objects[arg]
            mw = ob.matrix_world
            pts += [mw @ v.co for v in ob.data.vertices]
        else:
            nm, a, b = arg
            ob = bpy.data.objects["GEO-crawler-leg-%s" % nm]
            mw = ob.matrix_world
            pts += [mw @ ob.data.vertices[i].co for i in range(a, b)]
    return pts


def place(cam, az, el, target, dist, lens):
    cam.data.lens = lens
    a, e = math.radians(az), math.radians(el)
    d = Vector((-math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    cam.location = target + d * dist
    cam.rotation_euler = (target - cam.location).normalized().to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()


def projbox(cam, pts):
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    xs, ys = [], []
    for p in pts:
        co = world_to_camera_view(sc, cam, p)
        xs.append(co.x * RES)
        ys.append((1.0 - co.y) * RES)
    return [round(min(xs)), round(max(xs)), round(min(ys)), round(max(ys))]


def run(az, el, lens):
    sc = bpy.context.scene
    cam = sc.camera
    cam.data.shift_x = 0.0
    cam.data.shift_y = 0.0
    allpts = gather(None, GROUPS["whole"])
    mn = Vector((min(p.x for p in allpts), min(p.y for p in allpts), min(p.z for p in allpts)))
    mx = Vector((max(p.x for p in allpts), max(p.y for p in allpts), max(p.z for p in allpts)))
    target = (mn + mx) * 0.5
    tw = REF["whole"][1] - REF["whole"][0]
    th = REF["whole"][3] - REF["whole"][2]
    lo, hi = 1.0, 80.0
    for _ in range(50):
        dist = 0.5 * (lo + hi)
        place(cam, az, el, target, dist, lens)
        b = projbox(cam, allpts)
        frac = max((b[1] - b[0]) / tw, (b[3] - b[2]) / th)
        if frac > 1.0:
            lo = dist
        else:
            hi = dist
    dist = 0.5 * (lo + hi)
    place(cam, az, el, target, dist, lens)
    b = projbox(cam, allpts)
    rcx = (REF["whole"][0] + REF["whole"][1]) * 0.5
    rcy = (REF["whole"][2] + REF["whole"][3]) * 0.5
    cam.data.shift_x += ((b[0] + b[1]) * 0.5 - rcx) / RES
    cam.data.shift_y -= ((b[2] + b[3]) * 0.5 - rcy) / RES
    bpy.context.view_layer.update()

    out, err = {}, 0.0
    for k, spec in GROUPS.items():
        bb = projbox(cam, gather(None, spec))
        out[k] = bb
        if k in REF:
            r = REF[k]
            e = sum(abs(bb[i] - r[i]) for i in range(4))
            if k in ("visor", "blue", "bandL", "legBLband", "legFLband", "legFRband"):
                err += e
    asp = (out["whole"][3] - out["whole"][2]) / float(out["whole"][1] - out["whole"][0])
    return dist, asp, err, out


def main():
    print("az   el  lens  dist  asp(ref .794) err  | legBL legFL legFR marks")
    best = None
    for az in (40.0, 43.0, 46.0):
        for el in (12.0, 15.0, 18.0):
            for lens in (120.0, 180.0, 260.0):
                dist, asp, err, out = run(az, el, lens)
                tag = "BL%s FL%s FR%s V%s B%s" % (
                    out["legBLband"][2:], out["legFLband"][2:],
                    out["legFRband"][2:], out["visor"][2:], out["bandL"][2:])
                print("%4.1f %4.1f %5.0f %5.2f %.3f %5.0f | %s" % (az, el, lens, dist, asp, err, tag))
                if best is None or err < best[0]:
                    best = (err, az, el, lens, dist, asp)
    print("BEST err=%.0f az=%.1f el=%.1f lens=%.0f dist=%.2f aspect=%.3f" % best)


main()

