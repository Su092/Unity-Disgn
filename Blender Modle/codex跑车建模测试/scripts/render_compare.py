# -*- coding: utf-8 -*-
"""透明背景的侧/前剪影渲染，供参考图比例对照。"""

import bpy
import math
import os

from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "renders")


def look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "out", "sports_car.blend"))
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        sc.render.engine = "BLENDER_EEVEE"
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.55, 0.56, 0.58, 1.0)
    bg.inputs["Strength"].default_value = 1.0

    sun = bpy.data.objects.new("GEO-Sun", bpy.data.lights.new("Sun", "SUN"))
    sc.collection.objects.link(sun)
    sun.data.energy = 4.0
    sun.rotation_euler = (math.radians(48), 0.0, math.radians(-35))

    cam = bpy.data.objects.new("GEO-Camera", bpy.data.cameras.new("Camera"))
    sc.collection.objects.link(cam)
    sc.camera = cam

    def shoot(name, loc, target, ortho, res):
        sc.render.resolution_x, sc.render.resolution_y = res
        cam.location = Vector(loc)
        look_at(cam, target)
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho
        sc.render.filepath = os.path.join(OUT, name)
        bpy.ops.render.render(write_still=True)
        print("[render] %s" % sc.render.filepath)

    shoot("side-cut.png", (0.0, -9.5, 0.62), (0.0, 0.0, 0.62), 5.2, (1024, 576))
    shoot("front-cut.png", (9.0, 0.0, 0.62), (0.0, 0.0, 0.62), 2.8, (800, 600))


if __name__ == "__main__":
    main()
