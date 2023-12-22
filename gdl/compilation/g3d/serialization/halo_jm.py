# EXPERIMENTAL!!! borrowing halo ce animation
# format if the reclaimer module is available
from math import cos, sin, pi
from . import constants as c, vector_util
from ....rendering.assets.scene_objects.util import gdl_euler_to_quaternion

halo_anim = halo_model = None
if c.JMS_SUPPORT:
    from reclaimer.model import jms as halo_model
    from reclaimer.animation import jma as halo_anim


# NOTE: Converting from gauntlet coordinate system to halo coordinates
#       requires rotating axis and negating the y axis like so
# TODO: Try swapping x and y axis to go with rotations
def g3d_pos_to_halo_pos(x, y, z): return z, -x, y
def halo_pos_to_g3d_pos(x, y, z): return -y, z, x

# converting uvw is easy. just invert the v coordinate
def g3d_uvw_to_halo_uvw(u, v, w=0.0): return u, 1.0-v, w
halo_uvw_to_g3d_uvw = g3d_uvw_to_halo_uvw


def g3d_euler_to_jma_quaternion(h, p, r):
    return gdl_euler_to_quaternion(-r, -p, -h)
    #'''
    h_quat = gdl_euler_to_quaternion( 0, h, 0)
    p_quat = gdl_euler_to_quaternion( 0, 0, p)
    r_quat = gdl_euler_to_quaternion(-r, 0, 0)
    quats = (
        h_quat, p_quat, r_quat,
        #h_quat, p_quat, r_quat,#?
        #h_quat, r_quat, p_quat,#
        #p_quat, h_quat, r_quat,#
        #p_quat, r_quat, h_quat,#
        #r_quat, h_quat, p_quat,#
        #r_quat, p_quat, h_quat,#
        )
    return vector_util.multiply_quaternions(
        vector_util.multiply_quaternions(quats[0], quats[1]), quats[2]
        #quats[2], vector_util.multiply_quaternions(quats[1], quats[0])
        )


# NOTE: backslash isn't a reserved character in JMS materials, but
#       we're using it in the escape so we need to escape it as well.
JMS_MATERIAL_ESCAPE_CHAR = "\\"
JMS_MATERIAL_SPECIAL_CHARS = JMS_MATERIAL_ESCAPE_CHAR + "!@#$%^&*-."
_JMS_CHAR_CONVERT_MAP = {
    c: f"%s%02x" % (JMS_MATERIAL_ESCAPE_CHAR, i)
    for i, c in enumerate(JMS_MATERIAL_SPECIAL_CHARS)
    }


def g3d_texname_to_jms_material(texname):
    # NOTE: In JMS materials the following characters are reserved
    #       to apply special properties to the shader:  !@#$%^&*-.
    #       We'll get around this by escaping them when exporting
    #       to JMS, and unescaping when converting JMS to G3D.
    return "".join(_JMS_CHAR_CONVERT_MAP.get(c, c) for c in texname)


def jms_material_to_g3d_texname(material):
    texname = ""
    i = 0
    while i < len(material):
        c = material[i]
        if c == JMS_MATERIAL_ESCAPE_CHAR:
            try:
                c = JMS_MATERIAL_SPECIAL_CHARS[int(material[i+1: i+3], 16)]
                i += 2
            except (IndexError, ValueError):
                pass

        texname += c
        i += 1

    return texname


def g3d_nodes_to_jms_nodes(g3d_nodes):
    if halo_model is None:
        raise NotImplementedError(
            "Reclaimer model module is missing. Please install reclaimer."
            )
    elif g3d_nodes is None:
        raise ValueError("Cannot generate JmsNodes from empty iterable.")

    nodes = []

    children_by_parent = {}
    name_counts = {k: 0 for k in c.DEFAULT_NODE_NAMES}
    for i, g3d_node in enumerate(g3d_nodes):
        x, y, z = g3d_pos_to_halo_pos(*g3d_node.init_pos)
        jms_node = halo_model.JmsNode(
            parent_index=g3d_node.parent,
            pos_x=x, pos_y=y, pos_z=z
            )
        nodes.append(jms_node)

        if jms_node.parent_index != -1:
            children_by_parent.setdefault(jms_node.parent_index, []).append(i)

        name = (
            g3d_node.name if g3d_node.name else
            c.DEFAULT_NODE_NAMES[g3d_node.type_id]
            )

        count             = name_counts.get(name, 0)
        jms_node.name     = name if f"{name}.{count:04}" in name_counts else name
        name_counts[name] = count + 1

    for parent_index, children in children_by_parent.items():
        nodes[parent_index].first_child = children[0]
        for i, child_index in enumerate(children[:-1]):
            nodes[child_index].sibling_index = children[i+1]

    return nodes


