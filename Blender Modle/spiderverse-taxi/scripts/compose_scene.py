# -*- coding: utf-8 -*-
"""同场景合成：出租车 + 红色复古跑车，风格化 lookdev。

打开 out/taxi.blend，把 out/sportscar.blend 的 GEO-SportSpider 追加进来，
放到 location=(0, 3.2, 0)（见 sportscar-spec.md §2），两边都套上
阶调 / inverted-hull 描边 / 网点 / 色散，渲双车英雄机位。

用法：
  blender -b --factory-startup --python scripts/compose_scene.py
产物：
  out/duo.blend
  renders/duo-hero.png / duo-side.png / duo-rear34.png / duo-overhead.png
"""

import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lookdev_taxi as L  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(ROOT, "renders")
SPORT_OFFSET = (-6.5, 0.0, 0.0)  # 规格冻结：沿 X 左右并排（−Y 机位下 −X 在画面左侧）


def append_object(blend_path, obj_name):
    directory = os.path.join(blend_path, "Object") + os.sep
    before = set(bpy.data.objects.keys())
    bpy.ops.wm.append(filepath=os.path.join(directory, obj_name),
                      directory=directory, filename=obj_name, link=False)
    added = [n for n in bpy.data.objects.keys() if n not in before]
    if obj_name in bpy.data.objects:
        return bpy.data.objects[obj_name]
    if added:
        return bpy.data.objects[added[0]]
    raise RuntimeError("追加失败：%s 自 %s" % (obj_name, blend_path))


def clear_fx(prefix="FX_"):
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


def toonify_object(obj):
    for slot in obj.material_slots:
        if slot.material:
            L.toonify(slot.material)


def main():
    os.makedirs(SHOT, exist_ok=True)
    taxi_path = os.path.join(ROOT, "out", "taxi.blend")
    sport_path = os.path.join(ROOT, "out", "sportscar.blend")
    if not os.path.isfile(taxi_path) or not os.path.isfile(sport_path):
        raise SystemExit("缺 out/taxi.blend 或 out/sportscar.blend，先跑两个 build 脚本")

    bpy.ops.wm.open_mainfile(filepath=taxi_path)
    taxi = bpy.data.objects.get("GEO-TaxiSpider")
    if taxi is None:
        raise SystemExit("taxi.blend 里没有 GEO-TaxiSpider")

    sport = append_object(sport_path, "GEO-SportSpider")
    sport.location = Vector(SPORT_OFFSET)
    print("[duo] appended %s @ %s" % (sport.name, tuple(sport.location)))

    # QC 地面放大一点盖住两辆车
    ground = bpy.data.objects.get("QC_Ground")
    if ground is not None:
        ground.scale = (2.2, 1.4, 1.0)
        ground.location = (-3.0, 0.0, 0.0)

    clear_fx()
    toonify_object(taxi)
    toonify_object(sport)
    L.make_outline(taxi, thickness=0.014)
    # 跑车描边：复制后需要跟着偏移
    ol = L.make_outline(sport, thickness=0.012)
    if ol is not None:
        ol.name = "FX_Outline_Sport"
        ol.location = Vector(SPORT_OFFSET)

    L.setup_world_and_ground()
    L.setup_render()
    L.setup_compositor()

    cam = bpy.data.objects.get("Cam")
    if cam is None:
        cd = bpy.data.cameras.new("Cam")
        cam = bpy.data.objects.new("Cam", cd)
        bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.data.type = "PERSP"
    cam.data.lens = 35.0

    # 场景中心落在两车之间 (−3.25, 0, 0.8)
    mid = (-3.25, 0.0, 0.85)

    L.aim(cam, (2.5, -12.5, 3.4), mid, roll=math.radians(-1.5))
    L.render(os.path.join(SHOT, "duo-hero.png"), 1600, 900)

    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 16.0
    L.aim(cam, (-3.25, -16.0, 0.85), mid)
    L.render(os.path.join(SHOT, "duo-side.png"), 1800, 720)
    cam.data.type = "PERSP"

    L.aim(cam, (-10.5, -11.0, 3.2), mid, roll=math.radians(2.0))
    L.render(os.path.join(SHOT, "duo-rear34.png"), 1440, 810)

    cam.data.lens = 45.0
    L.aim(cam, (-3.25, 0.0, 16.0), mid)
    L.render(os.path.join(SHOT, "duo-overhead.png"), 1400, 900)

    cam.data.lens = 35.0
    L.aim(cam, (2.5, -12.5, 3.4), mid, roll=math.radians(-1.5))
    duo_path = os.path.join(ROOT, "out", "duo.blend")
    bpy.ops.wm.save_as_mainfile(filepath=duo_path)
    print("[duo] saved %s" % duo_path)


if __name__ == "__main__":
    main()
