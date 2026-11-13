# -*- coding: utf-8 -*-
"""风格化 lookdev：把物理渲染的出租车推成《蜘蛛侠：纵横宇宙》的漫画质感。

三层（都可单独关掉）：
  1. **几何描边**：复制网格 → Solidify(外扩 14mm, 法线翻转) + 背面剔除的黑材质
     = inverted hull，出图就是一圈墨线。导出前隐藏/删除，不进交付件。
  2. **构图**：中灰背景 + 硬阴影主光 + 冷色补光（参考图就是这种影棚 + 硬投影）。
  3. **后期**：Lensdist 色散（边缘红青分离）+ Fog Glow 微泛光 + Curves 提对比/饱和。

用法：
  blender -b --factory-startup --python scripts/lookdev.py
产物：renders/look-*.png + out/taxi_look.blend
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLEND = os.path.join(ROOT, "out", "taxi.blend")
SHOTS = os.path.join(ROOT, "renders")
OBJ_NAME = "GEO-TaxiAcross"


def make_black_mat():
    m = bpy.data.materials.get("M_FX_Outline")
    if m:
        return m
    m = bpy.data.materials.new("M_FX_Outline")
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.012, 0.010, 0.014, 1.0)
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Emission Color"].default_value = (0.012, 0.010, 0.014, 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.35
    m.use_backface_culling = True
    m.diffuse_color = (0.012, 0.010, 0.014, 1.0)
    return m


def build_outline(src, thickness_mm=14.0):
    """inverted hull：外扩一层、法线翻转、只渲背面的黑壳。"""
    old = bpy.data.objects.get("FX_Outline")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    dup = src.copy()
    dup.data = src.data.copy()
    dup.name = "FX_Outline"
    dup.data.name = "FX_OutlineMesh"
    bpy.context.scene.collection.objects.link(dup)
    dup.data.materials.clear()
    dup.data.materials.append(make_black_mat())
    for p in dup.data.polygons:
        p.material_index = 0
    col = bpy.data.collections.get("COL_FX_Outline")
    if col is None:
        col = bpy.data.collections.new("COL_FX_Outline")
        bpy.context.scene.collection.children.link(col)
    for c in list(dup.users_collection):
        c.objects.unlink(dup)
    col.objects.link(dup)

    mod = dup.modifiers.new("hull", "SOLIDIFY")
    mod.thickness = thickness_mm * 0.001
    mod.offset = 1.0
    mod.use_rim = False
    mod.use_flip_normals = True
    bpy.ops.object.select_all(action="DESELECT")
    dup.select_set(True)
    bpy.context.view_layer.objects.active = dup
    bpy.ops.object.modifier_apply(modifier=mod.name)

    # 不要 recalc_face_normals、也不要手动 flip：Solidify(use_flip_normals=True) 已经把
    # 外扩壳的法线翻到朝内，配合材质背面剔除 ⇒ 只留下"轮廓外那一圈"墨线。
    # （实测：再 recalc 或再 flip 一次，黑壳就会盖住整车 → 全黑）
    dup.data.update()
    dup.data.update()
    print("[look] outline ok: %d faces, %.0f mm" % (len(dup.data.polygons), thickness_mm))
    return dup


def setup_freestyle(sc, thickness=2.0):
    """漫画墨线：用 Freestyle（EEVEE 也支持）出轮廓/边界/折痕线。

    为什么不用 inverted hull：实测 EEVEE Next 下外扩黑壳配合背面剔除没有按预期剔除，
    整车被黑壳盖住（全黑两次）。Freestyle 是后处理线，语义明确、还能带内部折边（门缝/格栅）。
    """
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"
    sc.render.line_thickness = thickness
    vl = bpy.context.view_layer
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    fs.mode = "EDITOR"
    fs.crease_angle = math.radians(152.0)
    if not fs.linesets:
        fs.linesets.new("InkLines")
    ls = fs.linesets[0]
    ls.name = "InkLines"
    ls.select_silhouette = True
    ls.select_border = True
    ls.select_crease = True
    ls.select_contour = True
    ls.select_external_contour = True
    ls.select_edge_mark = False
    ls.select_material_boundary = True
    style = ls.linestyle
    if style is None:
        style = bpy.data.linestyles.new("InkStyle")
        ls.linestyle = style
    style.color = (0.015, 0.012, 0.020)
    style.thickness = thickness
    style.alpha = 1.0
    print("[look] freestyle on: thickness=%.1f crease=%.0fdeg"
          % (thickness, math.degrees(fs.crease_angle)))


def setup_stage():
    sc = bpy.context.scene
    # 背景：中灰影棚（参考图就是这种底）
    world = bpy.data.worlds.get("W") or bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["From Min"].default_value = -1.0
    mr.inputs["From Max"].default_value = 1.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.40
    ramp.color_ramp.elements[0].color = (0.030, 0.030, 0.036, 1.0)
    ramp.color_ramp.elements[1].position = 0.70
    ramp.color_ramp.elements[1].color = (0.70, 0.72, 0.78, 1.0)
    nt.links.new(coord.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.55

    # 主光：硬（小角度）+ 高能量；补光冷色
    sun = bpy.data.objects.get("Sun")
    if sun:
        sun.data.energy = 5.5
        sun.data.angle = math.radians(1.2)
        sun.rotation_euler = (math.radians(42), 0.0, math.radians(28))
        sun.data.color = (1.0, 0.96, 0.90)
    fill = bpy.data.objects.get("Fill")
    if fill:
        fill.data.energy = 420.0
        fill.data.color = (0.72, 0.82, 1.0)
    rim = bpy.data.objects.get("Rim")
    if rim:
        rim.data.energy = 900.0
        rim.data.color = (1.0, 0.88, 0.72)

    # 地面：更暗的摄影棚地台
    g = bpy.data.objects.get("QC_Ground")
    if g:
        gm = g.data.materials[0] if g.data.materials else None
        if gm and gm.use_nodes:
            gb = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
            gb.inputs["Base Color"].default_value = (0.11, 0.112, 0.125, 1.0)
            gb.inputs["Roughness"].default_value = 0.75
    return sc


def setup_compositor(sc, dispersion=0.035, glow=0.22, contrast=1.10):
    ng = bpy.data.node_groups.get("CompTaxi")
    if ng is None:
        ng = bpy.data.node_groups.new("CompTaxi", "CompositorNodeTree")
    sc.compositing_node_group = ng
    ng.nodes.clear()
    ng.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")

    rl = ng.nodes.new("CompositorNodeRLayers")
    rl.location = (-600, 0)
    ld = ng.nodes.new("CompositorNodeLensdist")
    ld.location = (-380, 0)
    ld.inputs["Distortion"].default_value = 0.0
    ld.inputs["Dispersion"].default_value = dispersion
    ld.inputs["Fit"].default_value = True
    gl = ng.nodes.new("CompositorNodeGlare")
    gl.location = (-180, 0)
    try:
        gl.inputs["Type"].default_value = "Fog Glow"
        gl.inputs["Quality"].default_value = "High"
        gl.inputs["Threshold"].default_value = 1.1
        gl.inputs["Size"].default_value = 7.0
        gl.inputs["Strength"].default_value = glow
    except Exception as exc:                     # noqa: BLE001
        print("[look] WARN glare params: %s" % exc)
    cv = ng.nodes.new("CompositorNodeCurveRGB")
    cv.location = (20, 0)
    # 提对比：把 C 曲线两端压/提
    try:
        c = cv.mapping.curves[3]
        c.points[0].location = (0.02, 0.0)
        c.points[1].location = (0.98, 1.0)
        mid = c.points.new(0.5, 0.5 + (0.5 - 0.5))
        cv.mapping.update()
    except Exception as exc:                     # noqa: BLE001
        print("[look] WARN curves: %s" % exc)
    out = ng.nodes.new("NodeGroupOutput")
    out.location = (260, 0)
    ng.links.new(rl.outputs["Image"], ld.inputs["Image"])
    ng.links.new(ld.outputs["Image"], gl.inputs["Image"])
    ng.links.new(gl.outputs["Image"], cv.inputs["Image"])
    ng.links.new(cv.outputs["Image"], out.inputs["Image"])
    sc.render.use_compositing = True
    print("[look] compositor: dispersion=%.3f glow=%.2f" % (dispersion, glow))


def aim(cam, loc, target):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def render(sc, path, w, h, samples=64):
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    ee = getattr(sc, "eevee", None)
    if ee is not None and hasattr(ee, "taa_render_samples"):
        ee.taa_render_samples = samples
    try:
        sc.render.use_persistent_data = True
    except Exception:                            # noqa: BLE001
        pass
    bpy.ops.render.render(write_still=True)
    print("[look] render -> %s" % path)


def main():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    disp = 0.035
    if "--no-fx" in argv:
        disp = 0.0

    bpy.ops.wm.open_mainfile(filepath=BLEND)
    sc = bpy.context.scene
    cam = bpy.data.objects.get("Cam")
    src = bpy.data.objects[OBJ_NAME]

    setup_stage()
    if disp > 0.0:
        setup_freestyle(sc, thickness=3.0)
        setup_compositor(sc, dispersion=disp)
    else:
        setup_compositor(sc, dispersion=0.0, glow=0.0)

    ee = getattr(sc, "eevee", None)
    if ee is not None:
        for attr, val in (("use_raytracing", True), ("use_shadows", True),
                          ("use_gtao", True), ("taa_render_samples", 64)):
            if hasattr(ee, attr):
                try:
                    setattr(ee, attr, val)
                except Exception:                # noqa: BLE001
                    pass

    shots = [
        ("look-hero", (5.6, -9.8, 3.3), (0.0, 0.0, 1.05), 1600, 900, 64),
        ("look-side", (0.0, 11.0, 1.15), (0.0, 0.0, 1.15), 1600, 760, 64),
        ("look-rear34", (-5.6, -7.6, 3.0), (0.0, 0.0, 1.0), 1500, 840, 64),
        ("look-front34", (8.6, -5.6, 2.7), (0.0, 0.0, 1.0), 1500, 840, 64),
        ("look-top", (0.4, -1.2, 11.0), (0.0, 0.0, 0.6), 1200, 1000, 48),
    ]
    if "--cmp-only" in argv:
        shots = []
    for name, loc, tgt, w, h, sp in shots:
        aim(cam, loc, tgt)
        render(sc, os.path.join(SHOTS, name + ".png"), w, h, sp)

    # ---- 与参考图**同机位同裁切**的正交对比帧（供 visualreport 算 IoU）
    # 参考侧视：1672x941，车长 1630 px ⇒ 视野宽 1672/0.313462 = 5334 mm
    # 对比帧必须**隐藏地面 + 透明底**：否则地面/阴影会进掩膜，IoU 直接失真
    if "--no-cmp" not in argv:
        ground = bpy.data.objects.get("QC_Ground")
        if ground:
            ground.hide_render = True
        sc.render.film_transparent = True
        try:
            sc.render.image_settings.color_mode = "RGBA"
        except Exception:                        # noqa: BLE001
            pass
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 5.334
        # 参考侧视是**车头朝左**的左视图 ⇒ 必须从 +Y 侧拍（+X 才会落在画面左侧）。
        # 从 −Y 侧拍会得到镜像图，掩膜 IoU 会被冤枉到 0.79（实测）。
        aim(cam, (0.0, 12.0, 1.089), (0.0, 0.0, 1.089))
        render(sc, os.path.join(SHOTS, "cmp-side.png"), 1672, 941, 32)
        cam.data.ortho_scale = 3.372
        aim(cam, (12.0, 0.0, 0.854), (0.0, 0.0, 0.854))
        render(sc, os.path.join(SHOTS, "cmp-front.png"), 1672, 941, 32)
        cam.data.type = "PERSP"
        cam.data.lens = 65.0
        sc.render.film_transparent = False
        if ground:
            ground.hide_render = False

    # 细节特写（看墨线/镀铬/棋盘格）
    cam.data.type = "PERSP"
    cam.data.lens = 85.0
    for name, loc, tgt in (
            ("detail-wheel", (2.6, -3.0, 0.9), (1.34, -0.62, 0.42)),
            ("detail-nose", (3.6, -2.4, 1.35), (2.3, -0.2, 0.80)),
            ("detail-checker", (1.0, -3.4, 1.15), (0.2, -0.9, 1.10))):
        aim(cam, loc, tgt)
        render(sc, os.path.join(SHOTS, name + ".png"), 1200, 800, 48)
    cam.data.lens = 65.0

    aim(cam, (5.0, -8.6, 3.1), (0.0, 0.0, 1.05))
    sc.render.resolution_x = 1600
    sc.render.resolution_y = 900
    out = os.path.join(ROOT, "out", "taxi_look.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out)
    print("[look] saved %s" % out)


if __name__ == "__main__":
    main()
