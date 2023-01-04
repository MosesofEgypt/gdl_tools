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

                rot_norm = vector_util.cross_product(norm, (0, 1, 0))
                rot_norm_len = math.sqrt(rot_norm[0]**2 + rot_norm[1]**2 + rot_norm[2]**2)
                rot_norm_angle = math.asin(max(-1.0, min(1.0, rot_norm_len)))
                if rot_norm_len:
                    rot_norm = (rot_norm[0]/rot_norm_len, rot_norm[1]/rot_norm_len, rot_norm[2]/rot_norm_len)

                x_norm = vector_util.cross_product((0,  0, 1), norm)
                y_axis_angle_cos = vector_util.dot_product((0, 1, 0), norm) # roll
                z_norm = vector_util.cross_product((-1, 0, 0), norm)

                # norm pointing along -z
                    # x_axis angle between y_up and norm == -90
                    # roll right -90 degrees(rotate around z)
                    # yaw  right   0 degrees(rotate around y)
                    # pitch  up  -90 degrees(rotate around x)
                # norm pointing along y
                    # x_axis angle between y_up and norm == 0
                    # roll right   0 degrees(rotate around z)
                    # yaw  right   0 degrees(rotate around y)
                    # pitch  up    0 degrees(rotate around x)
                # norm pointing along -y
                    # x_axis angle between y_up and norm == -180
                    # roll right 180 degrees(rotate around z)
                    # yaw  right   0 degrees(rotate around y)
                    # pitch  up    0 degrees(rotate around x)
                # norm pointing along x
                    # y_axis angle between z_up and norm == -90
                    # roll right  90 degrees(rotate around z)
                    # yaw  right  90 degrees(rotate around y)
                    # pitch   up   0 degrees(rotate around x)

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

                if max(abs(norm[0]), abs(norm[1]), abs(norm[2])) < 0.99999:
                #if norm[0] != 0:
                    # TEMPORARY
                    self.verts.extend((
                        (x0, y0, z0),
                        )*3)
                    continue

                # NOTE: pitch, yaw, roll below assume:
                #   pos world z is forward
                #   pos world y is up
                #   pos world x is right
                if sum(x_norm) == 0:
                    # norm pointing along +z or -z
                    # roll right -90 degrees(rotate around z)
                    # yaw  right   0 degrees(rotate around y)
                    # pitch  up  -90 degrees(rotate around x)
                    x_norm = y_norm  # y_norm points along neg x(pos if norm along neg z)
                    z_norm = z_norm  # z_norm points along neg y(pos if norm along neg z) 
                    if norm[2] >= 0.99999:
                        # norm pointing along +z
                        # rotate 180 degrees around any axis(determine which one)
                        z_norm = (z_norm[0], -z_norm[1], z_norm[2])
                    else:
                        # norm pointing along -z
                        pass

                elif sum(y_norm) == 0:
                    # norm pointing along +y or -y
                    if norm[1] <= -0.99999:
                        # norm pointing along -y
                        # rotate 180 degrees around any axis(determine which one)
                        x_norm = (-x_norm[0], x_norm[1], x_norm[2])
                    else:
                        # norm pointing along y
                        pass

                elif sum(z_norm) == 0:
                    # norm pointing along +x or -x
                    # roll right  90 degrees(rotate around z)
                    # yaw  right  90 degrees(rotate around y)
                    # pitch   up   0 degrees(rotate around x)
                    z_norm = x_norm  # x_norm points along neg y(pos if norm along neg x)
                    x_norm = y_norm  # y_norm points along neg z(pos if norm along neg x)
                    if norm[0] >= 0.99999:
                        # norm pointing along +x
                        # rotate 180 degrees around any axis(determine which one)
                        z_norm = (z_norm[0], -z_norm[1], z_norm[2])
                    else:
                        # norm pointing along -x
                        pass

                # calculate x1, x2, z1, and z2
                x1 = u1 * x_norm[0] + v1 * z_norm[0]
                y1 = u1 * x_norm[1] + v1 * z_norm[1]
                z1 = u1 * x_norm[2] + v1 * z_norm[2]
                x2 = u2 * x_norm[0] + v2 * z_norm[0]
                y2 = u2 * x_norm[1] + v2 * z_norm[1]
                z2 = u2 * x_norm[2] + v2 * z_norm[2]

                y = math.asin(max(-1.0, min(1.0, rot_norm_len)))
                p = math.asin(max(-1.0, min(1.0, rot_norm_len)))
                r = math.asin(max(-1.0, min(1.0, rot_norm_len)))
                rot_quat = vector_util.euler_to_quaternion(y, p, r)
                rot_mat  = vector_util.quaternion_to_matrix(*rot_quat)
                #print(norm)
                #print(rot_mat)

                mat1 = rot_mat * vector_util.Matrix(((u1, ), (0, ), (v1, )))
                mat2 = rot_mat * vector_util.Matrix(((u2, ), (0, ), (v2, )))
                #x1, y1, z1 = mat1[0][0], mat1[1][0], mat1[2][0]
                #x2, y2, z2 = mat2[0][0], mat2[1][0], mat2[2][0]

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
