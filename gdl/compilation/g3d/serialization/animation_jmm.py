# EXPERIMENTAL!!! borrowing halo ce animation
# format if the reclaimer module is available

from . import constants as c
from ....rendering.assets.scene_objects.util import gdl_euler_to_quaternion

halo_anim = None
if c.JMM_SUPPORT:
    from reclaimer.animation import jma as halo_anim


def import_jmm_to_g3d(jma, g3d_anim):
    if halo_anim is None:
        raise NotImplementedError(
            "Could not locate reclaimer animation module. Cannot import jmm."
            )
    raise NotImplementedError("Write this")


def export_g3d_to_jmm(g3d_anim):
    if halo_anim is None:
        raise NotImplementedError(
            "Could not locate reclaimer animation module. Cannot export jmm."
            )
    jma_nodes = [
        halo_anim.JmsNode(
            name=node.name, parent_index=node.parent,
            pos_x=node.init_pos[0],
            pos_y=node.init_pos[1],
            pos_z=node.init_pos[2]
            )
        for node in g3d_anim.nodes
        ]
    children_by_parent = {}    
    for i, node in enumerate(jma_nodes):
        if node.parent_index != -1:
            children_by_parent.setdefault(node.parent_index, []).append(i)

        if not node.name:
            node.name = f"__UNNAMED_{i}"

    for parent_index, children in children_by_parent.items():
        jma_nodes[parent_index].first_child = children[0]
        for i, child_index in enumerate(children[:-1]):
            jma_nodes[child_index].sibling_index = children[i+1]

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
        nodes=jma_nodes, frames=jma_frames_data
        )
    return jma
