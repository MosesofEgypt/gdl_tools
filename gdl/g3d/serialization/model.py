import hashlib
import os
import struct
import urllib

from array import array
from sys import byteorder

from math import sqrt
from traceback import format_exc

from ..stripify import Stripifier
from . import constants as c
from . import util

OBJECT_HEADER_STRUCT = struct.Struct('<fIIII 12x 16s')
#   bounding_radius
#   vert_count
#   tri_count
#   geom_count
#   flags
#   12_padding_bytes
#   md5_of_source_asset

SUBOBJ_HEADER_STRUCT = struct.Struct('<Hh 12x 32s 32s')
#   quadword_count
#   lod_k
#   12_padding_bytes
#   texture_name
#   lightmap_name

STREAM_HEADER_STRUCT = struct.Struct('<BBBB')
#   data_type
#   flags
#   count
#   storage_type

STREAM_DATA_STRUCTS = {
    (c.DATA_TYPE_GEOM,  c.STORAGE_TYPE_NULL)             : struct.Struct('<'),
    (c.DATA_TYPE_GEOM,  c.STORAGE_TYPE_STRIP_0_END)      : struct.Struct('<'),
    (c.DATA_TYPE_GEOM,  c.STORAGE_TYPE_STRIP_N_END)      : struct.Struct('<'),
    (c.DATA_TYPE_GEOM,  c.STORAGE_TYPE_FLOAT32)          : struct.Struct('<I4sff'),
    (c.DATA_TYPE_POS,   c.STORAGE_TYPE_FLOAT32)          : struct.Struct('<ffff'),
    (c.DATA_TYPE_POS,   c.STORAGE_TYPE_SINT32_XYZ)       : struct.Struct('<iii'),
    (c.DATA_TYPE_POS,   c.STORAGE_TYPE_SINT16_XYZ)       : struct.Struct('<hhh'),
    (c.DATA_TYPE_POS,   c.STORAGE_TYPE_SINT8_XYZ)        : struct.Struct('<bbb'),
    (c.DATA_TYPE_NORM,  c.STORAGE_TYPE_UINT16_BITPACKED) : struct.Struct('<H'),
    (c.DATA_TYPE_COLOR, c.STORAGE_TYPE_UINT16_BITPACKED) : struct.Struct('<H'),
    (c.DATA_TYPE_UV,    c.STORAGE_TYPE_UINT32_UV)        : struct.Struct('<II'),
    (c.DATA_TYPE_UV,    c.STORAGE_TYPE_UINT16_UV)        : struct.Struct('<HH'),
    (c.DATA_TYPE_UV,    c.STORAGE_TYPE_UINT8_UV)         : struct.Struct('<BB'),
    (c.DATA_TYPE_UV,    c.STORAGE_TYPE_UINT16_LMUV)      : struct.Struct('<HHHH'),
    (c.DATA_TYPE_UV,    c.STORAGE_TYPE_UNKNOWN)          : struct.Struct('<'),
    }


def pack_g3d_stream_header(buffer, d_type, s_type, flags=0, count=0):
    buffer.write(STREAM_HEADER_STRUCT.pack(d_type, flags, count, s_type))


