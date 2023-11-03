import struct

from . import constants
from .asset_cache import AssetCache
from .. import util

# ensure they're all no more than 4 characters since we use them as the cache_type
for ext in (constants.MODEL_CACHE_EXTENSION_NGC, constants.MODEL_CACHE_EXTENSION_PS2,
            constants.MODEL_CACHE_EXTENSION_XBOX, constants.MODEL_CACHE_EXTENSION_DC,
            constants.MODEL_CACHE_EXTENSION_ARC):
    assert len(ext) <= 4

MODEL_CACHE_VER  = 0x0001

# flags
MODEL_CACHE_FLAG_NORMALS = 1 << 0
MODEL_CACHE_FLAG_COLORS  = 1 << 1
MODEL_CACHE_FLAG_LMAP    = 1 << 2
# arcade
MODEL_CACHE_FLAG_FIFO2   = 1 << 8


MODEL_CACHE_HEADER_STRUCT = struct.Struct('<I f IIi')
#   flags
#   bounding_radius
#   vert_count
#   tri_count
#   tex_count

TEXTURE_NAME_STRUCT = struct.Struct('<H')
#   name_length

ARC_OBJECT_HEADER_STRUCT = struct.Struct('<IIII')
#   fifo_data_size
#   vert_data_size
#   tri_data_size
#   norm_data_size

DC_OBJECT_HEADER_STRUCT = struct.Struct('<III')
#   vert_data_size
#   tri_data_size
#   norm_data_size

VIF_OBJECT_HEADER_STRUCT = struct.Struct('<I')
#   geom_count

VIF_SUBOBJ_HEADER_STRUCT = struct.Struct('<Hh ii')
#   qword_count
#   lod_k
#   tex_index
#   lm_index


class ModelCache(AssetCache):
    has_normals      = False
    has_colors       = False
    has_lmap         = False
    is_fifo2         = False
    bounding_radius  = 0.0
    vert_count       = 0
    tri_count        = 0
    texture_names    = ()

    @property
    def has_mesh(self):
        return bool(self.tri_count)

    def parse(self, rawdata):
        super().parse(rawdata)

        model_flags, bounding_radius, vert_count, tri_count, tex_count = \
           MODEL_CACHE_HEADER_STRUCT.unpack(
               rawdata.read(MODEL_CACHE_HEADER_STRUCT.size)
               )

        # read texture names
        texture_names = []
        for i in range(tex_count):
            (str_len, ) = TEXTURE_NAME_STRUCT.unpack(
               rawdata.read(TEXTURE_NAME_STRUCT.size)
               )
            tex_name = rawdata.read(str_len).decode('latin-1').upper()
            texture_names.append(tex_name)

        self.bounding_radius = bounding_radius
        self.vert_count      = vert_count
        self.tri_count       = tri_count
        self.texture_names   = texture_names

        self.has_normals     = bool(model_flags & MODEL_CACHE_FLAG_NORMALS)
        self.has_colors      = bool(model_flags & MODEL_CACHE_FLAG_COLORS)
        self.has_lmap        = bool(model_flags & MODEL_CACHE_FLAG_LMAP)
        self.is_fifo2        = bool(model_flags & MODEL_CACHE_FLAG_FIFO2)

    def serialize(self):
        self.cache_type_version = MODEL_CACHE_VER
        
        model_flags = (
            (MODEL_CACHE_FLAG_NORMALS * bool(self.has_normals)) |
            (MODEL_CACHE_FLAG_COLORS  * bool(self.has_colors))  |
            (MODEL_CACHE_FLAG_LMAP    * bool(self.has_lmap))    |
            (MODEL_CACHE_FLAG_FIFO2   * bool(self.is_fifo2))
            )
        model_header_rawdata = MODEL_CACHE_HEADER_STRUCT.pack(
            model_flags, self.bounding_radius,
            self.vert_count, self.tri_count, len(self.texture_names),
            )

        tex_names_rawdata = b''
        for tex_name in self.texture_names:
            tex_name_rawdata = tex_name.upper().encode('latin-1')
            tex_names_rawdata += TEXTURE_NAME_STRUCT.pack(
                len(tex_name_rawdata)
                )
            tex_names_rawdata += tex_name_rawdata

        cache_header_rawdata = super().serialize()
        return cache_header_rawdata + model_header_rawdata + tex_names_rawdata


