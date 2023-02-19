from .tag import GdlTag
from ...compilation.g3d.serialization import constants as serial_const
from ...compilation.g3d.serialization.collision import CollisionTriangle


class WorldsTag(GdlTag):
    _collision_grid_tris = None

    def get_collision_tris(self, rebuild=False):
        if self._collision_grid_tris is None or rebuild:
            # scale to world units
            unit_scale = 1 / serial_const.COLL_SCALE
            self._collision_grid_tris = tuple(
                CollisionTriangle(
                    min_y = tri.min_y * unit_scale,
                    max_y = tri.max_y * unit_scale,
                    scale = tri.scale,
                    norm  = tri.norm,
                    v0    = tri.v0,
                    v1_xz = (tri.v1_x * unit_scale, tri.v1_z * unit_scale),
                    v2_xz = (tri.v2_x * unit_scale, tri.v2_z * unit_scale),
                    )
                for tri in self.data.coll_tris
                )

        return self._collision_grid_tris

    def set_pointers(self, offset):
        # TODO: write pointer calculation code
        pass