class G3DModel():

    source_file_hash = b'\x00'*16

    def __init__(self, *args, **kwargs):        
        self.stripifier = Stripifier()
        self.stripifier.max_strip_len = c.MAX_STRIP_LEN
        self.stripifier.degen_link = False

        #set up the instance variables
        self.clear()

    def clear(self):
        # Stores the unorganized verts, norms, and uvs
        self.verts  = []
        self.norms  = []
        self.uvs    = []
        self.lm_uvs = []
        self.colors = []

        self.lod_ks   = {c.DEFAULT_INDEX_KEY: c.DEFAULT_LOD_K}
        self.all_tris = {c.DEFAULT_INDEX_KEY: []}
        
        self.all_dont_draws   = {}
        self.all_vert_maxs    = {}
        self.all_uv_shifts    = {}
        self.all_lm_uv_shifts = {}
        self.all_uv_maxs      = {}

        self.bnd_rad = 0.0

    def make_strips(self):
        '''load the triangles into the stripifier, calculate
        strips, and link them together as best as possible'''
        self.stripifier.load_mesh(self.all_tris)
        self.stripifier.make_strips()
        self.stripifier.link_strips()

        vert_data  = self.stripifier.vert_data
        all_strips = self.stripifier.all_strips

        self.all_dont_draws   = {idx_key: [] for idx_key in all_strips}
        self.all_vert_maxs    = {idx_key: [] for idx_key in all_strips}
        self.all_uv_maxs      = {idx_key: [] for idx_key in all_strips}
        self.all_uv_shifts    = {idx_key: [] for idx_key in all_strips}
        self.all_lm_uv_shifts = {idx_key: [] for idx_key in all_strips}

        '''calculate the max vert and uv sizes for each strip
        and calculate the dont_draws from the all_degens lists'''
        for idx_key, strips in all_strips.items():
            degens = self.stripifier.all_degens[idx_key]

            #loop over each strip
            for i in range(len(strips)):

                # flag all degen tris and as not drawn
                d_draw = [0] * len(strips[i])
                self.all_dont_draws[idx_key].append(d_draw)

                # first 2 are never rendered cause theres not 3 verts yet.
                for d in (0, 1, *degens[i]):
                    d_draw[d] = 1

                uv_max_x    = uv_max_y    = vert_max = 0
                uv_min_x    = uv_min_y    = 0xffFFffFF
                lm_uv_min_x = lm_uv_min_y = 0xffFFffFF
                #calcualte the vert and uv maxs
                for v_i in strips[i]:
                    vert = vert_data[v_i]
                    pos_index, uv_index = vert[:2]

                    #get the largest axis values for this verts position and uvs
                    vert_max = max(
                        max(self.verts[pos_index]),
                        -min(self.verts[pos_index]),
                        vert_max
                        )
                    if self.uvs:
                        uv_min_x    = min(self.uvs[uv_index][0], uv_min_x)
                        uv_max_x    = max(self.uvs[uv_index][0], uv_max_x)
                        uv_min_y    = min(self.uvs[uv_index][1], uv_min_y)
                        uv_max_y    = max(self.uvs[uv_index][1], uv_max_y)

                    if self.lm_uvs:
                        lm_uv_min_x = min(self.lm_uvs[uv_index][0], lm_uv_min_x)
                        lm_uv_min_y = min(self.lm_uvs[uv_index][1], lm_uv_min_y)

                # uv_shift is expected to be negative, as we add it to
                # the uvs to shift them to the [0, 1] uv range
                # NOTE: converting to int to only shift whole canvas steps
                uv_shift_x    = -int(uv_min_x)
                uv_shift_y    = -int(uv_min_y)
                lm_uv_shift_x = -int(lm_uv_min_x)
                lm_uv_shift_y = -int(lm_uv_min_y)

                self.all_uv_shifts[idx_key].append((uv_shift_x, uv_shift_y))
                self.all_lm_uv_shifts[idx_key].append((lm_uv_shift_x, lm_uv_shift_y))
                self.all_vert_maxs[idx_key].append(vert_max)
                self.all_uv_maxs[idx_key].append(max(
                    uv_max_x + uv_shift_x,
                    uv_max_y + uv_shift_y
                    ))

    def import_g3d(
            self, input_buffer, headerless=False, subobj_count=1,
            stream_len=-1, tex_name="", lm_name="", lod_k=c.DEFAULT_LOD_K
            ):

        if subobj_count > 1 and headerless:
            raise ValueError("Cannot import multiple headerless g3d model streams.")

        if stream_len < 0:
            stream_len = len(input_buffer) - input_buffer.tell()

        for i in range(subobj_count):
            buffer_start = input_buffer.tell()
            buffer_end   = len(input_buffer)
            if not headerless:
                rawdata = input_buffer.read(SUBOBJ_HEADER_STRUCT.size)
                if len(rawdata) < SUBOBJ_HEADER_STRUCT.size:
                    return

                qword_count, lod_k, tex_name, lm_name = SUBOBJ_HEADER_STRUCT.unpack(rawdata)
                # NOTE: qword count doesn't include the header, so add 1
                stream_len = qword_count * 16

            g3d_end = min(buffer_end, stream_len + buffer_start)

            tex_name = tex_name.upper()
            lm_name  = lm_name.upper()
            idx_key = (tex_name, lm_name)
            bnd_rad_square = 0.0
            strip_count = 0

            verts       = []
            norms       = []
            colors      = []
            uvs         = []
            lm_uvs      = []
            faces_drawn = []
            face_dirs   = []
        
            if c.DEBUG:
                print('pos:%s,\ttex_name:"%s",\tlm_name:"%s",\tlod_k:%s' %
                      (buffer_start, tex_name, lm_name, lod_k - 4)
                      )

            #scan over all the data in the stream
            while input_buffer.tell() + STREAM_HEADER_STRUCT.size < g3d_end:
                # ensure we're always 4-byte aligned
                input_buffer.read(util.calculate_padding(
                    input_buffer.tell(), STREAM_HEADER_STRUCT.size
                    ))

                # read the header data and unpack it
                rawdata = input_buffer.read(STREAM_HEADER_STRUCT.size)
                if len(rawdata) < STREAM_HEADER_STRUCT.size:
                    break

                data_type, flags, count, storage_type = STREAM_HEADER_STRUCT.unpack(rawdata)
                stream_struct = STREAM_DATA_STRUCTS.get((data_type, storage_type))

                investigate = False
                if (data_type != c.DATA_TYPE_GEOM and
                    ((data_type != c.DATA_TYPE_UV and flags != c.STREAM_FLAGS_DEFAULT) or
                     (data_type == c.DATA_TYPE_UV and flags != c.STREAM_FLAGS_UV_DEFAULT and flags != 4))
                    ):
                    investigate = True

                if investigate or c.DEBUG or stream_struct is None:
                    print('pos:%s,\tdata_type:%s,\tflags:%s,\tcount:%s,\tstorage_type:%s' %
                          (input_buffer.tell() - STREAM_HEADER_STRUCT.size,
                           data_type, flags, count, storage_type)
                          )

                if stream_struct is None:
                    raise ValueError('Unknown data stream')

                stream_format = stream_struct.format.strip("<>")
                stream_stride = stream_struct.size
                rawdata = input_buffer.read(stream_stride*count)
                if len(rawdata) < stream_stride*count:
                    break

                data = []
                # if the struct format character is the same for every field, it's uniform
                if stream_format and (stream_format[0] * len(stream_format) == stream_format):
                    # data is uniform, so we can quickly unpack it as an array
                    data = array(stream_format[0], rawdata)
                    if byteorder == ">":
                        data.byteswap()
                elif stream_stride:
                    # non-uniform data, so must unpack in chunks
                    unpacker = stream_struct.unpack
                    for j in range(0, len(rawdata), stream_stride):
                        data.extend(unpacker(rawdata[j: j + stream_stride]))


                if storage_type in (c.STORAGE_TYPE_NULL, c.STORAGE_TYPE_STRIP_N_END, c.STORAGE_TYPE_STRIP_0_END):
                    # we're reading the padding at EOF, or this is a strip terminator
                    pass
                elif storage_type == c.STORAGE_TYPE_FLOAT32:
                    if data_type == c.DATA_TYPE_GEOM:
                        # triangle strip. only need the face direction from it
                        face_dirs.append(data[2])
                    elif data_type == c.DATA_TYPE_POS:
                        # append a single triangle
                        strip_count += 1
                        faces_drawn.append([0])
                        face_dirs.append(1.0)

                        # NOTE: we're ignoring the count here because it's not possible to
                        #       store more than a single triangle here. the count MUST be 12

                        # positions
                        for j in range(0, 12, 4):
                            scale = data[j+3]
                            x, y, z = data[j]/scale, data[j+1]/scale, data[j+2]/scale
                            verts.append([x, y, z])
                            bnd_rad_square = max(x**2 + y**2 + z**2, bnd_rad_square)

                        # normals
                        for j in range(12, 24, 4):
                            scale = data[j+3]
                            norms.append([data[j]*scale, data[j+1]*scale, data[j+2]*scale])

                        # colors
                        for j in range(24, 36, 4):
                            r, g, b, a = data[j]/255, data[j+1]/255, data[j+2]/255, data[j+3]/255
                            colors.append([r, g, b, a])

                        # uv coords
                        for j in range(36, 48, 4):
                            u, v, w = data[j], data[j+1], data[j+2]
                            uvs.append([u, v, w])

                elif data_type == c.DATA_TYPE_POS:
                    # make sure to ignore the last vertex
                    for j in range(0, len(data)-3, 3):
                        x, y, z = data[j]/c.POS_SCALE, data[j+1]/c.POS_SCALE, data[j+2]/c.POS_SCALE
                        verts.append([x, y, z])
                        bnd_rad_square = max(x**2 + y**2 + z**2, bnd_rad_square)

                    strip_count += 1

                elif data_type == c.DATA_TYPE_NORM:
                    dont_draw = []

                    for j in range(len(data)):
                        norm = data[j]
                        xn  = (norm&31)/15 - 1
                        yn  = ((norm>>5)&31)/15 - 1
                        zn  = ((norm>>10)&31)/15 - 1
                        mag = sqrt(xn*xn + yn*yn + zn*zn) + 0.0000001

                        norms.append([xn/mag, yn/mag, zn/mag])  # x-axis is reversed
                        # the last bit determines if a face is to be
                        # drawn or not. 0 means draw, 1 means dont draw
                        dont_draw.append(bool(norm&0x8000))

                    # make sure the first 2 are removed since they
                    # are always 1 and triangle strips are always
                    # made of 2 more verts than there are triangles
                    faces_drawn.append(dont_draw[2:])

                elif data_type == c.DATA_TYPE_COLOR:
                    for j in range(len(data)):
                        # colors are in RGBA order
                        colors.append([
                            (data[j]&31)/31,        # red
                            ((data[j]>>5)&31)/31,   # green
                            ((data[j]>>10)&31)/31,  # blue
                            ((data[j]>>15)&1),      # alpha(always set?)
                            ])

                elif data_type == c.DATA_TYPE_UV:
                    # 8/16/32 bit uv coordinates, or
                    # 16 bit diffuse and lightmap coordinates
                    if storage_type == c.STORAGE_TYPE_UINT16_LMUV:
                        for j in range(0, len(data), 4):
                            uvs.append([
                                data[j]/c.UV_SCALE,
                                data[j+1]/c.UV_SCALE
                                ])
                            lm_uvs.append([
                                data[j+2]/c.LM_UV_SCALE,
                                data[j+3]/c.LM_UV_SCALE
                                ])

                    else:
                        for j in range(0, len(data), 2):
                            uvs.append([
                                data[j]/c.UV_SCALE,
                                data[j+1]/c.UV_SCALE
                                ])

            #generate the triangles
            tris = []
            start_v = len(self.verts)
            for j in range(strip_count):
                dont_draw = faces_drawn[j]
                face_dir = int(bool(face_dirs[j] == -1.0))
                for f in range(len(dont_draw)):
                    # determine if the face is not supposed to be drawn
                    if not dont_draw[f]:
                        v = start_v + f
                        # swap the vert order of every other face
                        if (f + face_dir) & 1:
                            tris.append((v,v,v, v+1,v+1,v+1, v+2,v+2,v+2))
                        else:
                            tris.append((v+1,v+1,v+1, v,v,v, v+2,v+2,v+2))

                #increment the start vert by the number of verts used
                start_v += len(dont_draw) + 2

            # add the imported data to the class
            self.all_tris.setdefault(idx_key, [])
            self.verts.extend(verts)
            self.norms.extend(norms)
            self.colors.extend(colors)
            self.uvs.extend(uvs)
            self.lm_uvs.extend(lm_uvs)
            self.all_tris[idx_key].extend(tris)

            self.bnd_rad = max(sqrt(bnd_rad_square), self.bnd_rad)

            # if nothing was imported, remove the triangles
            if len(self.all_tris.get(idx_key, [None])) == 0:
                del self.all_tris[idx_key]

    def import_obj(self, input_lines, source_file_hash=b'\x00'*16):
        # when importing an obj, we have to clear the existing data 
        self.clear()

        # default tex_name to use if one isnt given
        tex_name = c.DEFAULT_TEX_NAME
        lm_name  = c.DEFAULT_LM_NAME
        idx_key  = c.DEFAULT_INDEX_KEY

        bnd_rad_square = 0.0
        tris = self.all_tris[idx_key]

        # collect all all tris, verts, uvw, normals, and texture indexes
        for line in input_lines:
            line = line.strip()
            
            if not len(line):
                continue
            elif line[0] == 'g':
                # dont need to worry about groups
                continue
            elif line[0] == '#':
                # this is either a comment, or an extra piece of data
                line = line[1:].strip()
                if line.startswith('$lod_k'):
                    self.lod_ks[idx_key] = int(line[6:])
                elif line.startswith('$lm_name'):
                    lm_name = urllib.parse.unquote(line[9:].strip().upper())
                    idx_key = (tex_name, lm_name)
                elif line.startswith("lmvt"):
                    line = [v.strip() for v in line[5:].split(' ') if v]
                    u, v = float(line[0]), 1 - float(line[1])
                    self.lm_uvs.append([u, v])
                elif line.startswith("vc"):
                    line = [v.strip() for v in line[3:].split(' ') if v]
                    r, g, b, a = float(line[0]), float(line[1]), float(line[2]), float(line[3])
                    self.colors.append([
                        max(min(r, 1.0), 0.0),
                        max(min(g, 1.0), 0.0),
                        max(min(b, 1.0), 0.0),
                        max(min(a, 1.0), 0.0)
                        ])
            elif line[:6] == 'usemtl':
                tex_name = urllib.parse.unquote(line[6:].strip().upper())

                idx_key = (tex_name, lm_name)
                # make a new triangle block if one for
                # this material doesnt already exist
                if idx_key not in self.all_tris:
                    self.all_tris[idx_key] = []
                    self.lod_ks.setdefault(idx_key, c.DEFAULT_LOD_K)
                tris = self.all_tris[idx_key]
            elif line[0:2] == 'vt':
                line = [v.strip() for v in line[2:].split(' ') if v]
                u, v = float(line[0]), 1 - float(line[1])
                self.uvs.append([u, v])
            elif line[0:2] == 'vn':
                line = [v.strip() for v in line[2:].split(' ') if v]
                # x-axis is reversed
                xn, yn, zn = -float(line[0]), float(line[1]), float(line[2])
                mag = sqrt(xn**2 + yn**2 + zn**2)
                if mag == 0:
                    mag = 1.0

                self.norms.append([
                    max(min(xn/mag, 1.0), -1.0),
                    max(min(yn/mag, 1.0), -1.0),
                    max(min(zn/mag, 1.0), -1.0)
                    ])
            elif line[0] == 'v':
                line = [v.strip() for v in line[1:].split(' ') if v]
                # x-axis is reversed
                x, y, z = -float(line[0]), float(line[1]), float(line[2])
                self.verts.append([x, y, z])
                bnd_rad_square = max(x**2 + y**2 + z**2, bnd_rad_square)
            elif line[0] == 'f':
                line = [v.strip() for v in line[1:].split(' ') if v]
                tris.append((tuple(int(i)-1 for i in line[0].split('/')),
                             tuple(int(i)-1 for i in line[1].split('/')),
                             tuple(int(i)-1 for i in line[2].split('/'))))

        self.bnd_rad = sqrt(bnd_rad_square)
        self.source_file_hash = source_file_hash

        # if no untextured triangles exist, remove the entries
        if len(self.all_tris.get(c.DEFAULT_INDEX_KEY, [None])) == 0:
            del self.all_tris[c.DEFAULT_INDEX_KEY]

    def export_g3d(self, output_buffer, headerless=False):
        vert_data = self.stripifier.vert_data
        tri_count = sum(self.stripifier.tri_counts.values())

        written_vert_count, total_geom_count = 0, 0
        subobj_buffers = []

        # loop over each subobject
        for idx_key, strips in self.stripifier.all_strips.items():
            strips = self.stripifier.all_strips[idx_key]
            tex_name, lm_name = idx_key
            
            if len(strips) == 0:
                continue

            # create a buffer to hold this sub object data
            subobj_buffers.append(util.FixedBytearrayBuffer())
            subobj_buffer = subobj_buffers[-1]
            geom_buffers = []
            total_geom_count += 1

            linked, lod_k = False, self.lod_ks.get(idx_key, 0)

            face_dirs    = self.stripifier.all_face_dirs[idx_key]
            dont_draws   = self.all_dont_draws[idx_key]
            vert_maxs    = self.all_vert_maxs[idx_key]
            uv_maxs      = self.all_uv_maxs[idx_key]
            uv_shifts    = self.all_uv_shifts[idx_key]
            lm_uv_shifts = self.all_lm_uv_shifts[idx_key]

            # write the model data
            for geom_num in range(len(strips)):
                strip = strips[geom_num]
                if len(strip) < 3:
                    continue

                # create a buffer to hold this geom data
                geom_buffers.append(util.FixedBytearrayBuffer())
                geom_buffer = geom_buffers[-1]

                d_draws  = dont_draws[geom_num]
                vert_max = vert_maxs[geom_num]
                uv_max   = uv_maxs[geom_num]
                uv_shift = uv_shifts[geom_num]
                lm_uv_shift = lm_uv_shifts[geom_num]

                #if the face is reversed, set that
                face_dir = 1.0 if face_dirs[geom_num] else -1.0

                # write the geometry header
                # this consists of the triangle strip length, an unknown
                # 4 bytes, the face direction, and an unknown float
                # TODO: figure out the purpose of the unknowns
                d_type, s_type = c.DATA_TYPE_GEOM, c.STORAGE_TYPE_FLOAT32
                stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
                pack_g3d_stream_header(geom_buffer, d_type, s_type, c.STREAM_FLAGS_DEFAULT, 1)
                geom_buffer.write(stream_data_packer(
                    len(strip), c.UNKNOWN_GEOM_DATA, face_dir, 1.0
                    ))

                # write the position data
                d_type = c.DATA_TYPE_POS
                s_type = c.STORAGE_TYPE_SINT32_XYZ
                if vert_max < 1:
                    s_type = c.STORAGE_TYPE_SINT8_XYZ
                elif vert_max < 256:
                    s_type = c.STORAGE_TYPE_SINT16_XYZ

                pack_g3d_stream_header(geom_buffer, d_type, s_type, c.STREAM_FLAGS_DEFAULT, len(strip)+1)
                stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
                for i in strip:
                    v = self.verts[vert_data[i][0]]
                    geom_buffer.write(stream_data_packer(
                        int(round(c.POS_SCALE * v[0])),
                        int(round(c.POS_SCALE * v[1])),
                        int(round(c.POS_SCALE * v[2]))
                        ))
                    written_vert_count += 1

                geom_buffer.write(stream_data_packer(0, 0, 0))  # extra padding vert
                geom_buffer.write(b'\x00'*util.calculate_padding(len(geom_buffer), 4))

                # write the normals data
                if self.norms:
                    d_type = c.DATA_TYPE_NORM
                    s_type = c.STORAGE_TYPE_UINT16_BITPACKED

                    pack_g3d_stream_header(geom_buffer,
                        d_type, s_type, c.STREAM_FLAGS_DEFAULT, len(strip)
                        )
                    stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
                    for i in range(len(strip)):
                        n = self.norms[vert_data[strip[i]][2]]
                        geom_buffer.write(stream_data_packer(
                             int(round(15 * (n[0] + 1.0)))      |
                            (int(round(15 * (n[1] + 1.0)))<<5)  |
                            (int(round(15 * (n[2] + 1.0)))<<10) |
                            0x8000*d_draws[i]
                            ))

                    geom_buffer.write(b'\x00'*util.calculate_padding(len(geom_buffer), 4))

                # write the color data
                if self.colors:
                    d_type = c.DATA_TYPE_COLOR
                    s_type = c.STORAGE_TYPE_UINT16_BITPACKED
                    pack_g3d_stream_header(geom_buffer,
                        d_type, s_type, c.STREAM_FLAGS_DEFAULT, len(strip)
                        )
                    stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
                    for i in strip:
                        color = self.colors[vert_data[i][1]]
                        geom_buffer.write(stream_data_packer(
                             int(round(31 * color[0]))      |
                            (int(round(31 * color[1]))<<5)  |
                            (int(round(31 * color[2]))<<10) |
                            (int(round(color[3]))<<15)
                            ))

                    geom_buffer.write(b'\x00'*util.calculate_padding(len(geom_buffer), 4))

                # write the uv data
                d_type = c.DATA_TYPE_UV
                s_type = c.STORAGE_TYPE_UINT32_UV
                if self.lm_uvs:
                    s_type = c.STORAGE_TYPE_UINT16_LMUV
                elif uv_max < 2:
                    s_type = c.STORAGE_TYPE_UINT8_UV
                elif uv_max < 512:
                    s_type = c.STORAGE_TYPE_UINT16_UV

                pack_g3d_stream_header(geom_buffer,
                    d_type, s_type, c.STREAM_FLAGS_UV_DEFAULT, len(strip)
                    )
                stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
                if self.lm_uvs:
                    # lightmap verts combine 2 uv sets in one
                    for i in strip:
                        uv_index = vert_data[i][1]
                        uv    = self.uvs[uv_index]
                        lm_uv = self.lm_uvs[uv_index]
                        geom_buffer.write(stream_data_packer(
                            max(0, min(0xFFFF, int(round(c.UV_SCALE * (uv[0] + uv_shift[0]))))),
                            max(0, min(0xFFFF, int(round(c.UV_SCALE * (uv[1] + uv_shift[1]))))),
                            max(0, min(0xFFFF, int(round(c.LM_UV_SCALE * (lm_uv[0] + lm_uv_shift[0]))))),
                            max(0, min(0xFFFF, int(round(c.LM_UV_SCALE * (lm_uv[1] + lm_uv_shift[1])))))
                            ))
                else:
                    for i in strip:
                        uv = self.uvs[vert_data[i][1]]
                        geom_buffer.write(stream_data_packer(
                            int(round(c.UV_SCALE * (uv[0] + uv_shift[0]))),
                            int(round(c.UV_SCALE * (uv[1] + uv_shift[1])))
                            ))

                geom_buffer.write(b'\x00'*util.calculate_padding(len(geom_buffer), 4))

                #write the link
                link_type = c.STORAGE_TYPE_STRIP_N_END if linked else c.STORAGE_TYPE_STRIP_0_END
                pack_g3d_stream_header(geom_buffer, c.DATA_TYPE_GEOM, link_type)
                linked = True

            # write a temp header and then the data
            subobj_header_pos = subobj_buffer.tell()
            subobj_buffer.write(SUBOBJ_HEADER_STRUCT.pack(0, 0, b'', b''))

            # add pad bytes for the header that would normally
            # be present if this model was inside an objects file 
            subobj_start = subobj_buffer.tell()
            subobj_buffer.write(b'\x00' * 8)
            for geom_buffer in geom_buffers:
                subobj_buffer.write(geom_buffer)

            subobj_buffer.write(b'\x00'*util.calculate_padding(
                subobj_buffer.tell() - subobj_start, 16
                ))
            subobj_end = subobj_buffer.tell()

            # seek back and write the subobject header
            quadword_count = (subobj_end - subobj_start) // 16
            subobj_buffer.seek(subobj_header_pos)
            subobj_buffer.write(SUBOBJ_HEADER_STRUCT.pack(
                # NOTE: qword_count does not include the first quadword, as it is assumed
                quadword_count - 1, lod_k, tex_name.encode(), lm_name.encode()
                ))

        has_data = bool(sum(len(b) for b in subobj_buffers))
        header_data = (
            self.bnd_rad, written_vert_count, tri_count, total_geom_count,
            has_data * (
                c.G3D_FLAG_MESH    * bool(self.verts)  |
                c.G3D_FLAG_NORMALS * bool(self.norms)  |
                c.G3D_FLAG_COLORS  * bool(self.colors) |
                c.G3D_FLAG_LMAP    * bool(self.lm_uvs)
                ),
            self.source_file_hash
            )

        if not headerless:
            #write the g3d header
            output_buffer.write(OBJECT_HEADER_STRUCT.pack(*header_data))

        # write the data and pad it to 16 bytes
        for subobj_buffer in subobj_buffers:
            output_buffer.write(subobj_buffer)

        return header_data

    def export_obj(self, output_filepath, texture_assets={}, swap_lightmap_and_diffuse=False):
        obj_dirname = os.path.dirname(output_filepath)
        mtl_filename = urllib.parse.quote(os.path.basename(output_filepath))

        mtl_filename = "mtl/%s.mtl" % os.path.splitext(mtl_filename)[0]
        mtl_filepath = os.path.join(obj_dirname, mtl_filename)

        uv_template   = "vt %.7f %.7f"
        lmuv_template = "#lmvt %.7f %.7f"

        mtl_str = '\n'.join((
            '# Gauntlet Dark Legacy material library',
            '#     Extracted by Moses',
            ))

        obj_str = '\n'.join((
            '# Gauntlet Dark Legacy 3d model',
            '#     Extracted by Moses',
            'mtllib %s' % mtl_filename
            ))
        if swap_lightmap_and_diffuse and self.lm_uvs and self.uvs:
            obj_str += '\n#lightmap_diffuse_swapped'
            uv_template, lmuv_template = lmuv_template, uv_template

        obj_str += '\n\n'
        obj_str += '\n'.join((
            'v %.7f %.7f %.7f' % (-v[0], v[1], v[2]) for v in self.verts
            ))
        obj_str += '\n'
        obj_str += '\n'.join((
            'vn %.7f %.7f %.7f' % (-n[0], n[1], n[2]) for n in self.norms
            ))
        obj_str += '\n'
        obj_str += '\n'.join((
            uv_template % (uv[0], 1 - uv[1]) for uv in self.uvs
            ))
        obj_str += '\n'
        obj_str += '\n'.join((
            lmuv_template % (lm_uv[0], 1 - lm_uv[1]) for lm_uv in self.lm_uvs
            ))
        obj_str += '\n'
        obj_str += '\n'.join((
            '#vc %.7f %.7f %.7f %.7f' % tuple(color[:4]) for color in self.colors
            ))
        obj_str += '\n'

        seen_bitmaps = set()
        for idx_key in sorted(self.all_tris):
            if not self.all_tris[idx_key]:
                continue

            for bitmap_name in idx_key:
                bitmap_name = bitmap_name.upper()
                bitmap_filepath = texture_assets.get(bitmap_name)
                if bitmap_name in seen_bitmaps:
                    continue
                elif not bitmap_filepath:
                    # TODO: write a shared function to handle this naming
                    for suffix in ("00", ".00001", ".00002"):
                        temp_name = bitmap_name + suffix
                        if temp_name in texture_assets:
                            bitmap_filepath = texture_assets[temp_name]
                            break

                if not bitmap_filepath:
                    continue

                mtl_str += '\n'.join((
                    '',
                    'newmtl %s' % urllib.parse.quote(bitmap_name),
                    'map_Kd %s' % bitmap_filepath.replace("\\", "/"),
                    ))
                seen_bitmaps.add(bitmap_name)

        # collect all all tris, verts, uvw, normals, and texture indexes
        i = 0
        for idx_key in sorted(self.all_tris):
            tris = self.all_tris[idx_key]
            if not tris:
                continue

            tex_name, lm_name = idx_key
            lod_k = self.lod_ks.get(idx_key, c.DEFAULT_LOD_K)
            if swap_lightmap_and_diffuse:
                tex_name, lm_name = lm_name, tex_name

            obj_str += '\n'.join((
                '',
                '#$lm_name %s' % urllib.parse.quote(lm_name),
                '#$lod_k %s' % lod_k,
                'usemtl %s' % urllib.parse.quote(tex_name),
                'g %s' % i
                ))
            obj_str += '\n'
            i += 1

            # write the triangles
            for tri in tris:
                tri = tuple(i+1 for i in tri)  # obj indices are ones based
                if len(tri) == 3:
                    obj_str += 'f %s %s %s\n' % tri
                elif len(tri) == 6:
                    obj_str += 'f %s/%s %s/%s %s/%s\n' % tri
                elif len(tri) == 9:
                    obj_str += 'f %s/%s/%s %s/%s/%s %s/%s/%s\n' % tri
                else:
                    raise ValueError("Expected either 3, 6, or 9 items in tri, not %s" % len(tri))

        mtl_bytes = mtl_str.encode()
        obj_bytes = obj_str.encode()

        os.makedirs(os.path.dirname(mtl_filepath), exist_ok=True)
        with open(mtl_filepath, 'wb+') as out_file:
            out_file.write(mtl_bytes)

        with open(output_filepath, 'wb+') as out_file:
            out_file.write(obj_bytes)

        digester = hashlib.md5(obj_bytes)
        self.source_file_hash = digester.digest()