def import_jmm_to_g3d(jma, g3d_anim):
    raise NotImplementedError("Write this")


def export_g3d_to_jmm(g3d_anim):
    nodes = g3d_nodes_to_jms_nodes(g3d_anim.nodes)

    jma_frames_data = [
        [halo_anim.JmaNodeState() for i in range(len(g3d_anim.nodes))]
        for f in range(g3d_anim.frame_count)
        ]
    uniform = True
    g3d_anim.generate_frames()
    for n, node in enumerate(g3d_anim.nodes):
        for f, frame_data in enumerate(jma_frames_data):
            jma_ns = frame_data[n]
            rx, ry, rz, px, py, pz, sx, sy, sz = node.get_frame(f)

            jma_ns.pos_x, jma_ns.pos_y, jma_ns.pos_z = g3d_pos_to_halo_pos(px, py, pz)
            jma_ns.rot_w, jma_ns.rot_i, jma_ns.rot_j, jma_ns.rot_k = \
                          g3d_euler_to_jma_quaternion(rx, ry, rz)
            uniform &= (abs(sx - sy) + abs(sy - sz)) < 0.000001
            # NOTE: this is a hack. GDL supports scale independently on
            #       x, y, and z, but halo only supports uniform scale.
            jma_ns.scale = (sx + sy + sz) / 3

    if not uniform:
        print("Warning: Nonuniform scale detected. Averaging to uniform scale.")

    jma = halo_anim.JmaAnimation(
        anim_type="base", frame_info_type="none", world_relative=False,
        frame_rate=g3d_anim.frame_rate, name=g3d_anim.name,
        nodes=nodes, frames=jma_frames_data
        )
    return jma


def import_jms_to_g3d(jms, g3d_model, node_index):
    raise NotImplementedError("Write this")


def export_g3d_to_jms(g3d_nodes, g3d_models):
    nodes = g3d_nodes_to_jms_nodes(g3d_nodes)

    regions = ["base", "lightmap"]
    region_tri_count = [0]*len(regions)
    verts   = []
    tris    = []
    mats    = {}
    for node_i in sorted(g3d_models.keys()):
        g3d_model       = g3d_models[node_i]
        g3d_node, seen  = g3d_nodes[node_i], set()
        gx0, gy0, gz0   = 0, 0, 0
        while id(g3d_node) not in seen:
            seen.add(id(g3d_node))
            gx0 += g3d_node.init_pos[0]
            gy0 += g3d_node.init_pos[1]
            gz0 += g3d_node.init_pos[2]

            if g3d_node.parent >= 0:
                g3d_node = g3d_nodes[g3d_node.parent]

        for reg_i in range(len(regions)):
            g3d_uvs = g3d_model.lm_uvs if reg_i else g3d_model.uvs
            if not g3d_uvs:
                continue

            v0 = len(verts)

            part_verts = [
                halo_model.JmsVertex(
                    node_i, *g3d_pos_to_halo_pos(gx0+gx, gy0+gy, gz0+gz)
                    )
                for gx, gy, gz in g3d_model.verts
                ]
            for vert, norm in zip(part_verts, g3d_model.norms):
                vert.norm_i, vert.norm_j, vert.norm_k = g3d_pos_to_halo_pos(*norm)

            for vert, uvw in zip(part_verts, g3d_uvs):
                vert.tex_u, vert.tex_v, vert.tex_w = g3d_uvw_to_halo_uvw(*uvw)

            verts.extend(part_verts)
            for idx_key in sorted(g3d_model.tri_lists):
                tex_name = idx_key[1] if reg_i else idx_key[0]
                tex_i    = mats.setdefault(tex_name, len(mats))
                tri_list = g3d_model.tri_lists[idx_key]
                region_tri_count[reg_i] += len(tri_list)

                tris.extend(
                    halo_model.JmsTriangle(reg_i, tex_i, a+v0, b+v0, c+v0)
                    for a, b, c in tri_list
                    )

    # remove lightmap region if no tris are in it
    if not region_tri_count[1]: regions.pop(1)

    mats_inv  = {v: k for k, v in mats.items()}
    materials = [
        halo_model.JmsMaterial(g3d_texname_to_jms_material(mats_inv[i]))
        for i in sorted(mats_inv)
        ]
    jms = halo_model.JmsModel(
        materials=materials, regions=regions,
        nodes=nodes, verts=verts, tris=tris
        )
    jms.calculate_vertex_normals()
    return jms
