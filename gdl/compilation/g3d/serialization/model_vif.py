import struct

from array import array
from sys import byteorder

from math import sqrt

from . import constants as c
from .. import util

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

COLL_SCALE  = 0x40
POS_SCALE   = 0x80
UV_SCALE    = 0x80
LM_UV_SCALE = 0x8000

DEFAULT_TEX_NAME  = "__unnamed_0"
DEFAULT_LM_NAME   = "__unnamed_0"
DEFAULT_INDEX_KEY = (DEFAULT_TEX_NAME, DEFAULT_LM_NAME)

STREAM_FLAGS_DEFAULT    = 0x80
STREAM_FLAGS_UV_DEFAULT = 0xC0

UNKNOWN_GEOM_DATA = b'\x00\x00\x00\x2D'

DATA_TYPE_GEOM  = 0x00
DATA_TYPE_POS   = 0x01
DATA_TYPE_NORM  = 0x02
DATA_TYPE_COLOR = 0x03
DATA_TYPE_UV    = 0x04

STORAGE_TYPE_NULL             = 0x00
STORAGE_TYPE_UNKNOWN          = 0x01
STORAGE_TYPE_STRIP_0_END      = 0x14
STORAGE_TYPE_STRIP_N_END      = 0x17
STORAGE_TYPE_UINT32_UV        = 0x64
STORAGE_TYPE_UINT16_UV        = 0x65
STORAGE_TYPE_UINT8_UV         = 0x66
STORAGE_TYPE_SINT32_XYZ       = 0x68
STORAGE_TYPE_SINT16_XYZ       = 0x69
STORAGE_TYPE_SINT8_XYZ        = 0x6A
STORAGE_TYPE_FLOAT32          = 0x6C
STORAGE_TYPE_UINT16_LMUV      = 0x6D
STORAGE_TYPE_UINT16_BITPACKED = 0x6F


STREAM_DATA_STRUCTS = {
    (DATA_TYPE_GEOM,  STORAGE_TYPE_NULL)             : struct.Struct('<'),
    (DATA_TYPE_GEOM,  STORAGE_TYPE_STRIP_0_END)      : struct.Struct('<'),
    (DATA_TYPE_GEOM,  STORAGE_TYPE_STRIP_N_END)      : struct.Struct('<'),
    (DATA_TYPE_GEOM,  STORAGE_TYPE_FLOAT32)          : struct.Struct('<I4sff'),
    (DATA_TYPE_POS,   STORAGE_TYPE_FLOAT32)          : struct.Struct('<ffff'),
    (DATA_TYPE_POS,   STORAGE_TYPE_SINT32_XYZ)       : struct.Struct('<iii'),
    (DATA_TYPE_POS,   STORAGE_TYPE_SINT16_XYZ)       : struct.Struct('<hhh'),
    (DATA_TYPE_POS,   STORAGE_TYPE_SINT8_XYZ)        : struct.Struct('<bbb'),
    (DATA_TYPE_NORM,  STORAGE_TYPE_UINT16_BITPACKED) : struct.Struct('<H'),
    (DATA_TYPE_COLOR, STORAGE_TYPE_UINT16_BITPACKED) : struct.Struct('<H'),
    (DATA_TYPE_UV,    STORAGE_TYPE_UINT32_UV)        : struct.Struct('<II'),
    (DATA_TYPE_UV,    STORAGE_TYPE_UINT16_UV)        : struct.Struct('<HH'),
    (DATA_TYPE_UV,    STORAGE_TYPE_UINT8_UV)         : struct.Struct('<BB'),
    (DATA_TYPE_UV,    STORAGE_TYPE_UINT16_LMUV)      : struct.Struct('<HHHH'),
    (DATA_TYPE_UV,    STORAGE_TYPE_UNKNOWN)          : struct.Struct('<'),
    }

def unpack_norm_1555(norm_1555):
    xn  = (norm_1555&31)/15 - 1
    yn  = ((norm_1555>>5)&31)/15 - 1
    zn  = ((norm_1555>>10)&31)/15 - 1
    inv_mag = 1/(sqrt(xn*xn + yn*yn + zn*zn) + 0.0000001)
    return (xn*inv_mag, yn*inv_mag, zn*inv_mag)

def unpack_color_1555(color_1555):
    return (
        (color_1555&31)/31,        # red
        ((color_1555>>5)&31)/31,   # green
        ((color_1555>>10)&31)/31,  # blue
        ((color_1555>>15)&1)*1.0,  # alpha(always set?)
        )

