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

        unit_scale = 1 / c.COLL_SCALE
        for mesh_name, indices in mesh_indices.items():
            v0 = len(self.verts)
            tri_start = indices["index"]
            tri_count = indices["count"]

            for i in range(tri_start, tri_start + tri_count):
                coll_tri = coll_tris[i]

                scale = coll_tri["scale"]
                norm  = tuple(coll_tri["norm"])
                x0, y0, z0 = coll_tri["v0"]

                u1, v1 = coll_tri["v1_x"], coll_tri["v1_z"]
                u2, v2 = coll_tri["v2_x"], coll_tri["v2_z"]

                r_cos = max(-1.0, min(1.0, vector_util.cos_angle_between_vectors((0, 1, 0), norm)))

                y = math.atan2(-norm[0]*scale, -norm[2]*scale) if scale != FLOAT_INFINITY else 0
                r = math.acos(r_cos)

                # rotations occur in this order:
                #   yaw: around y axis from +z to +x
                #  roll: around z axis from +x to +y
                c0, c1 = math.cos(y / 2), math.cos(r / 2)
                s0, s1 = math.sin(y / 2), math.sin(r / 2)
                rot_quat = (-c0*s1, s0*c1, s0*s1, c0*c1)

                v1_d = vector_util.rotate_vector_by_quaternion((u1, 0, v1), rot_quat)
                v2_d = vector_util.rotate_vector_by_quaternion((u2, 0, v2), rot_quat)

                # scale to world units and add the v0 offset
                x1 = x0 + v1_d[0]*unit_scale
                y1 = y0 + v1_d[1]*unit_scale
                z1 = z0 + v1_d[2]*unit_scale
                x2 = x0 + v2_d[0]*unit_scale
                y2 = y0 + v2_d[1]*unit_scale
                z2 = z0 + v2_d[2]*unit_scale
                self.verts.extend((
                    (x0, y0, z0),
                    (x1, y1, z1),
                    (x2, y2, z2),
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
