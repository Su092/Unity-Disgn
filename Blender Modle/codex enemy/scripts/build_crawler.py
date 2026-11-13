import bpy
import bmesh
import math
import os
from mathutils import Vector


ROOT = r"E:\Unity Development\Blender Modle\codex enemy"
BLEND_PATH = os.path.join(ROOT, "codex_crawler.blend")
RENDER_DIR = os.path.join(ROOT, "renders")
EXPORT_DIR = os.path.join(ROOT, "export")


def log(*args):
    print("[crawler]", *args)


def srgb_channel(value):
    value = value / 255.0
    if value <= 0.04045:
        return value / 12.92
    return ((value + 0.055) / 1.055) ** 2.4


def rgba(hex_value, alpha=1.0):
    value = hex_value.lstrip("#")
    return (
        srgb_channel(int(value[0:2], 16)),
        srgb_channel(int(value[2:4], 16)),
        srgb_channel(int(value[4:6], 16)),
        alpha,
    )


def make_material(name, color, roughness=0.55, metallic=0.0, emission=None,
                  emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = rgba(color)
    nodes = mat.node_tree.nodes
    shader = nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = rgba(color)
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    if emission is not None:
        emission_input = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
        if emission_input is not None:
            emission_input.default_value = rgba(emission)
        strength_input = shader.inputs.get("Emission Strength")
        if strength_input is not None:
            strength_input.default_value = emission_strength
    return mat


def create_collection(name):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def add_bevel(obj, width, segments=1, angle=math.radians(35.0)):
    if width <= 0.0:
        return
    modifier = obj.modifiers.new("Edge bevel", "BEVEL")
    modifier.width = width
    modifier.segments = segments
    modifier.limit_method = "ANGLE"
    modifier.angle_limit = angle
    if hasattr(modifier, "use_clamp_overlap"):
        modifier.use_clamp_overlap = True
    if hasattr(modifier, "harden_normals"):
        modifier.harden_normals = False


def create_mesh_object(name, verts, faces, material, collection, bevel=0.0):
    mesh = bpy.data.meshes.new("MESH-" + name.replace("GEO-", ""))
    mesh.from_pydata(verts, [], faces)
    mesh.validate(verbose=False)
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    mesh.materials.append(material)

    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    for polygon in mesh.polygons:
        polygon.use_smooth = False

    add_bevel(obj, bevel)
    return obj


def loft_y(name, sections, ring_function, material, collection, bevel=0.0):
    rings = []
    for section in sections:
        ring = ring_function(
            section["halfw"],
            section["zb"],
            section["zt"],
        )
        rings.append([(x, section["y"], z) for x, z in ring])

    count = len(rings[0])
    verts = [vertex for ring in rings for vertex in ring]
    faces = []

    for section_index in range(len(rings) - 1):
        a_offset = section_index * count
        b_offset = (section_index + 1) * count
        for index in range(count):
            next_index = (index + 1) % count
            a = a_offset + index
            b = a_offset + next_index
            c = b_offset + next_index
            d = b_offset + index
            if (section_index + index) % 2 == 0:
                faces.append((a, b, c))
                faces.append((a, c, d))
            else:
                faces.append((a, b, d))
                faces.append((b, c, d))

    faces.append(tuple(reversed(range(count))))
    last_offset = (len(rings) - 1) * count
    faces.append(tuple(last_offset + index for index in range(count)))
    return create_mesh_object(name, verts, faces, material, collection, bevel)


def shell_ring(halfw, zb, zt):
    height = zt - zb
    return [
        (-0.82 * halfw, zb),
        (-1.00 * halfw, zb + 0.20 * height),
        (-1.00 * halfw, zb + 0.50 * height),
        (-0.85 * halfw, zb + 0.80 * height),
        (-0.50 * halfw, zb + 0.96 * height),
        (0.00, zt),
        (0.50 * halfw, zb + 0.96 * height),
        (0.85 * halfw, zb + 0.80 * height),
        (1.00 * halfw, zb + 0.50 * height),
        (1.00 * halfw, zb + 0.20 * height),
        (0.82 * halfw, zb),
    ]


def body_ring(halfw, zb, zt):
    height = zt - zb
    return [
        (-0.82 * halfw, zb),
        (-0.52 * halfw, zb - 0.07 * height),
        (0.00, zb - 0.10 * height),
        (0.52 * halfw, zb - 0.07 * height),
        (0.82 * halfw, zb),
        (0.98 * halfw, zb + 0.22 * height),
        (1.00 * halfw, zb + 0.55 * height),
        (0.84 * halfw, zb + 0.88 * height),
        (0.36 * halfw, zt),
        (0.00, zt + 0.015 * height),
        (-0.36 * halfw, zt),
        (-0.84 * halfw, zb + 0.88 * height),
        (-1.00 * halfw, zb + 0.55 * height),
        (-0.98 * halfw, zb + 0.22 * height),
    ]


def head_ring(halfw, zb, zt):
    height = zt - zb
    return [
        (-0.68 * halfw, zb),
        (-0.98 * halfw, zb + 0.20 * height),
        (-1.00 * halfw, zb + 0.60 * height),
        (-0.80 * halfw, zb + 0.86 * height),
        (-0.34 * halfw, zt),
        (0.34 * halfw, zt),
        (0.80 * halfw, zb + 0.86 * height),
        (1.00 * halfw, zb + 0.60 * height),
        (0.98 * halfw, zb + 0.20 * height),
        (0.68 * halfw, zb),
    ]


def armor_ring(halfw, zb, zt):
    height = zt - zb
    return [
        (-0.70 * halfw, zb),
        (-1.00 * halfw, zb + 0.16 * height),
        (-0.98 * halfw, zb + 0.62 * height),
        (-0.70 * halfw, zb + 0.92 * height),
        (0.00, zt),
        (0.70 * halfw, zb + 0.92 * height),
        (0.98 * halfw, zb + 0.62 * height),
        (1.00 * halfw, zb + 0.16 * height),
    ]


def add_box(name, center, size, material, collection, bevel=0.0):
    cx, cy, cz = center
    sx, sy, sz = size
    x0, x1 = cx - sx * 0.5, cx + sx * 0.5
    y0, y1 = cy - sy * 0.5, cy + sy * 0.5
    z0, z1 = cz - sz * 0.5, cz + sz * 0.5
    verts = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7),
        (0, 1, 5, 4), (1, 2, 6, 5),
        (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    return create_mesh_object(name, verts, faces, material, collection, bevel)


def oriented_prism(name, p1, p2, width1, depth1, width2, depth2,
                   material, collection, bevel=0.0):
    p1 = Vector(p1)
    p2 = Vector(p2)
    direction = (p2 - p1).normalized()
    x_axis = Vector((1.0, 0.0, 0.0))
    if abs(direction.dot(x_axis)) > 0.95:
        x_axis = Vector((0.0, 1.0, 0.0))
    x_axis = (x_axis - direction * direction.dot(x_axis)).normalized()
    y_axis = direction.cross(x_axis).normalized()

    profile = [
        (-0.38, -0.50),
        (-0.50, -0.28),
        (-0.50, 0.28),
        (-0.38, 0.50),
        (0.38, 0.50),
        (0.50, 0.28),
        (0.50, -0.28),
        (0.38, -0.50),
    ]
    count = len(profile)
    verts = []
    for point, half_width, half_depth in (
        (p1, width1 * 0.5, depth1 * 0.5),
        (p2, width2 * 0.5, depth2 * 0.5),
    ):
        for u, v in profile:
            verts.append(tuple(point + x_axis * (u * half_width * 2.0)
                               + y_axis * (v * half_depth * 2.0)))

    faces = []
    for index in range(count):
        next_index = (index + 1) % count
        faces.append((index, next_index, count + next_index))
        faces.append((index, count + next_index, count + index))
    faces.append(tuple(reversed(range(count))))
    faces.append(tuple(count + index for index in range(count)))
    return create_mesh_object(name, verts, faces, material, collection, bevel)


def plate_box(name, center, u_axis, v_axis, length, width, thickness,
              outward_hint, material, collection, bevel=0.0):
    center = Vector(center)
    u_axis = Vector(u_axis).normalized()
    v_axis = Vector(v_axis).normalized()
    normal = u_axis.cross(v_axis).normalized()
    if normal.dot(Vector(outward_hint)) < 0.0:
        normal.negate()

    verts = []
    for u_sign, v_sign, n_sign in (
        (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
        (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
    ):
        point = (
            center
            + u_axis * (u_sign * length * 0.5)
            + v_axis * (v_sign * width * 0.5)
            + normal * (n_sign * thickness * 0.5)
        )
        verts.append(tuple(point))
    faces = [
        (0, 3, 2, 1), (4, 5, 6, 7),
        (0, 1, 5, 4), (1, 2, 6, 5),
        (2, 3, 7, 6), (3, 0, 4, 7),
    ]
    return create_mesh_object(name, verts, faces, material, collection, bevel)


def interpolate_half_width(sections, y):
    if y <= sections[0]["y"]:
        return sections[0]["halfw"]
    if y >= sections[-1]["y"]:
        return sections[-1]["halfw"]
    for first, second in zip(sections, sections[1:]):
        if first["y"] <= y <= second["y"]:
            t = (y - first["y"]) / (second["y"] - first["y"])
            return first["halfw"] * (1.0 - t) + second["halfw"] * t
    return sections[-1]["halfw"]


def interpolate_section(sections, y):
    if y <= sections[0]["y"]:
        return sections[0]
    if y >= sections[-1]["y"]:
        return sections[-1]
    for first, second in zip(sections, sections[1:]):
        if first["y"] <= y <= second["y"]:
            t = (y - first["y"]) / (second["y"] - first["y"])
            return {
                "y": y,
                "halfw": first["halfw"] * (1.0 - t) + second["halfw"] * t,
                "zb": first["zb"] * (1.0 - t) + second["zb"] * t,
                "zt": first["zt"] * (1.0 - t) + second["zt"] * t,
            }
    return sections[-1]


def body_surface_x(sections, y, z):
    section = interpolate_section(sections, y)
    ring = body_ring(section["halfw"], section["zb"], section["zt"])
    right_side = ring[4:10]
    for first, second in zip(right_side, right_side[1:]):
        z0, z1 = first[1], second[1]
        if min(z0, z1) - 1e-6 <= z <= max(z0, z1) + 1e-6:
            if abs(z1 - z0) < 1e-8:
                t = 0.5
            else:
                t = (z - z0) / (z1 - z0)
            return first[0] * (1.0 - t) + second[0] * t
    return 0.66 * section["halfw"]


def side_stripe(name, points_yz, half_band, side, sections, material,
                collection):
    centers = [Vector((y, z)) for y, z in points_yz]
    edge_points = []
    for index, point in enumerate(centers):
        if index == 0:
            tangent = centers[1] - centers[0]
        elif index == len(centers) - 1:
            tangent = centers[-1] - centers[-2]
        else:
            tangent = centers[index + 1] - centers[index - 1]
        tangent.normalize()
        normal = Vector((-tangent.y, tangent.x))
        if normal.dot(Vector((0.0, 1.0))) < 0.0:
            normal.negate()
        edge_points.append((point - normal * half_band, point + normal * half_band))

    verts = []
    for index, (y, z) in enumerate(points_yz):
        lower, upper = edge_points[index]
        outer_x = side * (body_surface_x(sections, y, z) + 0.009)
        inner_x = side * (body_surface_x(sections, y, z) - 0.010)
        verts.extend([
            (outer_x, lower.x, lower.y),
            (outer_x, upper.x, upper.y),
            (inner_x, lower.x, lower.y),
            (inner_x, upper.x, upper.y),
        ])

    faces = []
    for index in range(len(points_yz) - 1):
        a = index * 4
        b = (index + 1) * 4
        faces.extend([
            (a, a + 1, b + 1), (a, b + 1, b),
            (a + 2, b + 2, b + 3), (a + 2, b + 3, a + 3),
            (a, b, b + 2), (a, b + 2, a + 2),
            (a + 1, a + 3, b + 3), (a + 1, b + 3, b + 1),
        ])
    last = (len(points_yz) - 1) * 4
    faces.extend([
        (0, 2, 3), (0, 3, 1),
        (last, last + 1, last + 3), (last, last + 3, last + 2),
    ])
    return create_mesh_object(name, verts, faces, material, collection, 0.006)


def apply_modifiers(obj):
    if not obj.modifiers:
        return
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = obj.evaluated_get(depsgraph)
    new_mesh = bpy.data.meshes.new_from_object(
        evaluated,
        preserve_all_data_layers=True,
        depsgraph=depsgraph,
    )
    old_mesh = obj.data
    obj.modifiers.clear()
    obj.data = new_mesh
    new_mesh.name = old_mesh.name
    bpy.data.meshes.remove(old_mesh)
    for polygon in obj.data.polygons:
        polygon.use_smooth = False


def clean_mesh(obj):
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-8, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    for polygon in mesh.polygons:
        polygon.use_smooth = False


def build_crawler(materials, collection):
    shell_sections = [
        {"y": -1.42, "halfw": 0.76, "zb": 1.00, "zt": 1.38},
        {"y": -1.17, "halfw": 0.96, "zb": 0.94, "zt": 1.68},
        {"y": -0.64, "halfw": 1.04, "zb": 0.88, "zt": 1.88},
        {"y": -0.02, "halfw": 1.03, "zb": 0.90, "zt": 1.93},
        {"y": 0.48, "halfw": 0.98, "zb": 0.98, "zt": 1.84},
        {"y": 0.82, "halfw": 0.82, "zb": 1.08, "zt": 1.59},
        {"y": 1.03, "halfw": 0.65, "zb": 1.16, "zt": 1.39},
    ]
    body_sections = [
        {"y": -1.36, "halfw": 0.78, "zb": 0.72, "zt": 1.10},
        {"y": -1.05, "halfw": 0.88, "zb": 0.58, "zt": 1.20},
        {"y": -0.48, "halfw": 0.91, "zb": 0.53, "zt": 1.24},
        {"y": 0.10, "halfw": 0.90, "zb": 0.54, "zt": 1.24},
        {"y": 0.58, "halfw": 0.84, "zb": 0.58, "zt": 1.18},
        {"y": 0.88, "halfw": 0.70, "zb": 0.66, "zt": 1.10},
    ]
    head_sections = [
        {"y": 0.50, "halfw": 0.58, "zb": 0.62, "zt": 1.17},
        {"y": 0.88, "halfw": 0.70, "zb": 0.52, "zt": 1.31},
        {"y": 1.30, "halfw": 0.72, "zb": 0.48, "zt": 1.30},
        {"y": 1.58, "halfw": 0.67, "zb": 0.52, "zt": 1.19},
        {"y": 1.66, "halfw": 0.59, "zb": 0.57, "zt": 1.09},
    ]
    brow_sections = [
        {"y": 1.03, "halfw": 0.62, "zb": 1.12, "zt": 1.31},
        {"y": 1.47, "halfw": 0.71, "zb": 1.01, "zt": 1.23},
        {"y": 1.74, "halfw": 0.64, "zb": 0.93, "zt": 1.10},
        {"y": 1.82, "halfw": 0.55, "zb": 0.91, "zt": 1.04},
    ]
    jaw_sections = [
        {"y": 1.05, "halfw": 0.53, "zb": 0.58, "zt": 0.78},
        {"y": 1.47, "halfw": 0.60, "zb": 0.43, "zt": 0.73},
        {"y": 1.76, "halfw": 0.55, "zb": 0.43, "zt": 0.68},
        {"y": 1.82, "halfw": 0.47, "zb": 0.49, "zt": 0.64},
    ]

    loft_y("GEO-Carapace", shell_sections, shell_ring,
           materials["shell"], collection, bevel=0.014)
    loft_y("GEO-Underbody", body_sections, body_ring,
           materials["navy"], collection, bevel=0.014)
    loft_y("GEO-HeadCore", head_sections, head_ring,
           materials["head"], collection, bevel=0.012)
    loft_y("GEO-Brow", brow_sections, armor_ring,
           materials["grey"], collection, bevel=0.012)
    loft_y("GEO-Jaw", jaw_sections, armor_ring,
           materials["dark_grey"], collection, bevel=0.010)

    # Wide amber visor recessed under the brow.
    visor_columns = [-0.58, -0.29, 0.0, 0.29, 0.58]
    visor_top = [0.915, 0.930, 0.925, 0.930, 0.915]
    visor_bottom = [0.785, 0.770, 0.760, 0.770, 0.785]
    front_y = 1.735
    back_y = 1.675
    front_top = [(x, front_y, z) for x, z in zip(visor_columns, visor_top)]
    front_bottom = [(x, front_y, z) for x, z in zip(visor_columns, visor_bottom)]
    back_top = [(x, back_y, z) for x, z in zip(visor_columns, visor_top)]
    back_bottom = [(x, back_y, z) for x, z in zip(visor_columns, visor_bottom)]
    front_loop = front_top + list(reversed(front_bottom))
    back_loop = back_top + list(reversed(back_bottom))
    verts = front_loop + back_loop
    loop_size = len(front_loop)
    faces = []
    for index in range(loop_size):
        next_index = (index + 1) % loop_size
        faces.append((index, next_index, loop_size + next_index,
                      loop_size + index))
    faces.append(tuple(reversed(range(loop_size))))
    faces.append(tuple(loop_size + index for index in range(loop_size)))
    create_mesh_object("GEO-Visor", verts, faces, materials["visor"],
                       collection, bevel=0.005)

    # Zig-zag amber side marking, mirrored to both flanks.
    stripe_points = [
        (-1.25, 0.855),
        (-0.90, 0.860),
        (-0.62, 0.810),
        (-0.30, 0.740),
        (0.05, 0.695),
        (0.40, 0.670),
        (0.72, 0.660),
    ]
    side_stripe("GEO-Stripe-R", stripe_points, 0.064, 1, body_sections,
                materials["orange"], collection)
    side_stripe("GEO-Stripe-L", stripe_points, 0.064, -1, body_sections,
                materials["orange"], collection)

    # Twin cyan vents on each upper flank.
    for side in (-1, 1):
        side_name = "R" if side > 0 else "L"
        for index, (x, y, z) in enumerate((
            (0.703, 0.25, 1.797),
            (0.848, 0.21, 1.732),
        )):
            plate_box(
                f"GEO-Vent-{side_name}-{index + 1}",
                (side * x, y, z),
                (0.0, 1.0, 0.0),
                (0.90, 0.0, -0.435),
                0.52,
                0.082,
                0.014,
                (side, 0.0, 1.0),
                materials["cyan"],
                collection,
                bevel=0.005,
            )

    leg_specs = [
        ("Front-R", 1, 0.62, 0.10),
        ("Front-L", -1, 0.62, 0.10),
        ("Rear-R", 1, -0.72, -0.10),
        ("Rear-L", -1, -0.72, -0.10),
    ]
    for label, side, hip_y, fore_aft in leg_specs:
        hip = (side * 0.79, hip_y, 0.99)
        knee = (side * 1.20, hip_y + fore_aft, 0.59)
        ankle = (side * 1.29, hip_y + fore_aft * 1.30, 0.21)
        foot_y = hip_y + fore_aft * 1.35
        oriented_prism(
            f"GEO-Leg-{label}-Upper", hip, knee,
            0.39, 0.46, 0.32, 0.38,
            materials["grey"], collection, bevel=0.010,
        )
        oriented_prism(
            f"GEO-Leg-{label}-Lower", knee, ankle,
            0.31, 0.36, 0.26, 0.30,
            materials["navy"], collection, bevel=0.009,
        )
        lower_start = Vector(knee)
        lower_end = Vector(ankle)
        band_start = lower_start.lerp(lower_end, 0.20)
        band_end = lower_start.lerp(lower_end, 0.40)
        oriented_prism(
            f"GEO-Leg-{label}-Band", band_start, band_end,
            0.335, 0.385, 0.315, 0.365,
            materials["orange"], collection, bevel=0.006,
        )
        add_box(
            f"GEO-Leg-{label}-Foot",
            (side * 1.31, foot_y, 0.11),
            (0.48, 0.61, 0.22),
            materials["navy"], collection, bevel=0.028,
        )

    # Small rear cap keeps the underside silhouette closed and mechanical.
    add_box("GEO-Rear-Bumper", (0.0, -1.40, 0.88),
            (1.22, 0.16, 0.36), materials["dark_grey"], collection, 0.018)


def setup_scene():
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    scene.render.resolution_x = 1254
    scene.render.resolution_y = 1254
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except TypeError:
            scene.render.engine = "CYCLES"
            scene.cycles.samples = 64
            scene.cycles.use_denoising = True

    if hasattr(scene, "eevee"):
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = 64
        if hasattr(scene.eevee, "use_raytracing"):
            scene.eevee.use_raytracing = True

    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0


def setup_environment(materials):
    scene = bpy.context.scene
    env = create_collection("COL_Environment")

    world = bpy.data.worlds.new("WORLD-Crawler-Studio")
    world.use_nodes = True
    scene.world = world
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = rgba("#666666")
    background.inputs["Strength"].default_value = 1.0

    add_box("ENV-Ground", (0.0, 0.0, -0.03),
            (120.0, 120.0, 0.05), materials["ground"], env, 0.0)

    def add_area(name, location, energy, size, color):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = rgba(color)[:3]
        obj = bpy.data.objects.new(name, data)
        env.objects.link(obj)
        obj.location = location
        direction = Vector((0.0, 0.0, 0.9)) - Vector(location)
        obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        return obj

    add_area("LIGHT-Key", (-3.8, 4.2, 7.2), 360.0, 6.0, "#FFF9F4")
    add_area("LIGHT-Fill", (5.0, -2.0, 3.6), 100.0, 5.0, "#F7F9FF")
    add_area("LIGHT-Rim", (-2.4, -5.2, 5.0), 200.0, 4.0, "#FFE9D6")

    sun_data = bpy.data.lights.new("LIGHT-Sun", "SUN")
    sun_data.energy = 1.8
    sun_data.angle = math.radians(12.0)
    sun_data.color = (1.0, 0.98, 0.95)
    sun = bpy.data.objects.new("LIGHT-Sun", sun_data)
    env.objects.link(sun)
    sun.rotation_euler = (
        Vector((0.0, 0.0, 0.9)) - Vector((-4.0, 4.0, 9.0))
    ).to_track_quat("-Z", "Y").to_euler()

    visor_glow = bpy.data.lights.new("LIGHT-VisorGlow", "POINT")
    visor_glow.energy = 24.0
    visor_glow.color = rgba("#FF8A00")[:3]
    visor_glow.shadow_soft_size = 0.18
    glow_obj = bpy.data.objects.new("LIGHT-VisorGlow", visor_glow)
    env.objects.link(glow_obj)
    glow_obj.location = (0.0, 2.05, 0.86)

    camera_data = bpy.data.cameras.new("CAM-Hero")
    camera_data.lens = 100.0
    camera_data.sensor_width = 36.0
    camera = bpy.data.objects.new("CAM-Hero", camera_data)
    env.objects.link(camera)
    camera.location = (5.9, 7.6, 3.55)
    target = Vector((0.0, 0.05, 0.90))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera


def apply_all_and_report(collection):
    objects = [obj for obj in collection.objects if obj.type == "MESH"]
    for obj in objects:
        apply_modifiers(obj)
        clean_mesh(obj)

    mins = Vector((1e9, 1e9, 1e9))
    maxs = Vector((-1e9, -1e9, -1e9))
    total_vertices = 0
    total_faces = 0
    for obj in objects:
        matrix = obj.matrix_world
        points = [matrix @ vertex.co for vertex in obj.data.vertices]
        for point in points:
            mins.x = min(mins.x, point.x)
            mins.y = min(mins.y, point.y)
            mins.z = min(mins.z, point.z)
            maxs.x = max(maxs.x, point.x)
            maxs.y = max(maxs.y, point.y)
            maxs.z = max(maxs.z, point.z)
        total_vertices += len(obj.data.vertices)
        total_faces += len(obj.data.polygons)
        log(obj.name, "verts", len(obj.data.vertices),
            "faces", len(obj.data.polygons))
    log("bbox_m", tuple(round(value, 4) for value in (maxs - mins)))
    log("bbox_min", tuple(round(value, 4) for value in mins))
    log("bbox_max", tuple(round(value, 4) for value in maxs))
    log("totals", total_vertices, total_faces, len(objects))
    return objects, mins, maxs


def export_asset(objects):
    os.makedirs(EXPORT_DIR, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]

    fbx_path = os.path.join(EXPORT_DIR, "codex_crawler.fbx")
    glb_path = os.path.join(EXPORT_DIR, "codex_crawler.glb")

    bpy.ops.export_scene.fbx(
        filepath=fbx_path,
        use_selection=True,
        object_types={"MESH"},
        apply_scale_options="FBX_SCALE_ALL",
        axis_forward="-Z",
        axis_up="Y",
        add_leaf_bones=False,
        bake_anim=False,
    )
    log("exported", fbx_path)

    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
    )
    log("exported", glb_path)

    bpy.ops.object.select_all(action="DESELECT")


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(RENDER_DIR, exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)
    setup_scene()

    collection = create_collection("COL_Crawler")
    materials = {
        "shell": make_material("MAT-Armor-Red", "#C93B1C", roughness=0.62),
        "navy": make_material("MAT-Armor-Navy", "#2F3036", roughness=0.52),
        "head": make_material("MAT-Head-Core", "#33363F", roughness=0.44),
        "grey": make_material("MAT-Head-Armor", "#4A4F59", roughness=0.40),
        "dark_grey": make_material("MAT-Jaw-Dark", "#2F323A", roughness=0.46),
        "orange": make_material("MAT-Stripe-Amber", "#E58E18", roughness=0.42),
        "cyan": make_material("MAT-Vent-Cyan", "#5EC4FC", roughness=0.32,
                              emission="#5EC4FC", emission_strength=0.20),
        "visor": make_material("MAT-Visor-Amber", "#FFB000", roughness=0.24,
                               emission="#FFB000", emission_strength=1.3),
        "ground": make_material("MAT-Studio-Floor", "#707070", roughness=0.78,
                                emission="#707070", emission_strength=0.25),
    }

    build_crawler(materials, collection)
    objects, _mins, _maxs = apply_all_and_report(collection)
    setup_environment(materials)

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    log("saved", BLEND_PATH)

    export_asset(objects)

    # Primary hero render.
    bpy.context.scene.render.filepath = os.path.join(RENDER_DIR, "codex_crawler_hero.png")
    bpy.ops.render.render(write_still=True)
    log("rendered", bpy.context.scene.render.filepath)

    # Secondary rear three-quarter check.
    camera = bpy.data.objects["CAM-Hero"]
    camera.location = (-5.8, -7.1, 3.45)
    target = Vector((0.0, 0.02, 0.88))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.render.filepath = os.path.join(RENDER_DIR, "codex_crawler_rear.png")
    bpy.ops.render.render(write_still=True)
    log("rendered", bpy.context.scene.render.filepath)

    # Restore the hero camera in the saved file.
    camera.location = (5.9, 7.6, 3.55)
    target = Vector((0.0, 0.05, 0.90))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    log("done")


if __name__ == "__main__":
    main()
