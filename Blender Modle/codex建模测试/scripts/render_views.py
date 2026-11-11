# -*- coding: utf-8 -*-
"""给教堂模型出受控尺寸的 QC 渲染：hero / side / west。"""

import bpy
import math
import os
import sys

from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "renders")
os.makedirs(OUT, exist_ok=True)


def look_at(cam, target):
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def add_ground():
    me = bpy.data.meshes.new("MESH-Ground")
    me.from_pydata([(-60, -60, 0), (60, -60, 0), (60, 60, 0), (-60, 60, 0)], [], [(0, 1, 2, 3)])
    obj = bpy.data.objects.new("GEO-Ground", me)
    bpy.context.scene.collection.objects.link(obj)
    mat = bpy.data.materials.new("M_Ground")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.18, 0.18, 0.18, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.9
    obj.data.materials.append(mat)
    return obj


def setup():
    sc = bpy.context.scene
    sc.render.resolution_x = 960
    sc.render.resolution_y = 540
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        sc.render.engine = "BLENDER_EEVEE"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("World")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes.get("Background")
    bg.inputs["Color"].default_value = (0.55, 0.56, 0.58, 1.0)
    bg.inputs["Strength"].default_value = 0.85

    # 单侧强太阳 + 很弱的环境光
    sun = bpy.data.objects.new("GEO-Sun", bpy.data.lights.new("Sun", "SUN"))
    sc.collection.objects.link(sun)
    sun.data.energy = 4.5
    sun.data.angle = math.radians(2.0)
    sun.rotation_euler = (math.radians(52), 0.0, math.radians(-38))

    cam = bpy.data.objects.new("GEO-Camera", bpy.data.cameras.new("Camera"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def shoot(cam, name, loc, target, ortho=None, res=(960, 540)):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = Vector(loc)
    look_at(cam, target)
    if ortho is not None:
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"
        cam.data.lens = 48
    path = os.path.join(OUT, name)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[render] %s" % path)


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, "out", "church.blend"))
    add_ground()
    cam = setup()
    # 英雄机位：看得到西塔 + 南侧长墙
    shoot(cam, "hero.png", (-38.0, -52.0, 22.0), (10.0, 0.0, 11.0))
    # 南侧正立面
    shoot(cam, "side.png", (13.0, -55.0, 12.0), (13.0, 0.0, 12.0), ortho=36.0,
          res=(1024, 768))
    # 西立面
    shoot(cam, "west.png", (-40.0, 0.0, 12.5), (2.0, 0.0, 12.5), ortho=30.0,
          res=(600, 900))


if __name__ == "__main__":
    main()
