import pathlib

from traceback import format_exc
from supyr_struct import FieldType

from .tag import GdlTag
from ..anim import anim_def
from ..texdef import texdef_def
from ...compilation.util import calculate_padding, locate_objects_dir_files,\
     get_is_big_endian_texdef
from ...compilation.g3d import constants as c


class ObjectsTag(GdlTag):
    anim_tag    = None
    texdef_tag  = None

    _object_assets_by_name  = None
    _bitmap_assets_by_name  = None
    _object_assets_by_index = None
    _bitmap_assets_by_index = None

    _texmod_seqs  = None
    _texdef_names_by_pixels_pointer = None

    _lightmap_names = None
    _object_names   = None
    _bitmap_names   = None
    _texdef_names   = None

    def load_texmod_sequences(self, filepath=None, recache=False):
        if self._texmod_seqs and not recache:
            return
        elif self.anim_tag is None or recache:
            if filepath is None:
                filepath = locate_objects_dir_files(
                    pathlib.Path(self.filepath).parent
                    )['anim_filepath']

            if filepath:
                self.anim_tag = anim_def.build(filepath=filepath)

        self._texmod_seqs = {}
        if self.anim_tag:
            self._texmod_seqs.update({
                texmod.tex_index: dict(
                    start = texmod.type.source_index.idx,
                    count = abs(texmod.frame_count),
                    )
                for texmod in self.anim_tag.data.texmods
                if texmod.type.source_index.idx >= 0
                })

    def load_texdef_names(self, filepath=None, recache=False):
        if self._texdef_names_by_pixels_pointer and not recache:
            return
        elif self.texdef_tag is None or recache:
            if filepath is None:
                filepath = locate_objects_dir_files(
                    pathlib.Path(self.filepath).parent
                    )['texdef_filepath']

            if filepath:
                try:
                    # so strangely, some of the dreamcast texdefs are big endian
                    if get_is_big_endian_texdef(filepath):
                        FieldType.force_big()
                    self.texdef_tag = texdef_def.build(filepath=filepath)
                finally:
                    FieldType.force_normal()

        self._texdef_names_by_pixels_pointer = {}
        if self.texdef_tag:
            self._texdef_names_by_pixels_pointer.update({
                bitmap.tex_pointer: bitmap_def.name
                for bitmap, bitmap_def in zip(
                    self.texdef_tag.data.bitmaps,
                    self.texdef_tag.data.bitmap_defs
                    )
                if bitmap_def.name
                })

    def get_object_names(self, recache=False):
        if not recache and self._object_names is not None:
            return dict(self._object_names)

        object_names = {}
        for bitm_def in self.data.object_defs:
            obj_index = bitm_def.obj_index
            name      = bitm_def.name.strip().upper()

            for i in range(obj_index, obj_index + max(0, bitm_def.frames) + 1):
                object_names[i] = dict(
                    name        = (name if i == obj_index else f"{name}.{i:04}"),
                    asset_name  = name,
                    index       = i
                    )

        # fill in object names that couldn't be determined
        unnamed_count = 0
        for i, obj in enumerate(self.data.objects):
            if i in object_names:
                continue

            name = f"{c.UNNAMED_ASSET_NAME}.{unnamed_count:04}"
            object_names[i] = dict(
                name=name,
                asset_name=c.UNNAMED_ASSET_NAME,
                index=i
                )
            unnamed_count += 1

        self._object_names = object_names
        return dict(self._object_names)

    def get_bitmap_def_names(self, recache=False):
        if not recache and self._bitmap_names is not None:
            return dict(self._bitmap_names)

        self._bitmap_names = {
            b.tex_index: dict(name=b.name, asset_name=b.name, index=b.tex_index)
            for b in self.data.bitmap_defs if b.name
            }

        return dict(self._bitmap_names)

    def get_texdef_names(self, recache=False):
        if not recache and self._texdef_names is not None:
            return dict(self._texdef_names)

        texdef_names     = {}
        names_by_pointer = dict(self._texdef_names_by_pixels_pointer or {})

        for i, bitm in enumerate(self.data.bitmaps):
            if i not in texdef_names and bitm.tex_pointer in names_by_pointer:
                name = names_by_pointer.pop(bitm.tex_pointer)
                texdef_names[i] = dict(name=name, asset_name=name, index=i)

        self._texdef_names = texdef_names

        return dict(self._texdef_names)

    def get_lightmap_names(self, recache=False):
        if not recache and self._lightmap_names is not None:
            return dict(self._lightmap_names)

        version         = self.data.version_header.version.enum_name
        is_vif          = version in ("v4", "v12", "v13")
        object_names    = {} if is_vif else self.get_object_names()
        lightmap_names  = {}

        if is_vif and version != "v4":
            header = self.data.header
            lightmap_names.update({
                i: dict(index=i)
                for i in range(
                    header.lm_tex_first,
                    header.lm_tex_first + header.lm_tex_num
                    )
                })

        for i, obj in enumerate(self.data.objects):
            flags  = obj.flags if is_vif else obj.lods[0].flags
            if not getattr(flags, "lmap", False):
                continue

            if is_vif:
                subobj_headers = (obj.sub_object_0, )
                if hasattr(obj.data, "sub_objects"):
                    subobj_headers += tuple(obj.data.sub_objects)

                for subobj_header in subobj_headers:
                    lightmap_names[subobj_header.lm_index] = dict(
                        index = subobj_header.lm_index
                        )

            elif flags.fifo_cmds or flags.fifo_cmds_2:
                # figure out what to do for arcade fifo lightmaps
                #raise NotImplementedError()
                pass
            else:
                # for dreamcast/arcade lightmaps, we use the name
                # of the object when naming the lightmap
                try:
                    lm_header = obj.model_data.lightmap_header
                    if (version == "v0" and (
                        lm_header.dc_lm_sig1 != c.DC_LM_HEADER_SIG1 or
                        lm_header.dc_lm_sig2 != c.DC_LM_HEADER_SIG2
                        )):
                        continue
                except Exception:
                    continue

                object_asset = object_names.get(i, {})
                name        = f"{c.LIGHTMAP_NAME}_{object_asset['name']}"
                fake_index  = -(i+1) # to identify which object its from, we'll negate it
                lightmap_names[fake_index] = dict(
                    index       = fake_index,
                    name        = name,
                    asset_name  = c.LIGHTMAP_NAME,
                    )

        # name the lightmaps
        for i, tex_index in enumerate(sorted(lightmap_names)):
            lightmap_asset = lightmap_names[tex_index]
            if "name" not in lightmap_asset:
                name = f"{c.LIGHTMAP_NAME}.{i}"
                lightmap_asset.update(
                    name        = name,
                    asset_name  = c.LIGHTMAP_NAME,
                    )

        self._lightmap_names = lightmap_names
        return dict(self._lightmap_names)

    def generate_cache_names(self):
        version = self.data.version_header.version.enum_name
        is_vif  = version in ("v4", "v12", "v13")

        bitmap_names = {}
        object_names = self.get_object_names()

        # use model names to help name bitmaps
        if is_vif:
            name_counts = {}
            for i, obj in enumerate(self.data.objects):
                asset_name = object_names[i]["asset_name"]
                name_counts.setdefault(asset_name, 0)

                # populate maps to help name bitmaps
                subobj_headers = (obj.sub_object_0, )
                if hasattr(obj.data, "sub_objects"):
                    subobj_headers += tuple(obj.data.sub_objects)

                for header in subobj_headers:
                    if header.tex_index in bitmap_names:
                        continue

                    name = f"{asset_name}.{name_counts[asset_name]:04}"
                    name_counts[asset_name] += 1
                    bitmap_names[header.tex_index] = dict(
                        name=name, asset_name=asset_name, index=header.tex_index
                        )

        # generate names of lightmaps
        bitmap_names.update(self.get_lightmap_names())

        # grab names from texdefs and bitmap_defs
        bitmap_names.update(self.get_texdef_names())
        bitmap_names.update(self.get_bitmap_def_names())

        # fill in bitmap names that couldn't be determined
        asset_name, basename, unnamed_ct, name_index, frames = "", "", 0, 0, 0

        for i, bitm in enumerate(self.data.bitmaps):
            if bitm.frame_count and i in bitmap_names:
                asset_name  = bitmap_names[i]["asset_name"]
                basename    = bitmap_names[i]["name"]
                frames      = max(0, bitm.frame_count)
                name_index  = 0

            if i in bitmap_names:
                continue
            elif frames > 0:
                frames  -= 1
            else:
                basename    = c.UNNAMED_ASSET_NAME
                asset_name  = c.UNNAMED_ASSET_NAME
                name_index  = unnamed_ct
                unnamed_ct  += 1

            name = f"{basename}.{name_index:04}"
            bitmap_names[i] = dict(name=name, asset_name=asset_name, index=i)
            name_index += 1

        self._object_assets_by_index = object_names
        self._bitmap_assets_by_index = bitmap_names
        self._object_assets_by_name  = {d['name']: d for i, d in self._object_assets_by_index.items()}
        self._bitmap_assets_by_name  = {d['name']: d for i, d in self._bitmap_assets_by_index.items()}

    def get_cache_names(self, by_name=False, recache=False):
        if None in (self._object_assets_by_index, self._object_assets_by_name,
                    self._bitmap_assets_by_index, self._bitmap_assets_by_name):
            self.generate_cache_names()

        if by_name:
            object_names = self._object_assets_by_name
            bitmap_names = self._bitmap_assets_by_name
        else:
            object_names = self._object_assets_by_index
            bitmap_names = self._bitmap_assets_by_index

        return dict(object_names), dict(bitmap_names)

    def set_pointers(self, offset=0):
        header  = self.data.header
        version = self.data.version_header.version.enum_name

        objects = self.data.objects
        bitmaps = self.data.bitmaps
        object_defs = self.data.object_defs
        bitmap_defs = self.data.bitmap_defs

        alignment   = 16
        subobj_size = 8
        bitmap_size = 64
        object_size = 64
        bitmap_def_size = 36
        object_def_size = 24

        # add in the header size
        offset += (
            68 + # version header
            (92 if version in ("v12", "v13") else 36) # main header
            )
        if version in ("v0", "v1"):
            bitmap_size = 80
            object_size = 140
            subobj_size = 4
            alignment   = 4
        elif version == "v4":
            bitmap_size = 80
            subobj_size = 4
        elif version == "v12":
            subobj_size = 6
        elif version != "v13":
            raise ValueError("Pointers can only be calculated for v0, v1, v4, v12, and v13 objects.")

        # imitate some crap midway did where 0 in the object_defs_count
        # means that both arrays use the objects_count as their count.
        if version in ("v0", "v1") and len(object_defs) == len(objects):
            header.object_defs_count = 0

        # same thing for the bitmap_defs, but only in v0
        if version == "v0" and len(bitmap_defs) == len(bitmaps):
            header.bitmap_defs_count = 0

        # NOTE: we are intentionally serializing the object_defs and
        #       bitmap_defs before the sub_objects. Gauntlet doesn't
        #       seem to properly load player models containing a lot
        #       of data if the order mirrors existing objects files.

        # set the object and bitmap arrays pointers
        if version in ("v12", "v13"):
            header.objects_pointer = offset
            offset += len(objects) * object_size
            header.bitmaps_pointer = offset
            offset += len(bitmaps) * bitmap_size
        else:
            # v4 and earlier don't have dedicated pointers for the objects
            # and bitmaps. its assumed they're directly after the header.
            offset += (len(objects) * object_size +
                       len(bitmaps) * bitmap_size)

        # set the object_def and bitmap_def arrays pointers
        header.object_defs_pointer = offset
        offset += len(object_defs) * object_def_size
        offset += calculate_padding(offset, alignment) # align

        header.bitmap_defs_pointer = offset
        offset += len(bitmap_defs) * bitmap_def_size
        offset += calculate_padding(offset, alignment) # align

        if version in ("v12", "v13"):
            # calculate subobject header and model pointers
            header.sub_objects_pointer = offset
            for obj in objects:
                obj.sub_objects_pointer = offset
                offset += max(0, obj.sub_objects_count-1) * subobj_size

            header.sub_objects_end = offset  # not aligned
            offset += calculate_padding(offset, alignment) # align

            # loop over all objects and set the pointers of their geometry data
            for obj in objects:
                obj.sub_object_models_pointer = offset
                if obj.sub_objects_count < 2:
                    obj.sub_objects_pointer = offset

                # increment the offset by the size of the model data
                offset += sum(
                    16*(model.qword_count + 1)
                    for model in obj.data.sub_object_models
                    )

            # set the file length
            offset += calculate_padding(offset, alignment) # align
            header.obj_end  = offset
            header.tex_bits = offset

        elif version == "v4":
            # loop over all objects and set the pointers of their geometry data
            for obj in objects:
                obj.sub_object_models_pointer = offset
                # increment the offset by the size of the model data
                offset += sum(
                    16*(model.qword_count + 1)
                    for model in obj.data.sub_object_models
                    )

        elif version in ("v0", "v1"):
            pointers_by_data = {}
            for obj in objects:
                lod0    = obj.lods[0]
                data    = obj.model_data
                flags   = lod0.flags
                header  = lod0.data

                if flags.fifo_cmds or flags.fifo_cmds_2:
                    raise ValueError("Cannot calculate pointers for arcade compressed models.")
                elif flags.v_normals and flags.lmap:
                    raise ValueError("Cannot have v_normals and lmap set at the same time.")

                if data.vert_data in pointers_by_data:
                    header.verts_pointer = pointers_by_data[data.vert_data]
                else:
                    pointers_by_data[data.vert_data] = offset
                    header.verts_pointer = offset
                    offset += len(data.vert_data)
                    offset += calculate_padding(offset, alignment) # align

                if data.tri_data in pointers_by_data:
                    header.tris_pointer = pointers_by_data[data.tri_data]
                else:
                    pointers_by_data[data.tri_data] = offset
                    header.tris_pointer = offset
                    offset += len(data.tri_data)
                    offset += calculate_padding(offset, alignment) # align

                header.aux_pointer = offset
                if flags.v_normals:
                    if data.norm_data in pointers_by_data:
                        header.aux_pointer = pointers_by_data[data.norm_data]
                    else:
                        pointers_by_data[data.norm_data] = offset
                        offset += len(data.norm_data)
                elif not flags.lmap:
                    header.aux_pointer = -1
                elif version == "v0" and (
                        data.lightmap_header.dc_lm_sig1 != c.DC_LM_HEADER_SIG1 or
                        data.lightmap_header.dc_lm_sig2 != c.DC_LM_HEADER_SIG2
                        ):
                    data.lightmap_header = None
                else:
                    offset += 12  # size of header

                offset += calculate_padding(offset, alignment) # align

                # copy pointers to all other lods
                obj.lods[1].data[:] = header
                obj.lods[2].data[:] = header
                obj.lods[3].data[:] = header

    def serialize(self, **kwargs):
        version = self.data.version_header.version.enum_name
        if version in ("v12", "v13"):
            # v12 and v13 cache the lightmap indices in the header
            min_lm_index = len(self.data.bitmaps)
            max_lm_index = -1
            for obj in self.data.objects:
                if obj.flags.lmap:
                    for subobj in (obj.sub_object_0,) + tuple(obj.data.sub_objects):
                        min_lm_index = min(min_lm_index, subobj.lm_index)
                        max_lm_index = max(max_lm_index, subobj.lm_index)

            if min_lm_index <= max_lm_index:
                self.data.header.lm_tex_first = min_lm_index
                self.data.header.lm_tex_num   = 1 + (max_lm_index - min_lm_index)
            else:
                self.data.header.lm_tex_first = 0
                self.data.header.lm_tex_num   = 0

        try:
            # younger me was an idiot. zero-fill is making the file too
            # large since some of the data may become redundant by being
            # deduplicated, and the size it fills it to may be too large
            tmp = self.zero_fill
            self.zero_fill = False
            GdlTag.serialize(self, **kwargs)
        finally:
            self.zero_fill = tmp
