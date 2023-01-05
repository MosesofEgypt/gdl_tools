import os
import hashlib
import urllib
import math

from . import constants as c
from . import vector_util

FLOAT_INFINITY = float("inf")

class G3DCollision:
    source_file_hash = b'\x00'*16

    def clear(self):
        # Stores the unorganized verts, norms, and uvs
        self.verts  = []
        self.meshes = {}

    def import_g3c(self, coll_tris, mesh_indices):
        self.clear()
        
        for mesh_name, indices in mesh_indices.items():
            v0 = len(self.verts)
            tri_start = indices["index"]
            tri_count = indices["count"]

            for i in range(tri_start, tri_start + tri_count):
                coll_tri = coll_tris[i]

                scale = coll_tri["scale"]
                norm  = tuple(coll_tri["norm"])
                x0, y0, z0 = coll_tri["v0"]

                u1, v1 = coll_tri["v1_x"]  / c.COLL_SCALE, coll_tri["v1_z"]  / c.COLL_SCALE
                u2, v2 = coll_tri["v2_x"]  / c.COLL_SCALE, coll_tri["v2_z"]  / c.COLL_SCALE

                y_axis_angle_cos = math.acos(max(-1.0, min(1.0, vector_util.cos_angle_between_vectors((0, 1, 0), norm))))

                # scale seems to only factor into determining
                # whether or not to rotate the coordinates around y
                y = math.atan2(-norm[0]*scale, -norm[2]*scale) if scale != FLOAT_INFINITY else 0
                r = -y_axis_angle_cos

                # rotations occur in this order:
                #   yaw: around y axis from +z to +x
                # pitch: around x axis from +z to -y
                #  roll: around z axis from +x to +y
                rot_quat = vector_util.euler_to_quaternion(y, 0, r)

                x1, y1, z1 = vector_util.rotate_vector_by_quaternion((u1, 0, v1), rot_quat)
                x2, y2, z2 = vector_util.rotate_vector_by_quaternion((u2, 0, v2), rot_quat)

                self.verts.extend((
                    (x0,      y0,      z0     ),
                    (x1 + x0, y1 + y0, z1 + z0),
                    (x2 + x0, y2 + y0, z2 + z0)
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
