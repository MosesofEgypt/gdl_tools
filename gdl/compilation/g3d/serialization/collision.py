import os
import hashlib
import urllib
import math

from . import constants as c
from . import vector_util


class CollisionTriangle:
    min_y = 0.0
    max_y = 0.0
    scale = 1.0
    n_i  = 0.0; n_j  = 1.0; n_k  = 0.0
    v0_x = 0.0; v0_y = 0.0; v0_z = 0.0
    v1_x = 1.0;             v1_z = 0.0
    v2_x = 0.0;             v2_z = 1.0
    _v1  = None
    _v2  = None
    def __init__(self, **kwargs):
        self.min_y = float(kwargs.get("min_y", self.min_y))
        self.max_y = float(kwargs.get("max_y", self.max_y))
        self.scale = float(kwargs.get("scale", self.scale))

        self.n_i,  self.n_j,  self.n_k  = tuple(float(v) for v in kwargs.get("norm", self.norm))
        self.v0_x, self.v0_y, self.v0_z = tuple(float(v) for v in kwargs.get("v0", self.v0))
        self.v1_x, self.v1_z = tuple(float(v) for v in kwargs.get("v1_xz", self.v1_xz))
        self.v2_x, self.v2_z = tuple(float(v) for v in kwargs.get("v2_xz", self.v2_xz))

    @property
    def norm(self):  return (self.n_i, self.n_j, self.n_k)
    @property
    def v0(self):    return (self.v0_x, self.v0_y, self.v0_z)
    @property
    def v1(self):
        if not self._v1:
            self._v1 = self.local_xz_to_world_xyz(self.v1_x, self.v1_z)
        return self._v1
    @property
    def v2(self):
        if not self._v2:
            self._v2 = self.local_xz_to_world_xyz(self.v2_x, self.v2_z)
        return self._v2
    @property
    def v1_xz(self): return (self.v1_x, self.v1_z)
    @property
    def v2_xz(self): return (self.v2_x, self.v2_z)

    def local_xz_to_world_xyz(self, vx, vz):
        rot_quat = vector_util.gdl_normal_to_quaternion(
            -self.n_i * self.scale,
            self.n_j,
            -self.n_k * self.scale
            )
        vd = vector_util.rotate_vector_by_quaternion(
            (vx, 0, vz), rot_quat
            )

        # add the v0 offset
        return (self.v0_x + vd[0],
                self.v0_y + vd[1],
                self.v0_z + vd[2])

    def snap_to_y_plane(self, x, y, z, max_dist=float("inf"), up=(0, 1.0, 0)):
        # dont snap to upside-down or horizontal surfaces
        is_rightside_up = vector_util.dot_product(up, self.norm) > 0
        if not (self.n_j and is_rightside_up):
            return None

        # check to ensure the triangle is at all level with the x/z plane,
        # and the point is inside the triangle(viewed from the x/z plane)
        is_inside_coll_tri = vector_util.point_inside_2d_triangle(
            (x, z),
            (self.v0_x,  self.v0_z),
            (self.v1[0], self.v1[2]),
            (self.v2[0], self.v2[2])
            )
        if not is_inside_coll_tri:
            return None

        # using the equation of a plane, solve for the y coordinate
        new_y = self.v0_y + (
            self.n_i*(x - self.v0_x) +
            self.n_k*(z - self.v0_z)
            ) / -self.n_j

        # if the y delta is too large, don't snap
        return None if (
            abs(y - new_y) > max_dist or 
            new_y - c.Y_GRID_SNAP_TOLERANCE > self.max_y or
            new_y + c.Y_GRID_SNAP_TOLERANCE < self.min_y
            ) else new_y


class G3DCollision:
    source_file_hash = b'\x00'*16

    def __init__(self):
        self.clear()

    def clear(self):
        self.verts  = []
        self.meshes = {}

    def import_g3c(self, coll_tris, mesh_indices):
        self.clear()

        for mesh_name, indices in mesh_indices.items():
            v0 = len(self.verts)
            tri_start = indices["index"]
            tri_count = indices["count"]

            for i in range(tri_start, tri_start + tri_count):
                self.verts.extend((
                    coll_tris[i].v0,
                    coll_tris[i].v1,
                    coll_tris[i].v2,
                    ))

            self.meshes[mesh_name] = [
                (i, i + 1, i + 2)
                for i in range(v0*3, (v0 + tri_count)*3, 3)
                ]

    def import_obj(self, output_filepath):
        raise NotImplementedError("TODO")

    def export_obj(self, output_filepath):
        obj_str = '\n'.join((
            '# Gauntlet Dark Legacy collision model',
            '#     Extracted by Moses',
            ))
        obj_str += '\n\n'
        obj_str += '\n'.join((
            'v %.7f %.7f %.7f' % (-v[0], v[1], v[2]) for v in self.verts
            ))
        obj_str += '\n'

        # collect all all tris, verts, uvw, normals, and texture indexes
        for mesh_name in sorted(self.meshes):
            if not self.meshes[mesh_name]:
                continue

            obj_str += 'g %s\n' % urllib.parse.quote(mesh_name)

            # write the triangles
            for tri in self.meshes[mesh_name]:
                # obj indices are ones based
                obj_str += 'f %s %s %s\n' % (tri[0]+1, tri[1]+1, tri[2]+1)

        obj_bytes = obj_str.encode()
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        with open(output_filepath, 'wb+') as f:
            f.write(obj_bytes)

        self.source_file_hash = hashlib.md5(obj_bytes).digest()

    def export_g3c(self, output_filepath):
        raise NotImplementedError("TODO")
