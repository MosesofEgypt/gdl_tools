import array
import math
import struct

from sys import byteorder
from . import constants as c
from . import vector_util


COMP_POS_SCALE   = 256
COMP_UV_SCALE    = 1024


def import_raw_to_g3d(model_cache, start_vert=0):
    # slight speedup to cache these
    pos_scale   = 1/COMP_POS_SCALE
    uv_scale    = 1/COMP_UV_SCALE
    shade_scale = 1/254

    bnd_rad_square  = 0.0
    tri_lists       = {}
    verts, norms    = [], []
    uvs,   lm_uvs   = [], []
    colors          = []

    lm_name = model_cache.lightmap_name.upper()
    vdata_int16     = array.array("h", model_cache.verts_rawdata)
    tdata_int16     = array.array("H", model_cache.tris_rawdata)
    ndata_float     = array.array("f", model_cache.norms_rawdata)
    vdata_uint16    = array.array("H", model_cache.verts_rawdata)
    if byteorder == ">":
        vdata_int16.byteswap()
        vdata_uint16.byteswap()
        tdata_int16.byteswap()
        ndata_float.byteswap()

    if model_cache.is_compressed:
        i = 0
        expect_pos      = False
        new_uvs         = []
        new_colors      = []
        default_uv      = (0.0, 0.0)
        default_pos     = (0.0, 0.0, 0.0)
        stream_end      = len(vdata_int16) - 3
        pos             = default_pos

        while len(verts) < model_cache.vert_count:
            if i > stream_end:
                verts.extend([pos] * len(new_uvs))
                colors.extend(new_colors)
                uvs.extend(new_uvs)

                remainder = model_cache.vert_count-len(verts)
                if remainder:
                    print(f"Error: Vertex data truncated(expected {model_cache.vert_count} "
                          f"verts). Padding with null for {remainder} verts.")
                    verts.extend([(0, 0, 0)] * remainder)

                break

            if expect_pos:
                expect_pos  = False
                pos         = (
                    vdata_int16[i]  *pos_scale,
                    vdata_int16[i+1]*pos_scale,
                    vdata_int16[i+2]*pos_scale
                    )
            else:
                uv_index = vdata_uint16[i] & 0xFF
                shade    = max(0.0, min(
                    1.0, 0.5 + ((vdata_int16[i] >> 8)*shade_scale)
                    ))
                if uv_index == 0:
                    verts.extend([pos] * len(new_uvs))
                    colors.extend(new_colors)
                    uvs.extend(new_uvs)
                    new_uvs     = []
                    new_colors  = []
                    expect_pos  = True

                new_uvs.append((
                    vdata_int16[i+1]*uv_scale,
                    vdata_int16[i+2]*uv_scale
                    ))
                # instead of storing normals, there is an sint8 that
                # represents the smoothing gradient at this vertex.
                new_colors.append((shade, shade, shade, 1.0))

            i += 3

    else:
        vdata_float = array.array("f", model_cache.verts_rawdata)
        if byteorder == ">":
            vdata_float.byteswap()

        verts.extend([
            tuple(vdata_float[i:i+3])
            for i in range(0, len(vdata_float), 6)
            ])

        if model_cache.has_lmap:
            uvs.extend([
                (vdata_int16[i]*uv_scale, vdata_int16[i+1]*uv_scale)
                for i in range(6, len(vdata_int16), 12)
                ])
            lm_uvs.extend([
                (vdata_int16[i]*uv_scale,
                 vdata_int16[i+1]*uv_scale,
                 vdata_int16[i+2]*uv_scale)
                for i in range(8, len(vdata_int16), 12)
                ])
            norms.extend([
                vector_util.NORM_1555_UNPACK_TABLE[i]
                for i in vdata_int16[11::12]
                ])
        else:
            uvs.extend([
                (vdata_float[i], vdata_float[i+1], vdata_float[i+2])
                for i in range(3, len(vdata_float), 6)
                ])
            norms.extend([
                tuple(ndata_float[i:i+3])
                for i in range(0, len(ndata_float), 3)
                ])

    if verts:
        bnd_rad_square = max(x**2 + y**2 + z**2 for x, y, z in verts)

    flip            = False
    stripped        = True# False
    get_tri_list    = tri_lists.setdefault
    get_tex_name    = {
        i: n.upper() for i, n in
        enumerate(model_cache.texture_names)
        }.get
    # TODO: figure this out the rest of the way(determine purpose of bit14)
    for i, tri_tex_idx in enumerate(tdata_int16[3::4]):
        tex_idx         = tri_tex_idx & 0x3FFF
        strip_bits      = tri_tex_idx >> 14
        cont_strip      = strip_bits & 2
        #toggle_stripped = strip_bits & 1
        idx_key         = (get_tex_name(tex_idx, c.DEFAULT_TEX_NAME), lm_name)
        tris            = get_tri_list(idx_key, [])

        #if toggle_stripped:
        #    stripped = not stripped

        v0, v1, v2 = tdata_int16[i*4: i*4+3]
        if not stripped:
            flip = not flip

        v0 += start_vert
        v1 += start_vert
        v2 += start_vert

        tris.append(
            (v0, v2, v1) if flip else
            (v0, v1, v2)
            )

        if stripped:
            flip = (not flip) if cont_strip else False

    # return the parsed data
    return dict(
        tri_lists = tri_lists,
        verts = verts,
        norms = norms,
        colors = colors,
        uvs = uvs,
        lm_uvs = lm_uvs,
        bounding_radius = math.sqrt(bnd_rad_square)
        )


def export_g3d_to_raw(g3d_model):
    raise NotImplementedError()
