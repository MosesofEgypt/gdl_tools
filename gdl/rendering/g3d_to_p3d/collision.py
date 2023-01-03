from panda3d.core import NodePath, CollisionPolygon, CollisionNode, Point3

from ..assets.collision import CollisionMesh
from ...compilation.g3d.serialization.collision import G3DCollision


def load_collision_from_worlds_tag(
        worlds_tag, collision_name, tri_index, tri_count
        ):
    collision = CollisionMesh(
        name=collision_name,
        p3d_collision=CollisionNode(collision_name),
        )
    g3d_collision = G3DCollision()
    g3d_collision.import_g3c(
        worlds_tag.data.coll_tris,
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