NORM_1555_UNPACK_TABLE = tuple(map(unpack_norm_1555, range(0x8000)))
NORM_1555_UNPACK_TABLE += NORM_1555_UNPACK_TABLE  # double length for full 16bit range
COLOR_1555_UNPACK_TABLE = tuple(map(unpack_color_1555, range(0x10000)))


def pack_g3d_stream_header(buffer, d_type, s_type, flags=0, count=0):
    buffer.write(STREAM_HEADER_STRUCT.pack(d_type, flags, count, s_type))


def import_vif_to_g3d(input_buffer, start_vert=0, stream_len=-1):
    if stream_len < 0:
        stream_len = len(input_buffer) - input_buffer.tell()

    # slight speedup to cache these
    uint8_scale = 1/255
    pos_scale   = 1/POS_SCALE
    uv_scale    = 1/UV_SCALE
    lm_uv_scale = 1/LM_UV_SCALE

    buffer_start = input_buffer.tell()
    buffer_end   = len(input_buffer)

    g3d_end = min(buffer_end, stream_len + buffer_start)

    bnd_rad_square = 0.0
    strip_count = 0

    verts       = []
    norms       = []
    colors      = []
    uvs         = []
    lm_uvs      = []
    faces_drawn = []
    face_dirs   = []

    # scan over all the data in the stream
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
            for j in range(0, len(rawdata), stream_stride):
                data.extend(stream_struct.unpack(rawdata[j: j + stream_stride]))


        if storage_type in (STORAGE_TYPE_NULL, STORAGE_TYPE_STRIP_N_END, STORAGE_TYPE_STRIP_0_END):
            # we're reading the padding at EOF, or this is a strip terminator
            pass
        elif storage_type == STORAGE_TYPE_FLOAT32:
            if data_type == DATA_TYPE_GEOM:
                # triangle strip. only need the face direction from it
                strip_count += 1
                faces_drawn.append([])
                face_dirs.append(data[2])
            elif data_type == DATA_TYPE_POS:
                # append a single triangle
                faces_drawn[-1].append(0)
                face_dirs[-1] = -1.0

                # NOTE: we're ignoring the count here because it's not possible to
                #       store more than a single triangle here. the count MUST be 12

                # positions
                for j in range(0, 12, 4):
                    scale = 1/data[j+3]
                    x, y, z = data[j]*scale, data[j+1]*scale, data[j+2]*scale
                    verts.append([x, y, z])
                    bnd_rad_square = max(x**2 + y**2 + z**2, bnd_rad_square)

                # normals
                for j in range(12, 24, 4):
                    scale = data[j+3]
                    norms.append([data[j]*scale, data[j+1]*scale, data[j+2]*scale])

                # colors
                for j in range(24, 36, 4):
                    colors.append([
                        data[j]*uint8_scale,    # r
                        data[j+1]*uint8_scale,  # g
                        data[j+2]*uint8_scale,  # b
                        data[j+3]*uint8_scale   # a
                        ])

                # uv coords
                for j in range(36, 48, 4):
                    u, v, w = data[j], data[j+1], data[j+2]
                    uvs.append([u, v, w])

        elif data_type == DATA_TYPE_POS:
            # make sure to ignore the last vertex
            for j in range(0, len(data)-3, 3):
                x, y, z = data[j]*pos_scale, data[j+1]*pos_scale, data[j+2]*pos_scale
                verts.append([x, y, z])
                bnd_rad_square = max(x**2 + y**2 + z**2, bnd_rad_square)

        elif data_type == DATA_TYPE_NORM:
            dont_draw = [n >= 0x8000 for n in data]
            norms.extend(map(NORM_1555_UNPACK_TABLE.__getitem__, data))

            # make sure the first 2 are removed since they
            # are always 1 and triangle strips are always
            # made of 2 more verts than there are triangles
            faces_drawn[-1].extend(dont_draw[2:])

        elif data_type == DATA_TYPE_COLOR:
            colors.extend(map(COLOR_1555_UNPACK_TABLE.__getitem__, data))

        elif data_type == DATA_TYPE_UV:
            # 8/16/32 bit uv coordinates, or
            # 16 bit diffuse and lightmap coordinates
            if storage_type == STORAGE_TYPE_UINT16_LMUV:
                uvs.extend(
                    [data[j]*uv_scale, data[j+1]*uv_scale]
                    for j in range(0, len(data), 4)
                    )
                lm_uvs.extend(
                    [data[j]*lm_uv_scale, data[j+1]*lm_uv_scale]
                    for j in range(2, len(data)+2, 4)
                    )

            else:
                uvs.extend(
                    [data[j]*uv_scale, data[j+1]*uv_scale]
                    for j in range(0, len(data), 2)
                    )

    # generate the triangles
    tris = []
    for i in range(strip_count):
        dont_draw_list = faces_drawn[i]
        face_dir = int(bool(face_dirs[i] == -1.0))
        if not dont_draw_list:
            # empty strip. skip
            continue

        for f, dont_draw in enumerate(dont_draw_list):
            # determine if the face is not supposed to be drawn
            if not dont_draw:
                v = start_vert + f
                # swap the vert order of every other face
                if (f + face_dir) & 1:
                    tris.append((v,v,v, v+1,v+1,v+1, v+2,v+2,v+2))
                else:
                    tris.append((v+1,v+1,v+1, v,v,v, v+2,v+2,v+2))

        #increment the start vert by the number of verts used
        start_vert += len(dont_draw_list) + 2

    # return the parsed data
    return dict(
        tris = tris,
        verts = verts,
        norms = norms,
        colors = colors,
        uvs = uvs,
        lm_uvs = lm_uvs,
        bounding_radius = max(sqrt(bnd_rad_square))
        )


