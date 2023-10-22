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


def import_vif_to_g3d(
        g3d_model, input_buffer, headerless=False, stream_len=-1, 
        subobj_count=1, tex_name="", lm_name=""
        ):

    if subobj_count > 1 and headerless:
        raise ValueError("Cannot import multiple headerless vif streams.")

    if stream_len < 0:
        stream_len = len(input_buffer) - input_buffer.tell()

    # slight speedup to cache these
    uint8_scale = 1/255
    pos_scale   = 1/c.POS_SCALE
    uv_scale    = 1/c.UV_SCALE
    lm_uv_scale = 1/c.LM_UV_SCALE

    for i in range(subobj_count):
        buffer_start = input_buffer.tell()
        buffer_end   = len(input_buffer)
        if not headerless:
            rawdata = input_buffer.read(SUBOBJ_HEADER_STRUCT.size)
            if len(rawdata) < SUBOBJ_HEADER_STRUCT.size:
                return

            qword_count, lod_k, tex_name, lm_name = SUBOBJ_HEADER_STRUCT.unpack(rawdata)
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


            if storage_type in (c.STORAGE_TYPE_NULL, c.STORAGE_TYPE_STRIP_N_END, c.STORAGE_TYPE_STRIP_0_END):
                # we're reading the padding at EOF, or this is a strip terminator
                pass
            elif storage_type == c.STORAGE_TYPE_FLOAT32:
                if data_type == c.DATA_TYPE_GEOM:
                    # triangle strip. only need the face direction from it
                    strip_count += 1
                    faces_drawn.append([])
                    face_dirs.append(data[2])
                elif data_type == c.DATA_TYPE_POS:
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

            elif data_type == c.DATA_TYPE_POS:
                # make sure to ignore the last vertex
                for j in range(0, len(data)-3, 3):
                    x, y, z = data[j]*pos_scale, data[j+1]*pos_scale, data[j+2]*pos_scale
                    verts.append([x, y, z])
                    bnd_rad_square = max(x**2 + y**2 + z**2, bnd_rad_square)

            elif data_type == c.DATA_TYPE_NORM:
                dont_draw = [n >= 0x8000 for n in data]
                norms.extend(map(NORM_1555_UNPACK_TABLE.__getitem__, data))

                # make sure the first 2 are removed since they
                # are always 1 and triangle strips are always
                # made of 2 more verts than there are triangles
                faces_drawn[-1].extend(dont_draw[2:])

            elif data_type == c.DATA_TYPE_COLOR:
                colors.extend(map(COLOR_1555_UNPACK_TABLE.__getitem__, data))

            elif data_type == c.DATA_TYPE_UV:
                # 8/16/32 bit uv coordinates, or
                # 16 bit diffuse and lightmap coordinates
                if storage_type == c.STORAGE_TYPE_UINT16_LMUV:
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

        #generate the triangles
        tris = []
        start_v = len(g3d_model.verts)
        for j in range(strip_count):
            dont_draw = faces_drawn[j]
            face_dir = int(bool(face_dirs[j] == -1.0))
            if not dont_draw:
                # empty strip. skip
                continue

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
        g3d_model.tri_lists.setdefault(idx_key, [])
        g3d_model.verts.extend(verts)
        g3d_model.norms.extend(norms)
        g3d_model.colors.extend(colors)
        g3d_model.uvs.extend(uvs)
        g3d_model.lm_uvs.extend(lm_uvs)
        g3d_model.tri_lists[idx_key].extend(tris)

        g3d_model.bnd_rad = max(sqrt(bnd_rad_square), g3d_model.bnd_rad)

        # if nothing was imported, remove the triangles
        if len(g3d_model.tri_lists.get(idx_key, [None])) == 0:
            del g3d_model.tri_lists[idx_key]


