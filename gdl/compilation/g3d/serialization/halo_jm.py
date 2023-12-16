# EXPERIMENTAL!!! borrowing halo ce animation
# format if the reclaimer module is available

from . import constants as c
from ....rendering.assets.scene_objects.util import gdl_euler_to_quaternion

halo_anim = halo_model = None
if c.JMS_SUPPORT:
    from reclaimer.model import jms as halo_model
    from reclaimer.animation import jma as halo_anim


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
        jms_node = halo_model.JmsNode(
            parent_index=g3d_node.parent,
            pos_x=g3d_node.init_pos[0],
            pos_y=g3d_node.init_pos[1],
            pos_z=g3d_node.init_pos[2]
            )
        nodes.append(jms_node)

        if jms_node.parent_index != -1:
            children_by_parent.setdefault(jms_node.parent_index, []).append(i)

        name = (
            g3d_node.name if g3d_node.name else
            c.DEFAULT_NODE_NAMES[g3d_node.type_id]
            )

        count               = name_counts.get(name, 0)
        jms_node.name       = name if f"{name}.{count:04}" in name_counts else name
        name_counts[name]   = count + 1

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
    for f, frame_data in enumerate(jma_frames_data):
        for n, node in enumerate(g3d_anim.nodes):
            jma_ns = frame_data[n]
            px, py, pz, rx, ry, rz, sx, sy, sz = node.get_frame_data(f)

            jma_ns.pos_x, jma_ns.pos_y, jma_ns.pos_z = (px, py, pz)
            jma_ns.rot_w, jma_ns.rot_i, jma_ns.rot_j, jma_ns.rot_k = \
                          gdl_euler_to_quaternion(rx, ry, rz)
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
    verts   = []
    tris    = []
    mats    = {}
    for node_i in sorted(g3d_models.keys()):
        g3d_model   = g3d_models[node_i]
        x0, y0, z0  = 0, 0, 0
        parent      = node_i

        seen = set()
        while parent >= 0:
            if parent in seen:
                raise ValueError("Recursive nodes in G3DModel.")

            seen.add(parent)
            pos, parent = g3d_nodes[parent].init_pos, g3d_nodes[parent].parent
            x0, y0, z0  = x0+pos[0], y0+pos[1], z0+pos[2]

        for reg_i in range(len(regions)):
            g3d_uvs = g3d_model.lm_uvs if reg_i else g3d_model.uvs
            if not g3d_uvs:
                continue

            vs = len(verts)

            part_verts = [
                halo_model.JmsVertex(
                    node_i, x0+vert[0], y0+vert[1], z0+vert[2]
                    )
                for vert in g3d_model.verts
                ]
            for i, norm in enumerate(g3d_model.norms):
                part_verts[i].norm_i = norm[0]
                part_verts[i].norm_j = norm[1]
                part_verts[i].norm_k = norm[2]

            if len(g3d_uvs[0]) < 3:
                for i, uv in enumerate(g3d_uvs):
                    part_verts[i].tex_u = uv[0]
                    part_verts[i].tex_v = uv[1]
            else:
                for i, uv in enumerate(g3d_uvs):
                    part_verts[i].tex_u = uv[0]
                    part_verts[i].tex_v = uv[1]
                    part_verts[i].tex_w = uv[2]

            verts.extend(part_verts)
            for idx_key in sorted(g3d_model.tri_lists):
                tex_i   = mats.setdefault(
                    idx_key[1] if reg_i else idx_key[0], len(mats)
                    )

                tris.extend(
                    halo_model.JmsTriangle(
                        reg_i, tex_i, v0+vs, v1+vs, v2+vs
                        )
                    for v0, v1, v2 in g3d_model.tri_lists[idx_key]
                    )

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
