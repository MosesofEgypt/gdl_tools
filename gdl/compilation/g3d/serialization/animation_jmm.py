# EXPERIMENTAL!!! borrowing halo ce animation
# format if the reclaimer module is available

from . import constants as c

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

    jma_frame_data  = []

    jma = halo_anim.JmaAnimation(
        anim_type="base", frame_info_type="none", world_relative=False,
        frame_rate=g3d_anim.frame_rate, name=g3d_anim.name,
        nodes=jma_nodes, frames=jma_frame_data
        )
    return jma
