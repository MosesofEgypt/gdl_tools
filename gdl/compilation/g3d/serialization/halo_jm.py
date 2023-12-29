# EXPERIMENTAL!!! borrowing halo ce animation
# format if the reclaimer module is available
from math import cos, sin, pi, sqrt
from . import constants as c, vector_util
from ....rendering.assets.scene_objects.util import gdl_euler_to_quaternion

# TODO: create subclass of JmsModel to support halo 3 JMS enough to read them.
#       do the same with JmaAnimation enough to support custom halo 3 JMA.

halo_anim = halo_model = None
if c.JMS_SUPPORT:
    from reclaimer.model import jms as halo_model
    from reclaimer.animation import jma as halo_anim


# Converting from gauntlet coordinate system to Halo coordinates is 
# pretty simple, and just requires swapping y and z and scaling 
def g3d_pos_to_halo_pos(x, y, z): return x*10, z*10, y*10
def halo_pos_to_g3d_pos(x, y, z): return x/10, z/10, y/10

# converting uvw is easy. just invert the v coordinate
def g3d_uvw_to_halo_uvw(u, v, w=0.0): return u, 1.0-v, w
halo_uvw_to_g3d_uvw = g3d_uvw_to_halo_uvw


def g3d_euler_to_jma_quaternion(h, p, r, invert=True):
    w, i, j, k = gdl_euler_to_quaternion(-r, -p, -h)
    if not invert:
        return (w, i, j, k)

    length = i**2 + j**2 + k**2 + w**2
    scale = -1/sqrt(length) if length else 1
    return (-w*scale, i*scale, j*scale, k*scale)


def jma_quaternion_to_g3d_euler(h, p, r):
    raise NotImplementedError("Not implemented yet")


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
    texname, i = "", 0
    # look, I've been writing perl for 4 years now, and
    # I've gotten really good at regex. I could easily
    # write a regex for this, but I just don't want to.
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
    for i, g3d_node in enumerate(g3d_nodes):
        x, y, z = g3d_pos_to_halo_pos(*g3d_node.init_pos)
        jms_node = halo_model.JmsNode(
            name=g3d_node.name, parent_index=max(-1, g3d_node.parent),
            pos_x=x, pos_y=y, pos_z=z
            )
        nodes.append(jms_node)

        if jms_node.parent_index != -1:
            children_by_parent.setdefault(jms_node.parent_index, []).append(i)

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
        name=g3d_anim.name, frame_rate=30**2/max(1, g3d_anim.frame_rate),
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