def export_g3d_to_vif(g3d_model, output_buffer, headerless=False):
    vert_data = g3d_model.stripifier.vert_data
    tri_count = sum(g3d_model.stripifier.tri_counts.values())

    written_vert_count, total_geom_count = 0, 0
    subobj_buffers = []

    # loop over each subobject
    for idx_key, strips in g3d_model.stripifier.all_strips.items():
        strips = g3d_model.stripifier.all_strips[idx_key]
        tex_name, lm_name = idx_key
        
        if len(strips) == 0:
            continue

        # create a buffer to hold this sub object data
        subobj_buffers.append(util.FixedBytearrayBuffer())
        subobj_buffer = subobj_buffers[-1]
        geom_buffers = []
        total_geom_count += 1

        linked, lod_k = False, g3d_model.lod_ks.get(idx_key, 0)

        face_dirs    = g3d_model.stripifier.all_face_dirs[idx_key]
        dont_draws   = g3d_model.all_dont_draws[idx_key]
        vert_maxs    = g3d_model.all_vert_maxs[idx_key]
        uv_maxs      = g3d_model.all_uv_maxs[idx_key]
        uv_shifts    = g3d_model.all_uv_shifts[idx_key]
        lm_uv_shifts = g3d_model.all_lm_uv_shifts[idx_key]

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
                len(strip), c.UNKNOWN_GEOM_DATA, face_dir,
                -1.0  # not sure why -1.0, but it works for ps2?
                #       without it, some triangles dont render..
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
                v = g3d_model.verts[vert_data[i][0]]
                geom_buffer.write(stream_data_packer(
                    int(round(c.POS_SCALE * v[0])),
                    int(round(c.POS_SCALE * v[1])),
                    int(round(c.POS_SCALE * v[2]))
                    ))
                written_vert_count += 1

            geom_buffer.write(stream_data_packer(0, 0, 0))  # extra padding vert
            geom_buffer.write(b'\x00'*util.calculate_padding(len(geom_buffer), 4))

            # write the normals data
            if g3d_model.norms:
                d_type = c.DATA_TYPE_NORM
                s_type = c.STORAGE_TYPE_UINT16_BITPACKED

                pack_g3d_stream_header(geom_buffer,
                    d_type, s_type, c.STREAM_FLAGS_DEFAULT, len(strip)
                    )
                stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
                for i in range(len(strip)):
                    n = g3d_model.norms[vert_data[strip[i]][2]]
                    geom_buffer.write(stream_data_packer(
                         int(round(15 * (n[0] + 1.0)))      |
                        (int(round(15 * (n[1] + 1.0)))<<5)  |
                        (int(round(15 * (n[2] + 1.0)))<<10) |
                        0x8000*d_draws[i]
                        ))

                geom_buffer.write(b'\x00'*util.calculate_padding(len(geom_buffer), 4))

            # write the color data
            if g3d_model.colors:
                d_type = c.DATA_TYPE_COLOR
                s_type = c.STORAGE_TYPE_UINT16_BITPACKED
                pack_g3d_stream_header(geom_buffer,
                    d_type, s_type, c.STREAM_FLAGS_DEFAULT, len(strip)
                    )
                stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
                for i in strip:
                    color = g3d_model.colors[vert_data[i][1]]
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
            if g3d_model.lm_uvs:
                s_type = c.STORAGE_TYPE_UINT16_LMUV
            elif uv_max < 2:
                s_type = c.STORAGE_TYPE_UINT8_UV
            elif uv_max < 512:
                s_type = c.STORAGE_TYPE_UINT16_UV

            pack_g3d_stream_header(geom_buffer,
                d_type, s_type, c.STREAM_FLAGS_UV_DEFAULT, len(strip)
                )
            stream_data_packer = STREAM_DATA_STRUCTS[(d_type, s_type)].pack
            if g3d_model.lm_uvs:
                # lightmap verts combine 2 uv sets in one
                for i in strip:
                    uv_index = vert_data[i][1]
                    uv    = g3d_model.uvs[uv_index]
                    lm_uv = g3d_model.lm_uvs[uv_index]
                    geom_buffer.write(stream_data_packer(
                        max(0, min(0xFFFF, int(round(c.UV_SCALE * (uv[0] + uv_shift[0]))))),
                        max(0, min(0xFFFF, int(round(c.UV_SCALE * (uv[1] + uv_shift[1]))))),
                        max(0, min(0xFFFF, int(round(c.LM_UV_SCALE * (lm_uv[0] + lm_uv_shift[0]))))),
                        max(0, min(0xFFFF, int(round(c.LM_UV_SCALE * (lm_uv[1] + lm_uv_shift[1])))))
                        ))
            else:
                for i in strip:
                    uv = g3d_model.uvs[vert_data[i][1]]
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
        g3d_model.bnd_rad, written_vert_count, tri_count, total_geom_count,
        has_data * (
            c.G3D_FLAG_MESH    * bool(g3d_model.verts)  |
            c.G3D_FLAG_NORMALS * bool(g3d_model.norms)  |
            c.G3D_FLAG_COLORS  * bool(g3d_model.colors) |
            c.G3D_FLAG_LMAP    * bool(g3d_model.lm_uvs)
            ),
        g3d_model.source_file_hash
        )

    if not headerless:
        #write the g3d header
        output_buffer.write(OBJECT_HEADER_STRUCT.pack(*header_data))

    # write the data and pad it to 16 bytes
    for subobj_buffer in subobj_buffers:
        output_buffer.write(subobj_buffer)

    return header_data
