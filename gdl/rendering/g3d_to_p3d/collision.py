from panda3d.core import CollisionPolygon, CollisionNode, Point3

from ..assets.collision import Collision, CollisionObject, CollisionObjectGrid
from ...compilation.g3d.serialization.collision import G3DCollision


def load_collision_from_worlds_tag(
        worlds_tag, collision_name, tri_index, tri_count
        ):
    if tri_index < 0 or tri_count <= 0:
        return None

    collision = Collision(
        name=collision_name,
        p3d_collision=CollisionNode(collision_name),
        )
    g3d_collision = G3DCollision()
    g3d_collision.import_g3c(
        worlds_tag.get_collision_tris(),
        {collision_name: dict(index=tri_index, count=tri_count)}
        )

    verts = g3d_collision.verts
    for tri in g3d_collision.meshes[collision_name]:
        v0 = verts[tri[0]]
        v1 = verts[tri[1]]
        v2 = verts[tri[2]]
        coll_tri = CollisionPolygon(
            Point3(v0[0], v0[2], v0[1]),
            Point3(v2[0], v2[2], v2[1]),
            Point3(v1[0], v1[2], v1[1]),
            )
        collision.p3d_collision.add_solid(coll_tri)

    return collision


def load_collision_grid_from_worlds_tag(worlds_tag):
    world_objects = worlds_tag.data.world_objects
    header        = worlds_tag.data.header
    collision_tris = worlds_tag.get_collision_tris()
    collision_grid = CollisionObjectGrid(
        min_x       = header.world_min_bounds.x,
        min_z       = header.world_min_bounds.z,
        width       = header.grid_number_x,
        height      = header.grid_number_z,
        grid_size   = header.grid_size,
        )

    for z, grid_row in enumerate(worlds_tag.data.grid_rows):
        x0 = grid_row.first
        for x, grid_entry in enumerate(grid_row.grid_entries):
            cell = collision_grid.get_collision_cell_at_grid_pos(x0+x, z)
            for entry in grid_entry.grid_entry_list:
                world_object = world_objects[entry.collision_object_index]
                name = world_object.name.upper().strip()
                tris = tuple(
                    collision_tris[world_object.coll_tri_index + tri_n]
                    for tri_n in entry.tri_indices
                    )

                cell[name] = CollisionObject(tris=tris)

    for i in worlds_tag.data.dynamic_grid_objects.world_object_indices:
        world_object = world_objects[i]
        tris = tuple(
            collision_tris[world_object.coll_tri_index + tri_n]
            for tri_n in range(world_object.coll_tri_count)
            )

        radius_sq = 0.0
        for tri in tris:
            radius_sq = max(
                radius_sq,
                (tri.v0[0]**2 + tri.v0[1]**2 + tri.v0[2]**2),
                (tri.v1[0]**2 + tri.v1[1]**2 + tri.v1[2]**2),
                (tri.v2[0]**2 + tri.v2[1]**2 + tri.v2[2]**2),
                )

        collision_grid.add_dynamic_collision_object(
            CollisionObject(tris=tris, radius_sq=radius_sq),
            world_object.name
            )

    return collision_grid