def export_g3d_to_vif(g3d_model, idx_key):
    # create a buffer to write the serialized data to
    vif_buffer = util.FixedBytearrayBuffer()

    # grab everything we need from the G3DModel and assign locally
    vert_data    = g3d_model.stripifier.vert_data
    strips       = g3d_model.stripifier.all_strips[idx_key]
    face_dirs    = g3d_model.stripifier.all_face_dirs[idx_key]
    dont_draws   = g3d_model.all_dont_draws[idx_key]
    vert_maxs    = g3d_model.all_vert_maxs[idx_key]
    uv_maxs      = g3d_model.all_uv_maxs[idx_key]
    uv_shifts    = g3d_model.all_uv_shifts[idx_key]
    lm_uv_shifts = g3d_model.all_lm_uv_shifts[idx_key]
    verts        = g3d_model.verts
    norms        = g3d_model.norms
    colors       = g3d_model.colors
    lm_uvs       = g3d_model.lm_uvs
    uvs          = g3d_model.vs

    written_vert_count = 0
    written_tri_count  = 0
    linked             = False

    # write the model data
    for geom_i, strip in enumerate(strips):
        if len(strip) < 3:
            continue

        dont_draw              =   dont_draws[geom_i]
        u_shift,    v_shift    =    uv_shifts[geom_i][0],    uv_shifts[geom_i][1]
        lm_u_shift, lm_v_shift = lm_uv_shifts[geom_i][0], lm_uv_shifts[geom_i][1]

        # if the face is reversed, set that
        face_dir = 1.0 if face_dirs[geom_i] else -1.0

        # dont_draw has a bool for each face specifying whether or to draw it.
        # get triangle count by subtracting non-drawn from the strip length.
        written_tri_count += len(dont_draw) - sum(dont_draw)

        # write the geometry header
        # this consists of the triangle strip length, an unknown
        # 4 bytes, the face direction, and an unknown float
        # TODO: figure out the purpose of the unknowns
        d_type, s_type = DATA_TYPE_GEOM, STORAGE_TYPE_FLOAT32
        stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
        pack_g3d_stream_header(vif_buffer, d_type, s_type, STREAM_FLAGS_DEFAULT, 1)
        vif_buffer.write(stream_data_packer(
            len(strip), UNKNOWN_GEOM_DATA, face_dir,
            -1.0  # not sure why -1.0, but it works for ps2?
            #       without it, some triangles dont render..
            ))

        ##############################################################
        # write the position data
        ##############################################################
        d_type = DATA_TYPE_POS
        s_type = (
            STORAGE_TYPE_SINT8_XYZ   if vert_maxs[geom_i] < 1   else
            STORAGE_TYPE_SINT16_XYZ  if vert_maxs[geom_i] < 256 else
            STORAGE_TYPE_SINT32_XYZ
            )

        pack_g3d_stream_header(vif_buffer, d_type, s_type, STREAM_FLAGS_DEFAULT, len(strip)+1)
        stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
        for i in strip:
            v = verts[vert_data[i][0]]
            vif_buffer.write(stream_data_packer(
                int(round(POS_SCALE * v[0])),
                int(round(POS_SCALE * v[1])),
                int(round(POS_SCALE * v[2]))
                ))
            written_vert_count += 1

        vif_buffer.write(stream_data_packer(0, 0, 0))  # extra padding vert
        vif_buffer.write(b'\x00'*util.calculate_padding(len(vif_buffer), 4))

        ##############################################################
        # write the normals data
        ##############################################################
        if norms:
            d_type = DATA_TYPE_NORM
            s_type = STORAGE_TYPE_UINT16_BITPACKED

            pack_g3d_stream_header(vif_buffer,
                d_type, s_type, STREAM_FLAGS_DEFAULT, len(strip)
                )
            stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
            for i in range(len(strip)):
                n = norms[vert_data[strip[i]][2]]
                vif_buffer.write(stream_data_packer(
                     int(round(15 * (n[0] + 1.0)))      |
                    (int(round(15 * (n[1] + 1.0)))<<5)  |
                    (int(round(15 * (n[2] + 1.0)))<<10) |
                    0x8000*dont_draw[i]
                    ))

            vif_buffer.write(b'\x00'*util.calculate_padding(len(vif_buffer), 4))

        ##############################################################
        # write the color data
        ##############################################################
        if colors:
            d_type = DATA_TYPE_COLOR
            s_type = STORAGE_TYPE_UINT16_BITPACKED
            pack_g3d_stream_header(vif_buffer,
                d_type, s_type, STREAM_FLAGS_DEFAULT, len(strip)
                )
            stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
            for i in strip:
                color = colors[vert_data[i][1]]
                vif_buffer.write(stream_data_packer(
                     int(round(31 * color[0]))      |
                    (int(round(31 * color[1]))<<5)  |
                    (int(round(31 * color[2]))<<10) |
                    (int(round(color[3]))<<15)
                    ))

            vif_buffer.write(b'\x00'*util.calculate_padding(len(vif_buffer), 4))

        ##############################################################
        # write the uv data
        ##############################################################
        d_type = DATA_TYPE_UV
        s_type = (
            STORAGE_TYPE_UINT16_LMUV if lm_uvs       else
            STORAGE_TYPE_UINT8_UV    if uv_maxs[geom_i] < 2   else
            STORAGE_TYPE_UINT16_UV   if uv_maxs[geom_i] < 512 else
            STORAGE_TYPE_UINT32_UV
            )

        pack_g3d_stream_header(vif_buffer,
            d_type, s_type, STREAM_FLAGS_UV_DEFAULT, len(strip)
            )
        stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
        if lm_uvs:
            # lightmap verts combine 2 uv sets in one
            for i in strip:
                uv_index = vert_data[i][1]
                uv       = uvs[uv_index]
                lm_uv    = lm_uvs[uv_index]

                u    = int(round(UV_SCALE    * (uv[0]    +    u_shift)))
                v    = int(round(UV_SCALE    * (uv[1]    +    v_shift)))
                lm_u = int(round(LM_UV_SCALE * (lm_uv[0] + lm_u_shift)))
                lm_v = int(round(LM_UV_SCALE * (lm_uv[1] + lm_v_shift)))
                vif_buffer.write(stream_data_packer(
                    0xFFFF if    u > 0xFFFF else 0 if    u < 0 else    u,
                    0xFFFF if    v > 0xFFFF else 0 if    v < 0 else    v,
                    0xFFFF if lm_u > 0xFFFF else 0 if lm_u < 0 else lm_u,
                    0xFFFF if lm_v > 0xFFFF else 0 if lm_v < 0 else lm_v,
                    ))
        else:
            for i in strip:
                uv = uvs[vert_data[i][1]]
                vif_buffer.write(stream_data_packer(
                    int(round(UV_SCALE * (uv[0] + u_shift))),
                    int(round(UV_SCALE * (uv[1] + v_shift)))
                    ))

        ##############################################################
        # pad and write the strip link header
        ##############################################################
        vif_buffer.write(b'\x00'*util.calculate_padding(len(vif_buffer), 4))

        pack_g3d_stream_header(
            vif_buffer, DATA_TYPE_GEOM,
            STORAGE_TYPE_STRIP_N_END if linked else STORAGE_TYPE_STRIP_0_END
            )
        linked = True

    return dict(
        vif_rawdata = bytes(vif_buffer),
        vert_count  = written_vert_count,
        tri_count   = written_tri_count,
        lod_k       = g3d_model.lod_ks.get(idx_key, 0),
        tex_name    = idx_key[0].upper(),
        lm_name     = idx_key[1].upper(),
        )
