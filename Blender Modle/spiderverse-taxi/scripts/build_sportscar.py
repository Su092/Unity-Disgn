# -*- coding: utf-8 -*-
"""蜘蛛侠纵横宇宙风 · 红色复古跑车 · 参数化建模（headless 安全）

规格见 ../sportscar-spec.md。复用 build_taxi 的网格原语 / UV / 烘焙，
材质与装配独立。交付对象 GEO-SportSpider（1 对象 / 5 壳）。

用法：
  blender -b --factory-startup --python scripts/build_sportscar.py
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

# 同目录导入出租车脚本里的原语（box / cylinder / UV / bake …）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_taxi as T  # noqa: E402

MM = T.MM
ASSET_STEM = "Modle_Vehicle_SpiderSport"
TEX_NAME = ASSET_STEM + "_basecolor.jpg"

SPEC = {
    "length": 4200.0,
    "width": 1780.0,
    "height": 1215.0,
    "body_half": 860.0,
    "sill_z": 170.0,
    "wheel_x": 1250.0,
    "wheel_y": 740.0,
    "tire_r": 350.0,
    "tire_w": 220.0,
    "hub_r": 205.0,
    "hub_w": 232.0,
    "arch_r": 450.0,
    "arch_y_in": 610.0,
    "bumper_tip": 2100.0,
}

# 材质
PAINT, GLASS, CHROME, TIRE, RIM, LEATHER, TRIM = (
    "M_Sport_Paint", "M_Sport_Glass", "M_Sport_Chrome", "M_Sport_Tire",
    "M_Sport_Rim", "M_Sport_Leather", "M_Sport_Trim",
)
MAT_NAMES = [PAINT, GLASS, CHROME, TIRE, RIM, LEATHER, TRIM]
MI = {n: i for i, n in enumerate(MAT_NAMES)}

MAT_LOOK = {
    PAINT:   ((0.780, 0.050, 0.050, 1.0), 0.38, 0.05),
    GLASS:   ((0.080, 0.100, 0.140, 1.0), 0.12, 0.10),
    CHROME:  ((0.820, 0.840, 0.860, 1.0), 0.18, 0.95),
    TIRE:    ((0.030, 0.030, 0.035, 1.0), 0.90, 0.00),
    RIM:     ((0.720, 0.730, 0.750, 1.0), 0.28, 0.85),
    LEATHER: ((0.200, 0.105, 0.080, 1.0), 0.62, 0.00),
    TRIM:    ((0.040, 0.040, 0.045, 1.0), 0.55, 0.15),
}

WHEEL_Z = SPEC["tire_r"]          # 轮心高度 = 胎半径（落地 z=0）

# 断面绕 X 放样：翼子板峰压在轮心上方，甲板在轮上不开槽。
# 约束：zt(wheel_x) > WHEEL_Z + arch_r = 350 + 440 = 790（否则轮拱切穿上表面）
BODY_SECTIONS = [
    (-2050.0, 0.86, 620.0),   # 尾端
    (-1900.0, 0.94, 700.0),
    (-1650.0, 0.99, 795.0),   # 后翼子板肩
    (-1250.0, 1.00, 830.0),   # 后翼子板峰
    (-900.0, 0.99, 785.0),
    (-350.0, 0.98, 762.0),    # 座舱后段
    (300.0, 0.98, 758.0),     # 风挡下沿 / 前围
    (900.0, 0.99, 795.0),     # 前翼子板肩
    (1250.0, 1.00, 830.0),    # 前翼子板峰
    (1650.0, 0.97, 772.0),
    (1900.0, 0.92, 676.0),
    (2050.0, 0.86, 600.0),    # 鼻端
]


# ---------------------------------------------------------------- 材质 / 槽

def build_materials():
    for name in list(bpy.data.materials.keys()):
        if name.startswith("M_Sport_"):
            bpy.data.materials.remove(bpy.data.materials[name])
    for name in MAT_NAMES:
        col, rough, metal = MAT_LOOK[name]
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = col
        bsdf.inputs["Roughness"].default_value = rough
        bsdf.inputs["Metallic"].default_value = metal
        m.diffuse_color = col
    return [bpy.data.materials[n] for n in MAT_NAMES]


def normalize_slots(obj):
    me = obj.data
    n_before = len(me.materials)
    per_face = []
    for p in me.polygons:
        mat = me.materials[p.material_index] if p.material_index < len(me.materials) else None
        per_face.append(mat)
    used = []
    for mat in per_face:
        if mat is not None and mat not in used:
            used.append(mat)
    order = [bpy.data.materials[n] for n in MAT_NAMES if bpy.data.materials.get(n) in used]
    order += [m for m in used if m not in order]
    me.materials.clear()
    for m in order:
        me.materials.append(m)
    index = {m: i for i, m in enumerate(order)}
    fallback = index.get(bpy.data.materials[PAINT], 0)
    for p, mat in zip(me.polygons, per_face):
        p.material_index = index.get(mat, fallback)
    print("[sport] material slots: %d -> %d (%s)"
          % (n_before, len(me.materials), ", ".join(m.name for m in me.materials)))


# ---------------------------------------------------------------- 造型

def build_body(mats):
    secs = [{"x": x, "w": SPEC["body_half"] * s, "zt": zt} for (x, s, zt) in BODY_SECTIONS]

    def profile(sec):
        w, zt = sec["w"], sec["zt"]
        return [
            (-0.88 * w, SPEC["sill_z"]),
            (-1.00 * w, 290.0),
            (-1.00 * w, zt - 90.0),
            (-0.93 * w, zt),
            (0.93 * w, zt),
            (1.00 * w, zt - 90.0),
            (1.00 * w, 290.0),
            (0.88 * w, SPEC["sill_z"]),
        ]

    # loft 需要 MI；临时挂到 T.MI 不行——自己写一版用本地 MI
    bm = bmesh.new()
    rings = []
    for sec in secs:
        pts = profile(sec)
        rings.append([bm.verts.new((sec["x"] * MM, y * MM, z * MM)) for (y, z) in pts])
    n = len(rings[0])
    face_mats = []
    for si in range(len(rings) - 1):
        a, b = rings[si], rings[si + 1]
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
            face_mats.append(MI[PAINT])
    bm.faces.new(list(reversed(rings[0])))
    face_mats.append(MI[PAINT])
    bm.faces.new(rings[-1])
    face_mats.append(MI[PAINT])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    body = T.new_object("GEO-SportBody", bm, mats, face_mats)
    T.bevelize(body, 18.0, 2)
    return body


def build_wheel(name, cx, cy):
    tire = T.cylinder(name + "_Tire", "Y", (cx, WHEEL_Z), SPEC["tire_r"],
                      cy - SPEC["tire_w"] * 0.5, cy + SPEC["tire_w"] * 0.5, 32, TIRE)
    T.bevelize(tire, 45.0, 3)

    # 只做朝外一侧（轮井内侧间隙纪律，见 taxi report §5 #6）
    sg = 1.0 if cy > 0.0 else -1.0

    # 深色轮盘：给辐条做背景，侧视才有"亮辐条 + 暗间隙"的对比
    plate = T.cylinder(name + "_Plate", "Y", (cx, WHEEL_Z), 196.0,
                       cy + sg * 112.0, cy + sg * 124.0, 32, TRIM)
    T.bool_op(tire, plate, "UNION")

    # 五辐：从轮心 55 伸到 200，明显凸出轮盘 10 mm
    bm2 = bmesh.new()
    for k in range(5):
        th = 2.0 * math.pi * k / 5.0 + math.pi * 0.5
        ca, sa = math.cos(th), math.sin(th)
        pts = []
        for (r, s) in ((55.0, -22.0), (200.0, -26.0), (200.0, 26.0), (55.0, 22.0)):
            pts.append((cx + r * ca - s * sa, WHEEL_Z + r * sa + s * ca))
        T.bm_add_prism(bm2, pts, cy + sg * 104.0, cy + sg * 134.0)
    bmesh.ops.recalc_face_normals(bm2, faces=bm2.faces)
    spokes = T.new_object(name + "_Spokes", bm2, [bpy.data.materials[CHROME]],
                          [0] * len(bm2.faces))
    T.bool_op(tire, spokes, "UNION")

    # 轮圈外唇 + 中心盖
    lip = T.ring(name + "_Lip", "Y", (cx, WHEEL_Z), 182.0, 200.0,
                 cy + sg * 120.0, cy + sg * 130.0, 32, CHROME)
    T.bevelize(lip, 4.0, 2)
    T.bool_op(tire, lip, "UNION")

    cap = T.cylinder(name + "_Cap", "Y", (cx, WHEEL_Z), 62.0,
                     cy + sg * 118.0, cy + sg * 138.0, 20, CHROME)
    T.bevelize(cap, 6.0, 2)
    T.bool_op(tire, cap, "UNION")
    tire.name = name
    return tire


def build_details():
    """所有零件必须与车身（或先并入的同类件）有 ≥15 mm 真体积交叠。

    体块按参考图重做（`refs/_crop-side.png`）：
      · 甲板压低到 758~815，翼子板峰压在轮心上方 → 轮拱（顶 z=790）不再切穿上表面
      · 座舱是**真开口**：DIFFERENCE 挖一个 z 520→1000 的盲腔，不破底面
      · 风挡只占车身中段（x −55→340），顶 z=1215；后面两个头枕鼓包 + 一条低篷包
    座舱件都在甲板之上，靠"先挖腔、再各自压进腔底/甲板 ≥15 mm"保证连通。
    """
    parts = []

    def add(part, bev=0.0):
        if bev > 0.0:
            T.bevelize(part, bev, 2)
        parts.append(part)
        return part

    tip = SPEC["bumper_tip"]

    # ① 前后保险杠（y 到 ±890 = 量测宽度基准）
    for sx in (1.0, -1.0):
        add(T.box("GEO-SBump", 1980.0 * sx, tip * sx, -890, 890, 235, 325, CHROME), 10.0)

    # ② 圆大灯 ×2 + 灯芯
    for sy in (1.0, -1.0):
        add(T.cylinder("GEO-SLight", "X", (560.0 * sy, 480.0), 78.0,
                       1980.0, 2055.0, 24, CHROME), 8.0)
        add(T.cylinder("GEO-SLens", "X", (560.0 * sy, 480.0), 58.0,
                       2050.0, 2064.0, 20, GLASS), 2.0)

    # ③ 前格栅环 + 横条 + 车牌（环外沿 180 < 鼻端半宽 740）
    add(T.ring("GEO-SGrille", "X", (0.0, 400.0), 140.0, 180.0,
               2040.0, 2078.0, 28, CHROME), 3.0)
    for z in (350.0, 400.0, 450.0):
        add(T.box("GEO-SGrilleBar", 2048, 2068, -128, 128, z, z + 11.0, TRIM), 1.5)
    add(T.box("GEO-SPlate", 2045, 2065, -180, 180, 265, 345, TRIM), 2.0)

    # ④ 尾灯 + 鸭尾
    for sy in (1.0, -1.0):
        add(T.box("GEO-STail", -2058, -2010, 430 * sy, 540 * sy, 470, 555, CHROME), 6.0)
    add(T.box("GEO-SDucktail", -2040, -1880, -720, 720, 650, 730, PAINT), 8.0)

    # ⑤ 引擎盖进气口 + 中线凸条（甲板 758~782，凸 18~30 mm）
    add(T.box("GEO-SScoop", 700, 1100, -110, 110, 730, 800, TRIM), 6.0)


    # ⑥ 侧出排气管：z 340 处车身最宽 ±860，管心 845 + r45 → 外沿 890，露出 30 mm
    #    中段避开前后轮拱切削区（前拱 810→1690 / 后拱 −1690→−810）
    for sy in (1.0, -1.0):
        add(T.cylinder("GEO-SExMid", "X", (845.0 * sy, 340.0), 45.0,
                       -780.0, 780.0, 20, CHROME), 4.0)
        add(T.cylinder("GEO-SExRear", "X", (845.0 * sy, 340.0), 45.0,
                       -2040.0, -1700.0, 20, CHROME), 4.0)

    # ⑦ 门把手（该断面半宽 0.98×860=843，把手内沿 820 咬进 23 mm）
    for sy in (1.0, -1.0):
        add(T.box("GEO-SHandle", 120, 200, 820 * sy, 858 * sy, 620, 678, CHROME), 2.0)

    # ⑧ 后视镜：杆压进甲板 28 mm，头外沿 ≤872
    for sy in (1.0, -1.0):
        add(T.box("GEO-SMirStalk", 180, 250, 650 * sy, 790 * sy, 730, 800, TRIM))
        add(T.box("GEO-SMirHead", 160, 260, 780 * sy, 872 * sy, 790, 858, CHROME), 6.0)

    # ⑨ 风挡框：底梁压甲板；A 柱是后倾整片（梯形棱柱），顶梁压在柱顶
    add(T.box("GEO-SWindBase", 240, 340, -500, 500, 735, 805, TRIM), 4.0)
    add(T.box("GEO-SWindTop", -60, 40, -490, 490, 1185, 1215, TRIM), 4.0)
    for sy in (1.0, -1.0):
        bmp = bmesh.new()
        T.bm_add_prism(bmp, [(345.0, 760.0), (295.0, 760.0),
                             (-25.0, 1200.0), (25.0, 1200.0)],
                       455.0 * sy, 505.0 * sy)
        bmesh.ops.recalc_face_normals(bmp, faces=bmp.faces)
        add(T.new_object("GEO-SWindPillar", bmp, [bpy.data.materials[TRIM]],
                         [0] * len(bmp.faces)))

    # ⑩ 风挡玻璃：上/下各嵌进梁内 10 mm，左右钻进 A 柱 15 mm（不共面）
    bm = bmesh.new()
    corners = [
        (330.0, -470.0, 795.0),
        (330.0, 470.0, 795.0),
        (-20.0, 455.0, 1192.0),
        (-20.0, -455.0, 1192.0),
    ]
    nrm = Vector((0.85, 0.0, 0.52)).normalized()
    a = [bm.verts.new(Vector((c[0] * MM, c[1] * MM, c[2] * MM)) - nrm * 0.020)
         for c in corners]
    b = [bm.verts.new(Vector((c[0] * MM, c[1] * MM, c[2] * MM)) + nrm * 0.020)
         for c in corners]
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(a)))
    bm.faces.new(b)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    add(T.new_object("GEO-SWindGlass", bm, [bpy.data.materials[GLASS]],
                     [0] * len(bm.faces)))

    # ⑪ 低篷包（折叠状态，只在座舱后方抬起 70 mm）
    add(T.box("GEO-STonneau", -1010, -730, -480, 480, 735, 845, PAINT), 22.0)

    return parts


def build_interior():
    """座舱内件：必须在挖完舱口之后 UNION。

    腔底 z=520、腔口 y ±430、x −700→200。
    垫底压进腔底 15 mm，靠背压进坐垫，头枕压进靠背 —— 一路串成一体。
    """
    parts = []

    def add(part, bev=0.0):
        if bev > 0.0:
            T.bevelize(part, bev, 2)
        parts.append(part)
        return part

    for sy in (1.0, -1.0):
        add(T.box("GEO-SSeatCush", -680, -340, 60 * sy, 360 * sy, 505, 610, LEATHER), 10.0)
        add(T.box("GEO-SSeatBack", -690, -575, 75 * sy, 345 * sy, 590, 900, LEATHER), 10.0)
        add(T.box("GEO-SHeadrest", -690, -565, 90 * sy, 330 * sy, 880, 1010, LEATHER), 16.0)
    return parts


def cut_cockpit(body):
    """敞篷开口：盲腔（底 520 / 甲板 758~762），不破底面 → 仍水密。

    x 只到 +200、后沿 −700：前面给风挡底梁留 40 mm，后面离后轮拱 110 mm。
    """
    cut = T.box("GEO-SCockpit", -700, 200, -430, 430, 520, 1000, TRIM)
    T.bool_op(body, cut, "DIFFERENCE")
    print("[sport] cockpit pocket cut")


def build_sportscar():
    mats = build_materials()
    body = build_body(mats)
    parts = build_details()

    for p in parts:
        n0 = len(body.data.polygons)
        T.bool_op(body, p, "UNION")
        n1 = len(body.data.polygons)
        if n1 < n0 * 0.5:
            raise RuntimeError("UNION(%s) 疑似丢失主体：%d -> %d 面" % (p.name, n0, n1))
    print("[sport] union done: %d verts / %d faces"
          % (len(body.data.vertices), len(body.data.polygons)))
    sc = T.shells_count(body)
    print("[sport] shells after union: %d" % sc)
    assert sc == 1, "UNION 后车身不是单一壳（%d）" % sc

    # 敞篷开口（盲腔，不破底面）——必须在座椅之前，否则座椅被实心车身吞掉
    cut_cockpit(body)
    assert T.shells_count(body) == 1, "舱口切削后断壳"

    for p in build_interior():
        T.bool_op(body, p, "UNION")
    sc = T.shells_count(body)
    print("[sport] shells after interior: %d" % sc)
    assert sc == 1, "座舱内件并合后断壳（%d）" % sc

    # 轮拱切削
    for sx in (1.0, -1.0):
        for sy in (1.0, -1.0):
            cut = T.cylinder("GEO-SArch", "Y", (SPEC["wheel_x"] * sx, WHEEL_Z),
                             SPEC["arch_r"], SPEC["arch_y_in"] * sy, 940.0 * sy, 28, TRIM)
            T.bool_op(body, cut, "DIFFERENCE")

    wheels = []
    for sx in (1.0, -1.0):
        for sy in (1.0, -1.0):
            wheels.append(build_wheel(
                "GEO-SWheel%s%s" % ("F" if sx > 0 else "R", "L" if sy > 0 else "R"),
                SPEC["wheel_x"] * sx, SPEC["wheel_y"] * sy))

    normalize_slots(body)
    bpy.ops.object.select_all(action="DESELECT")
    for w in wheels:
        w.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.name = "GEO-SportSpider"
    normalize_slots(body)

    for p in body.data.polygons:
        p.use_smooth = False
    body.location = (0.0, 0.0, 0.0)
    body.rotation_euler = (0.0, 0.0, 0.0)
    body.scale = (1.0, 1.0, 1.0)
    return body


# ---------------------------------------------------------------- 主流程

def setup_scene():
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            sc.render.engine = engine
            print("[sport] engine:", engine)
            break
        except TypeError:
            continue
    # 简单灯 + 相机 + 地面（QC 用，不进 FBX）
    key = bpy.data.lights.new("Key", "AREA")
    key.energy = 600.0
    key.size = 4.0
    ko = bpy.data.objects.new("Key", key)
    sc.collection.objects.link(ko)
    ko.location = (3.0, -4.0, 5.0)

    fill = bpy.data.lights.new("Fill", "AREA")
    fill.energy = 200.0
    fill.size = 3.0
    fo = bpy.data.objects.new("Fill", fill)
    sc.collection.objects.link(fo)
    fo.location = (-3.0, -2.0, 3.0)

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 55.0
    cam = bpy.data.objects.new("Cam", cam_data)
    sc.collection.objects.link(cam)
    sc.camera = cam

    ground = bpy.data.meshes.new("QC_Ground")
    bmg = bmesh.new()
    bmesh.ops.create_grid(bmg, x_segments=1, y_segments=1, size=12.0)
    bmg.to_mesh(ground)
    bmg.free()
    g = bpy.data.objects.new("QC_Ground", ground)
    sc.collection.objects.link(g)
    gm = bpy.data.materials.new("M_QC_Ground")
    gm.use_nodes = True
    gb = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    gb.inputs["Base Color"].default_value = (0.16, 0.16, 0.18, 1.0)
    ground.materials.append(gm)
    return cam


def aim(cam, loc, target):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def render_to(path, w, h, samples=32):
    sc = bpy.context.scene
    try:
        sc.eevee.taa_render_samples = samples
    except Exception:
        pass
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("[sport] render -> %s (%dx%d)" % (path, w, h))


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_dir = os.path.join(root, "out")
    shot_dir = os.path.join(root, "renders")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(shot_dir, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    cam = setup_scene()
    obj = build_sportscar()
    audit = T.unwrap_uv(obj, pad=0.003)

    tex_path = os.path.join(out_dir, TEX_NAME)
    img = T.bake_basecolor(obj, tex_path, 1024)
    if img is None:
        img = T.grain_image(512)
        img.filepath_raw = tex_path
        img.file_format = "JPEG"
        img.save()
        print("[sport] fallback texture -> %s" % tex_path)
    T.wire_texture(obj, img, tex_path)

    print("[sport] verts=%d faces=%d shells=%d tris=%d"
          % (len(obj.data.vertices), len(obj.data.polygons), T.shells_count(obj),
             sum(len(p.vertices) - 2 for p in obj.data.polygons)))
    print("[sport] uv audit: %s" % audit)

    aim(cam, (3.2, -5.8, 1.6), (0.0, 0.0, 0.55))
    render_to(os.path.join(shot_dir, "sport-hero.png"), 1280, 720)
    aim(cam, (0.0, -7.0, 0.6), (0.0, 0.0, 0.55))
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 5.0
    render_to(os.path.join(shot_dir, "sport-side.png"), 1280, 720)
    cam.data.type = "PERSP"
    aim(cam, (-3.6, -5.0, 1.5), (0.0, 0.0, 0.55))
    render_to(os.path.join(shot_dir, "sport-rear.png"), 960, 540)

    aim(cam, (3.2, -5.8, 1.6), (0.0, 0.0, 0.55))
    blend_path = os.path.join(out_dir, "sportscar.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print("[sport] saved %s" % blend_path)


if __name__ == "__main__":
    main()
