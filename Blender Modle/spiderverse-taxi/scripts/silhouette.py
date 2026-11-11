# -*- coding: utf-8 -*-
"""剪影渲染：把整车渲成"纯黑车身 + 纯白底"的侧视正交图，供 measure_ref 数值比对。

为什么要这一步：对着渲染图目测轮廓没有可复算的判据；剪影图的 H/L、轮径比、
轮廓采样点可以直接和参考图用同一套量测脚本对拍。

用法：
  blender -b --factory-startup --python scripts/silhouette.py -- \
      <blend> <objName> <out.png> [ortho_scale]
"""

import sys
import os

import bpy

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []
blend, obj_name, out = argv[0], argv[1], argv[2]
ortho = float(argv[3]) if len(argv) > 3 else 6.2

bpy.ops.wm.open_mainfile(filepath=blend)

obj = bpy.data.objects[obj_name]
for o in bpy.data.objects:
    if o.type == "MESH" and o is not obj:
        o.hide_render = True

# 纯黑自发光覆盖全部材质
black = bpy.data.materials.new("M_Silhouette")
black.use_nodes = True
nt = black.node_tree
for n in [n for n in nt.nodes if n.type != "OUTPUT_MATERIAL"]:
    nt.nodes.remove(n)
outn = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
emis = nt.nodes.new("ShaderNodeEmission")
emis.inputs["Color"].default_value = (0, 0, 0, 1)
emis.inputs["Strength"].default_value = 1.0
nt.links.new(emis.outputs["Emission"], outn.inputs["Surface"])

obj.data.materials.clear()
obj.data.materials.append(black)
for p in obj.data.polygons:
    p.material_index = 0

world = bpy.context.scene.world or bpy.data.worlds.new("W")
bpy.context.scene.world = world
world.use_nodes = True
wnt = world.node_tree
for n in [n for n in wnt.nodes if n.type != "OUTPUT_WORLD"]:
    wnt.nodes.remove(n)
wout = next(n for n in wnt.nodes if n.type == "OUTPUT_WORLD")
bg = wnt.nodes.new("ShaderNodeBackground")
bg.inputs["Color"].default_value = (1, 1, 1, 1)
bg.inputs["Strength"].default_value = 1.0
wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

cam = bpy.data.objects.get("Cam")
if cam is None:
    cd = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cd)
    bpy.context.scene.collection.objects.link(cam)
bpy.context.scene.camera = cam
cam.data.type = "ORTHO"
cam.data.ortho_scale = ortho
cam.location = (0.0, -12.0, obj.dimensions.z * 0.0 + 0.6)
cam.rotation_euler = (1.5707963, 0.0, 0.0)

sc = bpy.context.scene
for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
    try:
        sc.render.engine = eng
        break
    except TypeError:
        continue
sc.render.resolution_x, sc.render.resolution_y = 1600, 900
sc.render.image_settings.file_format = "PNG"
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("[sil] %s -> %s" % (obj_name, out))