class Ps2ModelCache(ModelCache):
    cache_type = constants.MODEL_CACHE_EXTENSION_PS2
    geoms = ()

    def __init__(self):
        super().__init__()
        self.geoms = []

    def parse(self, rawdata):
        super().parse(rawdata)

        (geom_count, ) = VIF_OBJECT_HEADER_STRUCT.unpack(
            rawdata.read(VIF_OBJECT_HEADER_STRUCT.size)
            )
        geoms = []
        for i in range(geom_count):
            qwc, lod_k, tex_idx, lm_idx = VIF_SUBOBJ_HEADER_STRUCT.unpack(
                rawdata.read(VIF_SUBOBJ_HEADER_STRUCT.size)
                )
            if tex_idx not in range(len(self.texture_names)):
                raise ValueError(f"Invalid texture index '{tex_idx}' in subobject {i}.")
            elif lm_idx >= 0 and lm_idx not in range(len(self.texture_names)):
                raise ValueError(f"Invalid lightmap index '{lm_idx}' in subobject {i}.")

            # quadwords stored is always 1 + qwc. Since we have an
            # extra half a quadword to read, add 8 bytes for this.
            vif_data = rawdata.read(qwc * 16 + 8)
            geoms.append(dict(
                vif_rawdata=vif_data,
                qword_count=qwc,
                lod_k=lod_k,
                tex_name=self.texture_names[tex_idx],
                lm_name=self.texture_names[lm_idx] if lm_idx >= 0 else "",
                ))

        self.geoms = geoms

    def serialize(self):
        object_rawdata = b''
        texture_names_dict = {}

        for geom in self.geoms:
            lod_k       = geom.get("lod_k", constants.DEFAULT_MOD_LOD_K)
            tex_name    = geom.get("tex_name", "")
            lm_name     = geom.get("lm_name", "")

            texture_names_dict.setdefault(tex_name, len(texture_names_dict))
            if self.has_lmap:
                texture_names_dict.setdefault(lm_name, len(texture_names_dict))

            tex_index   = texture_names_dict[tex_name]
            lm_index    = texture_names_dict.get(lm_name, -1)

            subobj_rawdata = bytes(geom["vif_rawdata"])
            # pad to multiple of 16 bytes
            # NOTE: we add 8 bytes of padding or our calculation, as that would
            #       normally be the sub_object_model header in the objects file
            subobj_rawdata += b'\x00'*util.calculate_padding(len(subobj_rawdata) + 8, 16)

            # NOTE: qword_count does not include the first quadword, as it is assumed.
            #       integer division will reduce qwc by 1, so no need to subtract.
            qwc = len(subobj_rawdata) // 16

            subobj_header_rawdata = VIF_SUBOBJ_HEADER_STRUCT.pack(
                qwc, lod_k, tex_index, lm_index
                )
            object_rawdata += subobj_header_rawdata + subobj_rawdata

        # serialize the subobject count
        object_header_rawdata = VIF_OBJECT_HEADER_STRUCT.pack(len(self.geoms))

        # update the texture names with the reduced set we've calculated
        texture_names_dict = {v: k for k, v in texture_names_dict.items()}
        self.texture_names = list(
            texture_names_dict[i] for i in sorted(texture_names_dict)
            )

        header_rawdata = super().serialize()
        return header_rawdata + object_header_rawdata + object_rawdata


class XboxModelCache(Ps2ModelCache):
    cache_type = constants.MODEL_CACHE_EXTENSION_XBOX


class GamecubeModelCache(Ps2ModelCache):
    cache_type = constants.MODEL_CACHE_EXTENSION_NGC


class DreamcastModelCache(ModelCache):
    cache_type = constants.MODEL_CACHE_EXTENSION_DC

    verts_rawdata = b''
    tris_rawdata  = b''
    norms_rawdata = b''

    def parse(self, rawdata):
        super().parse(rawdata)

        vert_size, tri_size, norm_size = DC_OBJECT_HEADER_STRUCT.unpack(
            rawdata.read(DC_OBJECT_HEADER_STRUCT.size)
            )
        self.verts_rawdata = rawdata.read(vert_size)
        self.tris_rawdata  = rawdata.read(tri_size)
        self.norms_rawdata = rawdata.read(norm_size)

    def serialize(self):
        object_rawdata = self.verts_rawdata + self.tris_rawdata + self.norms_rawdata
        object_header_rawdata = DC_OBJECT_HEADER_STRUCT.pack(
            len(self.verts_rawdata), len(self.tris_rawdata), len(self.norms_rawdata)
            )
        header_rawdata = super().serialize()
        return header_rawdata + object_header_rawdata + object_rawdata


class ArcadeModelCache(ModelCache):
    cache_type = constants.MODEL_CACHE_EXTENSION_ARC

    fifo_rawdata  = b''
    verts_rawdata = b''
    tris_rawdata  = b''
    norms_rawdata = b''

    def parse(self, rawdata):
        super().parse(rawdata)

        fifo_size, vert_size, tri_size, norm_size = ARC_OBJECT_HEADER_STRUCT.unpack(
            rawdata.read(ARC_OBJECT_HEADER_STRUCT.size)
            )
        if fifo_size:
            self.fifo_rawdata  = rawdata.read(fifo_size)
            self.verts_rawdata = self.tris_rawdata = self.norms_rawdata = b''
        else:
            self.verts_rawdata = rawdata.read(vert_size)
            self.tris_rawdata  = rawdata.read(tri_size)
            self.norms_rawdata = rawdata.read(norm_size)
            self.fifo_rawdata  = b''

    def serialize(self):
        if self.fifo_rawdata:
            object_rawdata = self.fifo_rawdata
        else:
            object_rawdata = self.verts_rawdata + self.tris_rawdata + self.norms_rawdata

        object_header_rawdata = ARC_OBJECT_HEADER_STRUCT.pack(
            len(self.fifo_rawdata), len(self.verts_rawdata),
            len(self.tris_rawdata), len(self.norms_rawdata)
            )

        header_rawdata = super().serialize()
        return header_rawdata + object_header_rawdata + object_rawdata


ModelCache._sub_classes = {
    cls.cache_type: cls for cls in (
        Ps2ModelCache, XboxModelCache, GamecubeModelCache,
        DreamcastModelCache, ArcadeModelCache
        )
    }
