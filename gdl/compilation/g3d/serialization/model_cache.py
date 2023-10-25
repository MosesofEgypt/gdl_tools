import hashlib
import mmap
import os
import struct

from . import constants
from .cache import parse_cache_header, serialize_cache_header
from .. import util

# ensure they're all no more than 4 characters since we use them as the subtype
for ext in (constants.MODEL_CACHE_EXTENSION_NGC, constants.MODEL_CACHE_EXTENSION_PS2,
            constants.MODEL_CACHE_EXTENSION_XBOX, constants.MODEL_CACHE_EXTENSION_DC,
            constants.MODEL_CACHE_EXTENSION_ARC):
    assert len(ext) <= 4

MODEL_CACHE_VER  = 0x0001

# common flags
MODEL_CACHE_FLAG_MESH    = 1 << 0
MODEL_CACHE_FLAG_NORMALS = 1 << 1
MODEL_CACHE_FLAG_COLORS  = 1 << 2
MODEL_CACHE_FLAG_LMAP    = 1 << 3
# arcade
MODEL_CACHE_FLAG_FIFO_1  = 1 << 8
MODEL_CACHE_FLAG_FIFO_2  = 1 << 9


MODEL_CACHE_HEADER_STRUCT = struct.Struct('<I f IIi')
#   flags
#   bounding_radius
#   vert_count
#   tri_count
#   tex_count

ARC_OBJECT_HEADER_STRUCT = struct.Struct('<IIII')
#   fifo_data_size
#   vert_data_size
#   tri_data_size
#   norm_data_size

PS2_OBJECT_HEADER_STRUCT = struct.Struct('<I')
#   geom_count

PS2_SUBOBJ_HEADER_STRUCT = struct.Struct('<Hh ii')
#   qword_count
#   lod_k
#   tex_index
#   lm_index


def parse_model_cache_header(rawdata):
    cache_header = read_cache_header(rawdata)
    flags, bounding_radius, vert_count, tri_count, tex_count = \
           MODEL_CACHE_HEADER_STRUCT.unpack(
               rawdata.read(MODEL_CACHE_HEADER_STRUCT.size)
               )
    model_header = dict(
        flags=flags,
        bounding_radius=bounding_radius,
        vert_count=vert_count,
        tri_count=tri_count,
        tex_count=tex_count,
        )

    return cache_header, model_header


def serialize_model_cache_header(cache_header, model_header):
    cache_header.setdefault("subtype_version", MODEL_CACHE_VER)
    cache_header_rawdata = write_cache_header(**cache_header)
    model_header_rawdata = MODEL_CACHE_HEADER_STRUCT.pack(
        model_header.get("flags", 0),
        model_header.get("bounding_radius", 0.0),
        model_header.get("vert_count", 0),
        model_header.get("tri_count", 0),
        model_header.get("tex_count", 0),
        )

    return cache_header_rawdata + model_header_rawdata
    

def parse_model_cache(filepath=None, rawdata=None):
    rawdata = get_readable_rawdata(filepath, rawdata)
    try:
        cache_header, model_header = parse_model_cache_header(rawdata)

        # determine what parser to use
        subtype, subtype_ver = cache_header["subtype"], cache_header["subtype_version"]
        parser = _data_parsers.get((subtype, subtype_version))
        if parser is None:
            raise NotImplementedError(
                f"No parser implemented for version '{subtype_ver}' of '{subtype}'."
                )

        # read texture names
        texture_names = []
        for i in range(model_header["tex_count"]):
            start   = rawdata.tell()
            str_len = rawdata.find(b'\x00', start) - start
            if str_len <= 0:
                raise ValueError(
                    "Model data appears truncated. Cannot read texture name."
                    )

            tex_name = rawdata.read(str_len+1).decode('latin-1').rstrip('\x00')
            texture_names.append(tex_name)

        # parse the rest of the data
        model_data = parser(rawdata, cache_header, model_header)

        return dict(
            cache_header=cache_header,
            model_header=model_header,
            texture_names=texture_names,
            model_data=model_data,
            )
    finally:
        if hasattr(rawdata, "close"):
            rawdata.close()
    

def serialize_model_cache(model_cache):
    cache_header  = model_cache["cache_header"]
    model_header  = model_cache["model_header"]
    texture_names = model_cache["texture_names"]
    model_data    = model_cache["model_data"]

    # determine what serializer to use
    subtype, subtype_ver = cache_header["subtype"], cache_header["subtype_version"]
    serializer = _data_serializers.get((subtype, subtype_version))
    if serializer is None:
        raise NotImplementedError(
            f"No serializer implemented for version '{subtype_ver}' of '{subtype}'."
            )

    header_rawdata = serialize_model_cache_header(cache_header, model_header)

    # serialize texture names
    tex_names_rawdata = b''
    for tex_name in texture_names:
        tex_names_rawdata += tex_name.encode('latin-1') + b'\x00'

    # serialize the rest of the data
    model_rawdata = serializer(cache_header, model_header, model_data)

    return header_rawdata + tex_names_rawdata + model_rawdata


