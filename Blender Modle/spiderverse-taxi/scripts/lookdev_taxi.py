# -*- coding: utf-8 -*-
"""蜘蛛侠纵横宇宙风 · 渲染层（只改外观，不动网格）

四个手段，全部可在 EEVEE 里落地：
  ① 分层平涂     Principled → Shader to RGB → RGBtoBW → 三段 CONSTANT ColorRamp → 乘回基础色
  ② 反壳描边     复制网格 + Solidify(flip normals) + 背剔黑面 ⇒ 只留轮廓一圈
  ③ 半调网点     屏幕坐标 × 网屏贴图，乘在最终色上（印刷感）
  ④ 红青分离     compositor Lens Distortion 的 Dispersion（5.2 走 compositing_node_group）

用法：
  blender -b out/taxi.blend --python scripts/lookdev_taxi.py
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHOT_DIR = os.path.join(ROOT, "renders")
OUTLINE_THICK = 0.014


# ---------------------------------------------------------------- 半调网屏贴图

def halftone_image(size=128, cell=16, cover=0.32):
    """无缝网点：棋盘偏移的二重方阵（周期 = cell），白底黑点，REPEAT 平铺。"""
    img = bpy.data.images.get("TEX_Halftone")
    if img:
        return img
    img = bpy.data.images.new("TEX_Halftone", width=size, height=size, alpha=False)
    px = [1.0] * (size * size * 4)
    r = cell * cover

    def near(x, y, ox, oy):
        dx = (x - ox + cell * 0.5) % cell - cell * 0.5
        dy = (y - oy + cell * 0.5) % cell - cell * 0.5
        return math.hypot(dx, dy)

    for y in range(size):
        for x in range(size):
            d = min(near(x, y, 0.0, 0.0),
                    near(x, y, cell * 0.5, cell * 0.5))
            v = 0.0 if d < r else 1.0
            i = (y * size + x) * 4
            px[i] = px[i + 1] = px[i + 2] = v
            px[i + 3] = 1.0
    img.pixels = px
    img.pack()
    return img


def halftone_screen_nodes(nt, x=-1000, y=-500, scale=46.0, strength=0.22):
    """屏幕空间网点：Window 坐标 → 缩放 → 网屏图 → 与颜色相乘。"""
    tc = nt.nodes.new("ShaderNodeTexCoord")
    tc.location = (x - 300, y)
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.location = (x - 150, y)
    mp.inputs["Scale"].default_value = (scale, scale, 1.0)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.location = (x, y)
    tex.image = halftone_image()
    tex.interpolation = "Closest"
    tex.extension = "REPEAT"
    nt.links.new(tc.outputs["Window"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
    return tex, strength


def toonify(mat):
    """把一个材质改成"分层平涂 + 网点"的发光材质，灰度台阶由灯光决定。"""
    if not mat or not mat.use_nodes:
        return
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    tex = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None)
    if bsdf is None or out is None:
        return

    base = None
    if tex is not None:
        base = tex.outputs["Color"]
    else:
        base = None

    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.location = (bsdf.location.x + 260, bsdf.location.y)
    nt.links.new(bsdf.outputs["BSDF"], s2rgb.inputs["Shader"])

    bw = nt.nodes.new("ShaderNodeRGBToBW")
    bw.location = (s2rgb.location.x + 180, s2rgb.location.y)
    nt.links.new(s2rgb.outputs["Color"], bw.inputs["Color"])

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (bw.location.x + 180, s2rgb.location.y)
    cr = ramp.color_ramp
    cr.interpolation = "CONSTANT"
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.42, 0.42, 0.42, 1.0)
    cr.elements[1].position = 0.42
    cr.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    e = cr.elements.new(0.80)
    e.color = (1.30, 1.30, 1.35, 1.0)
    nt.links.new(bw.outputs["Val"], ramp.inputs["Fac"])

    # 台阶 × 基础色
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mix.location = (ramp.location.x + 200, s2rgb.location.y)
    if base is not None:
        nt.links.new(base, mix.inputs["A"])
    else:
        mix.inputs["A"].default_value = bsdf.inputs["Base Color"].default_value
    nt.links.new(ramp.outputs["Color"], mix.inputs["B"])

    # 网点
    htex, hstrength = halftone_screen_nodes(nt, x=-800, y=-620)
    mix2 = nt.nodes.new("ShaderNodeMix")
    mix2.data_type = "RGBA"
    mix2.blend_type = "MULTIPLY"
    mix2.inputs["Factor"].default_value = hstrength
    mix2.location = (mix.location.x + 200, s2rgb.location.y)
    nt.links.new(mix.outputs["Result"], mix2.inputs["A"])
    nt.links.new(htex.outputs["Color"], mix2.inputs["B"])

    emis = nt.nodes.new("ShaderNodeEmission")
    emis.location = (mix2.location.x + 200, s2rgb.location.y)
    emis.inputs["Strength"].default_value = 1.0
    nt.links.new(mix2.outputs["Result"], emis.inputs["Color"])
    nt.links.new(emis.outputs["Emission"], out.inputs["Surface"])

    bsdf.inputs["Roughness"].default_value = min(
        bsdf.inputs["Roughness"].default_value, 0.45)
    bsdf.inputs["Specular IOR Level"].default_value = 0.25


def make_outline(obj, thickness=OUTLINE_THICK):
    dup = obj.copy()
    dup.data = obj.data.copy()
    dup.name = "FX_Outline"
    bpy.context.scene.collection.objects.link(dup)
    dup.parent = None
    mat = bpy.data.materials.new("M_FX_Outline")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in [n for n in nt.nodes if n.type != "OUTPUT_MATERIAL"]:
        nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    emis = nt.nodes.new("ShaderNodeEmission")
    emis.inputs["Color"].default_value = (0.02, 0.015, 0.02, 1.0)
    emis.inputs["Strength"].default_value = 1.0
    nt.links.new(emis.outputs["Emission"], out.inputs["Surface"])
    mat.use_backface_culling = True
    try:
        mat.use_backface_culling_shadow = True
    except AttributeError:
        pass

    dup.data.materials.clear()
    dup.data.materials.append(mat)
    for p in dup.data.polygons:
        p.material_index = 0

    m = dup.modifiers.new("hull", "SOLIDIFY")
    m.thickness = thickness
    m.offset = 1.0
    m.use_flip_normals = True
    m.use_rim = False
    try:
        dup.visible_shadow = False
    except AttributeError:
        pass
    return dup


# ---------------------------------------------------------------- 场景

def setup_world_and_ground():
    sc = bpy.context.scene
    world = sc.world or bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in [n for n in nt.nodes if n.type not in ("OUTPUT_WORLD",)]:
        nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_WORLD")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "EASE"
    cr.elements[0].position = 0.05
    cr.elements[0].color = (0.30, 0.06, 0.36, 1.0)   # 地平线：品红
    cr.elements[1].position = 0.62
    cr.elements[1].color = (0.05, 0.30, 0.42, 1.0)   # 天顶：青
    mid = cr.elements.new(0.30)
    mid.color = (0.55, 0.16, 0.30, 1.0)
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 0.9
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    ground = bpy.data.objects.get("QC_Ground")
    if ground is None:
        me = bpy.data.meshes.new("FX_Ground")
        bmg = bmesh.new()
        bmesh.ops.create_grid(bmg, x_segments=1, y_segments=1, size=30.0)
        bmg.to_mesh(me)
        bmg.free()
        ground = bpy.data.objects.new("FX_Ground", me)
        sc.collection.objects.link(ground)
    gm = bpy.data.materials.new("M_FX_Ground")
    gm.use_nodes = True
    gnt = gm.node_tree
    gb = next(n for n in gnt.nodes if n.type == "BSDF_PRINCIPLED")
    gb.inputs["Base Color"].default_value = (0.10, 0.05, 0.14, 1.0)
    gb.inputs["Roughness"].default_value = 1.0
    ground.data.materials.clear()
    ground.data.materials.append(gm)

    # 主光：硬阴影 + 一点边缘光
    for name, kind, energy, rot, loc in [
        ("Key", "SUN", 5.0, (math.radians(56), 0.0, math.radians(38)), None),
        ("Rim", "SUN", 3.0, (math.radians(70), 0.0, math.radians(-135)), None),
    ]:
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
        ld = bpy.data.lights.new(name, kind)
        ld.energy = energy
        ld.angle = math.radians(1.5)
        ld.color = (1.0, 0.85, 0.72) if name == "Key" else (0.55, 0.75, 1.0)
        o = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(o)
        o.rotation_euler = rot


def setup_render():
    sc = bpy.context.scene
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            sc.render.engine = engine
            break
        except TypeError:
            continue
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.render.film_transparent = False
    ee = getattr(sc, "eevee", None)
    if ee is not None and hasattr(ee, "taa_render_samples"):
        ee.taa_render_samples = 64


def setup_compositor():
    """红青分离 + 轻微暗角。5.2 的合成器挂在 scene.compositing_node_group 上。"""
    try:
        sc = bpy.context.scene
        ng = bpy.data.node_groups.new("Comp_SPD", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        rl = ng.nodes.new("CompositorNodeRLayers")
        lens = ng.nodes.new("CompositorNodeLensdist")
        lens.inputs["Distortion"].default_value = 0.0
        lens.inputs["Dispersion"].default_value = 0.022
        glare = ng.nodes.new("CompositorNodeGlare")
        glare.inputs["Threshold"].default_value = 1.0
        out = ng.nodes.new("NodeGroupOutput")
        ng.links.new(rl.outputs["Image"], lens.inputs["Image"])
        ng.links.new(lens.outputs["Image"], glare.inputs["Image"])
        ng.links.new(glare.outputs["Image"], out.inputs[0])
        sc.compositing_node_group = ng
        print("[look] compositor: dispersion=0.018 + glare")
        return True
    except Exception as exc:                      # noqa: BLE001
        print("[look] WARN: 合成器不可用（%s），跳过红青分离" % exc)
        return False


def aim(cam, loc, target, roll=0.0):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    q = d.to_track_quat("-Z", "Y")
    e = q.to_euler()
    e.rotate_axis("Z", roll)
    cam.rotation_euler = e


def render(path, w, h):
    sc = bpy.context.scene
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[look] render -> %s (%dx%d)" % (path, w, h))


def main():
    os.makedirs(SHOT_DIR, exist_ok=True)
    obj = bpy.data.objects.get("GEO-TaxiSpider")
    if obj is None:
        print("!! 找不到 GEO-TaxiSpider")
        return

    for slot in obj.material_slots:
        toonify(slot.material)

    # 旧的描边对象先清掉（可重跑）
    old = bpy.data.objects.get("FX_Outline")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    make_outline(obj)

    setup_world_and_ground()
    setup_render()
    setup_compositor()

    cam = bpy.data.objects.get("Cam")
    if cam is None:
        cd = bpy.data.cameras.new("Cam")
        cam = bpy.data.objects.new("Cam", cd)
        bpy.context.scene.collection.objects.link(cam)
        bpy.context.scene.camera = cam
    cam.data.lens = 38.0
    bpy.context.scene.camera = cam

    aim(cam, (4.4, -7.6, 1.28), (0.1, 0.0, 1.02), roll=math.radians(-2.5))
    render(os.path.join(SHOT_DIR, "look-hero.png"), 1600, 900)

    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 6.4
    aim(cam, (0.0, -10.0, 0.9), (0.0, 0.0, 0.9))
    render(os.path.join(SHOT_DIR, "look-side.png"), 1280, 720)
    cam.data.type = "PERSP"

    aim(cam, (-5.0, -6.4, 2.2), (0.0, 0.0, 0.95), roll=math.radians(2.0))
    render(os.path.join(SHOT_DIR, "look-rear34.png"), 1280, 720)

    # 局部：棋盘带 + 侧窗（L2 级证据）
    cam.data.lens = 85.0
    aim(cam, (1.9, -3.1, 1.15), (0.6, -0.9, 0.78))
    render(os.path.join(SHOT_DIR, "look-detail-checker.png"), 900, 900)

    # 存档回到英雄机位（另存，保持 out/taxi.blend 是干净构建件）
    cam.data.lens = 38.0
    aim(cam, (4.4, -7.6, 1.28), (0.1, 0.0, 1.02), roll=math.radians(-2.5))
    bpy.context.scene.render.resolution_x = 1600
    bpy.context.scene.render.resolution_y = 900
    look_path = os.path.join(ROOT, "out", "taxi_look.blend")
    bpy.ops.wm.save_as_mainfile(filepath=look_path)
    print("[look] saved %s" % look_path)


if __name__ == "__main__":
    main()
