"""细节特写：直接开 out/taxi.blend，用已有相机/灯光渲若干近距离机位，用于验收细节。

用法：
    blender -b --factory-startup --python scripts/detail_shots.py
产物落到 renders/detail-*.png。
"""
import bpy, os
from mathutils import Vector

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.open_mainfile(filepath=os.path.join(root, "out", "taxi.blend"))

sc = bpy.context.scene
cam = bpy.data.objects.get("CAM_Studio") or next(o for o in bpy.data.objects if o.type == "CAMERA")
sc.camera = cam
cam.data.type = "PERSP"
sc.render.image_settings.file_format = "PNG"
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        continue
try:
    sc.eevee.taa_render_samples = 32
except Exception:
    pass


def aim(loc, target, lens):
    cam.data.lens = lens
    cam.location = Vector(loc)
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


# name, 机位, 目标, 焦距, 宽, 高
SHOTS = [
    ("detail-front",      (4.30, -3.90, 1.65), (1.75, 0.00, 0.72), 50.0, 900, 560),
    ("detail-front-close", (3.05, -1.95, 1.00), (2.42, -0.10, 0.66), 62.0, 900, 560),
    ("detail-rear",       (-4.90, -3.60, 1.55), (-1.85, 0.00, 0.66), 50.0, 900, 560),
    ("detail-rear-close", (-3.10, -1.85, 1.00), (-2.48, -0.05, 0.62), 62.0, 900, 560),
    ("detail-wheel",      (2.85, -2.30, 0.85), (1.60, -0.72, 0.44), 50.0, 900, 560),
    ("detail-roof",       (2.60, -2.55, 2.75), (-0.10, -0.15, 1.50), 50.0, 900, 560),
    ("detail-nose",       (9.60, 0.60, 1.10), (2.45, 0.00, 0.72), 85.0, 900, 560),
    ("detail-tail",       (-9.60, -0.60, 1.05), (-2.50, 0.00, 0.66), 85.0, 900, 560),
]

for name, loc, tgt, lens, w, h in SHOTS:
    aim(loc, tgt, lens)
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.filepath = os.path.join(root, "renders", name + ".png")
    bpy.ops.render.render(write_still=True)
    print("[shot] %s -> %s" % (name, sc.render.filepath))