def _parse_ps2_model_data(rawdata, cache_header, model_header):
    geom_count = PS2_OBJECT_HEADER_STRUCT.unpack(
        rawdata.read(PS2_OBJECT_HEADER_STRUCT.size)
        )
    model_data = []
    for i in range(geom_count):
        qwc, lod_k, tex_idx, lm_idx = PS2_SUBOBJ_HEADER_STRUCT.unpack(
            rawdata.read(PS2_SUBOBJ_HEADER_STRUCT.size)
            )

        # quadwords stored is always 1 + qwc. Since we have an
        # extra half a quadword to read, add 8 bytes for this.
        vif_data = rawdata.read(qwc * 16 + 8)
        model_data.append(dict(
            vif_rawdata=vif_data,
            qword_count=qwc, lod_k=lod_k,
            tex_index=tex_idx, lm_index=lm_idx,
            ))

    return model_data


def _parse_arcade_model_data(rawdata, cache_header, model_header):
    fifo_size, vert_size, tri_size, norm_size = ARC_OBJECT_HEADER_STRUCT.unpack(
        rawdata.read(ARC_OBJECT_HEADER_STRUCT.size)
        )
    fifo_rawdata = verts_rawdata = tris_rawdata = norms_rawdata = b''
    if vert_size + tri_size + norm_size:
        if fifo_size:
            raise ValueError(
                "Detected FIFO data and uncompressed data in the same cache."
                )

        verts_rawdata = rawdata.read(vert_size)
        tris_rawdata  = rawdata.read(tri_size)
        norms_rawdata = rawdata.read(norm_size)
        fifo_rawdata  = b''
    else:
        fifo_rawdata  = rawdata.read(fifo_size)
        verts_rawdata = tris_rawdata = norms_rawdata = b''

    model_data = dict(
        fifo_rawdata=fifo_rawdata,
        verts_rawdata=verts_rawdata,
        tris_rawdata=tris_rawdata,
        norms_rawdata=norms_rawdata
        )
    return model_data


def _serialize_ps2_model_data(cache_header, model_header, model_data):
    object_rawdata = b''
    for model in model_data:
        vif_rawdata = model["vif_rawdata"]
        lod_k       = model.get("lod_k", constants.DEFAULT_MOD_LOD_K)
        tex_index   = model.get("tex_index", -1)
        lm_index    = model.get("lm_index", -1)

        subobj_rawdata = bytes(vif_rawdata)
        # pad to multiple of 16 bytes
        # NOTE: we add 8 bytes of padding or our calculation, as that would
        #       normally be the sub_object_model header in the objects file
        subobj_rawdata += b'\x00'*util.calculate_padding(len(subobj_rawdata) + 8, 16)

        # NOTE: qword_count does not include the first quadword, as it is assumed.
        #       integer division will reduce qwc by 1, so no need to subtract.
        qwc = len(subobj_rawdata) // 16

        subobj_header_rawdata = PS2_SUBOBJ_HEADER_STRUCT.pack(
            qwc, lod_k, tex_index, lm_index
            )
        object_rawdata += subobj_header_rawdata + subobj_rawdata

    # serialize the subobject count
    object_header_rawdata = PS2_OBJECT_HEADER_STRUCT.pack(len(model_data))

    return object_header_rawdata + object_rawdata


def _serialize_arcade_model_data(cache_header, model_header, model_data):
    fifo_rawdata  = bytes(model_data["fifo_rawdata"])
    verts_rawdata = bytes(model_data["verts_rawdata"])
    tris_rawdata  = bytes(model_data["tris_rawdata"])
    norms_rawdata = bytes(model_data.get("norms_rawdata", b''))

    if fifo_rawdata:
        if (verts_rawdata or tris_rawdata or norms_rawdata):
            raise ValueError(
                "Cannot write FIFO data and uncompressed data to the same cache."
                )
        object_rawdata = fifo_rawdata
    else:
        object_rawdata = verts_rawdata + tris_rawdata + norms_rawdata

    object_header_rawdata = ARC_OBJECT_HEADER_STRUCT.pack(
        len(fifo_rawdata), len(verts_rawdata), len(tris_rawdata), len(norms_rawdata)
        )

    return object_header_rawdata + object_rawdata


_data_parsers = {
    (MODEL_CACHE_EXTENSION_NGC,  MODEL_CACHE_VER): _parse_ps2_model_data,
    (MODEL_CACHE_EXTENSION_PS2,  MODEL_CACHE_VER): _parse_ps2_model_data,
    (MODEL_CACHE_EXTENSION_XBOX, MODEL_CACHE_VER): _parse_ps2_model_data,
    (MODEL_CACHE_EXTENSION_DC,   MODEL_CACHE_VER): _parse_arcade_model_data,
    (MODEL_CACHE_EXTENSION_ARC,  MODEL_CACHE_VER): _parse_arcade_model_data,
    }


_data_serializers = {
    (MODEL_CACHE_EXTENSION_NGC,  MODEL_CACHE_VER): _serialize_ps2_model_data,
    (MODEL_CACHE_EXTENSION_PS2,  MODEL_CACHE_VER): _serialize_ps2_model_data,
    (MODEL_CACHE_EXTENSION_XBOX, MODEL_CACHE_VER): _serialize_ps2_model_data,
    (MODEL_CACHE_EXTENSION_DC,   MODEL_CACHE_VER): _serialize_arcade_model_data,
    (MODEL_CACHE_EXTENSION_ARC,  MODEL_CACHE_VER): _serialize_arcade_model_data,
    }
