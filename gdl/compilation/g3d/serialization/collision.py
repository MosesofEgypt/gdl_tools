import os
import hashlib
import urllib
import math

from . import constants as c
from . import vector_util

POS_INFINITY = float("inf")
NEG_INFINITY = -float("inf")

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
            #if mesh_name == "E1STNDE":
            #    print(mesh_name, tri_start, tri_count)

            for i in range(tri_start, tri_start + tri_count):
                coll_tri = coll_tris[i]

                scale = coll_tri["scale"]
                norm  = tuple(coll_tri["norm"])
                x0, y0, z0 = coll_tri["v0"]

                unpack_scale  = 1 / c.COLL_SCALE
                if scale not in (POS_INFINITY, NEG_INFINITY):
                    unpack_scale *= scale

                min_y, max_y = coll_tri["min_y"] * unpack_scale, coll_tri["max_y"] * unpack_scale
                u1,     v1   = coll_tri["v1_x"]  * unpack_scale, coll_tri["v1_z"]  * unpack_scale
                u2,     v2   = coll_tri["v2_x"]  * unpack_scale, coll_tri["v2_z"]  * unpack_scale

                # cross the normal with the axis rays to get the
                # normals the x and z axis will move along the plane
                x_norm = vector_util.cross_product(norm, (0,  0, 1))
                y_norm = vector_util.cross_product(norm, (0,  1, 0))
                z_norm = vector_util.cross_product(norm, (-1, 0, 0))
                x_norm_len = math.sqrt(x_norm[0]**2 + x_norm[1]**2 + x_norm[2]**2)
                y_norm_len = math.sqrt(y_norm[0]**2 + y_norm[1]**2 + y_norm[2]**2)
                z_norm_len = math.sqrt(z_norm[0]**2 + z_norm[1]**2 + z_norm[2]**2)

                # normalize
                if x_norm_len:
                    x_norm = (x_norm[0]/x_norm_len, x_norm[1]/x_norm_len, x_norm[2]/x_norm_len)
                if y_norm_len:
                    y_norm = (y_norm[0]/y_norm_len, y_norm[1]/y_norm_len, y_norm[2]/y_norm_len)
                if z_norm_len:
                    z_norm = (z_norm[0]/z_norm_len, z_norm[1]/z_norm_len, z_norm[2]/z_norm_len)

                if sum(x_norm) + sum(y_norm) + sum(z_norm) not in (2.0, 0.0, -2.0):
                    # TEMPORARY
                    self.verts.extend((
                        (x0, y0, z0),
                        )*3)
                    continue
                    
                if sum(x_norm) == 0:
                    x_norm = y_norm
                    if norm[2] > 0.999999:
                        z_norm = (z_norm[0], -z_norm[1], z_norm[2])
                elif sum(y_norm) == 0:
                    if norm[1] > 0.999999:
                        z_norm = (z_norm[0], -z_norm[1], z_norm[2])
                elif sum(z_norm) == 0:
                    z_norm = x_norm
                    x_norm = y_norm
                    if norm[0] >= 0.999999:
                        z_norm = (z_norm[0], -z_norm[1], z_norm[2])

                # calculate x1, x2, z1, and z2
                x1 = u1 * x_norm[0] + v1 * z_norm[0]
                y1 = u1 * x_norm[1] + v1 * z_norm[1]
                z1 = u1 * x_norm[2] + v1 * z_norm[2]
                x2 = u2 * x_norm[0] + v2 * z_norm[0]
                y2 = u2 * x_norm[1] + v2 * z_norm[1]
                z2 = u2 * x_norm[2] + v2 * z_norm[2]
                '''
                rot = vector_util.Matrix((
                    (norm[0], 0, 0),
                    (0, norm[1], 0),
                    (0, 0, norm[2]),
                    ))
                x1, y1, z1 = rot * vector_util.Matrix(((u1, ), (0, ), (v1, )))
                x2, y2, z2 = rot * vector_util.Matrix(((u2, ), (0, ), (v2, )))'''

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
