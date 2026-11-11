# -*- coding: utf-8 -*-
"""跑车 QC 渲染：hero / side / front / rear34。"""

import bpy
import math
import os

from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "renders")
os.makedirs(OUT, exist_ok=True)


def look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def setup():
    sc = bpy.context.scene
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        sc.render.engine = "BLENDER_EEVEE"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.55, 0.56, 0.58, 1.0)
    bg.inputs["Strength"].default_value = 1.0

    sun = bpy.data.objects.new("GEO-Sun", bpy.data.lights.new("Sun", "SUN"))
    sc.collection.objects.link(sun)
    sun.data.energy = 4.0
    sun.data.angle = math.radians(4.0)
    sun.rotation_euler = (math.radians(48), 0.0, math.radians(-35))

    area = bpy.data.objects.new("GEO-Fill", bpy.data.lights.new("Fill", "AREA"))
    sc.collection.objects.link(area)
    area.data.energy = 450
    area.data.size = 6.0
    area.location = (4.0, -4.0, 6.0)
    area.rotation_euler = (math.radians(30), 0.0, math.radians(45))

    me = bpy.data.meshes.new("MESH-Ground")
    me.from_pydata([(-20, -20, 0), (20, -20, 0), (20, 20, 0), (-20, 20, 0)], [], [(0, 1, 2, 3)])
    ground = bpy.data.objects.new("GEO-Ground", me)
    sc.collection.objects.link(ground)
    mat = bpy.data.materials.new("M_Ground")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.16, 0.16, 0.16, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.85
    ground.data.materials.append(mat)

    cam = bpy.data.objects.new("GEO-Camera", bpy.data.cameras.new("Camera"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def shoot(cam, name, loc, target, ortho=None, res=(960, 540), lens=50):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = Vector(loc)
    look_at(cam, target)
    if ortho is not None:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"
        cam.data.lens = lens
    path = os.path.join(OUT, name)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render] %s" % path)


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "out", "sports_car.blend"))
    cam = setup()
    shoot(cam, "hero.png", (5.6, -7.8, 3.2), (0.0, 0.0, 0.62), lens=52)
    shoot(cam, "side.png", (0.0, -9.5, 1.0), (0.0, 0.0, 0.62), ortho=5.2,
          res=(1024, 576))
    shoot(cam, "front.png", (9.0, 0.0, 0.72), (0.0, 0.0, 0.72), ortho=2.8,
          res=(800, 600))
    shoot(cam, "rear34.png", (-5.4, -7.8, 3.0), (0.0, 0.0, 0.62), lens=52)


if __name__ == "__main__":
    main()
