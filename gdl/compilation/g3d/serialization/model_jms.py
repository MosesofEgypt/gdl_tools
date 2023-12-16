# EXPERIMENTAL!!! borrowing halo ce model
# format if the reclaimer module is available

from . import constants as c
from ....rendering.assets.scene_objects.util import gdl_euler_to_quaternion

halo_model = None
if c.JMS_SUPPORT:
    from reclaimer.model import jms as halo_model


def import_jms_to_g3d(jms, g3d_model, node_index):
    raise NotImplementedError("Write this")


def export_g3d_to_jms(g3d_nodes, g3d_models):
    if halo_model is None:
        raise NotImplementedError(
            "Could not locate reclaimer model module. Cannot export jms."
            )
    elif g3d_nodes is None:
        raise ValueError("Cannot export JMS model with no nodes.")

    nodes = [
        halo_model.JmsNode(
            name=node.name, parent_index=node.parent,
            pos_x=node.init_pos[0],
            pos_y=node.init_pos[1],
            pos_z=node.init_pos[2]
            )
        for node in g3d_nodes
        ]

    children_by_parent = {}    
    for i, node in enumerate(nodes):
        if node.parent_index != -1:
            children_by_parent.setdefault(node.parent_index, []).append(i)

        if not node.name:
            node.name = f"__UNNAMED_{i}"

    for parent_index, children in children_by_parent.items():
        nodes[parent_index].first_child = children[0]
        for i, child_index in enumerate(children[:-1]):
            nodes[child_index].sibling_index = children[i+1]

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
        halo_model.JmsMaterial(mats_inv[i])
        for i in sorted(mats_inv)
        ]
    jms = halo_model.JmsModel(
        materials=materials, regions=regions,
        nodes=nodes, verts=verts, tris=tris
        )
    return jms

