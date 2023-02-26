import os

from traceback import format_exc

from .tag import GdlTag
from ..texdef import texdef_ps2_def
from ...compilation.util import calculate_padding
from ...compilation.g3d import constants as c


class ObjectsPs2Tag(GdlTag):
    texdef_names  = None

    _object_assets_by_name  = None
    _bitmap_assets_by_name  = None
    _object_assets_by_index = None
    _bitmap_assets_by_index = None

    def load_texdef_names(self, filepath=None):
        if filepath is None:
            filepath = os.path.join(
                os.path.dirname(self.filepath), "%s.%s" % (
                    c.TEXDEF_FILENAME, c.PS2_EXTENSION
                    )
                )

        texdef_tag = texdef_ps2_def.build(filepath=filepath)
        bitmap_defs = texdef_tag.data.bitmap_defs
        bitmaps     = texdef_tag.data.bitmaps
        self.texdef_names = {
            bitmaps[i].tex_pointer: bitmap_defs[i].name
            for i in range(min(len(bitmap_defs), len(bitmaps)))
            if bitmap_defs[i].name
            }

    def generate_cache_names(self):
        bitmaps     = self.data.bitmaps
        objects     = self.data.objects
        object_defs = self.data.object_defs
        bitmap_defs = self.data.bitmap_defs
        texdef_names = self.texdef_names
        object_names = {
            b.obj_index: dict(name=b.name, asset_name=b.name, index=b.obj_index)
            for b in object_defs if b.name
            }
        bitmap_names = {
            b.tex_index: dict(name=b.name, asset_name=b.name, index=b.tex_index)
            for b in bitmap_defs if b.name
            }
        if texdef_names:
            # grab additional names from texdefs
            bitm_i = 0
            texdef_names = dict(self.texdef_names)
            while bitm_i < len(bitmaps):
                bitm = bitmaps[bitm_i]
                if bitm.tex_pointer in texdef_names and not bitmap_names.get(bitm_i):
                    # bitmaps with frame counts are sequences
                    name = texdef_names.pop(bitm.tex_pointer)
                    bitmap_names[bitm_i] = dict(name=name, asset_name=name, index=bitm_i)

                bitm_i += 1

        object_frame_counts = {b.obj_index: b.frames + 1 for b in object_defs if b.name}

        lm_start = getattr(self.data.header, "lm_tex_first", 0)
        lm_num   = getattr(self.data.header, "lm_tex_num", 0)
        lightmap_indices = set(range(lm_start, lm_start + lm_num))
        texture_model_indices = {}

        # track how many times each name is used
        name_counts = {d['name']: 0 for d in object_names.values()}

        frame_count, asset_name = 0, c.UNNAMED_ASSET_NAME
        # make best guess at model names
        for i in range(len(objects)):
            if i in object_names or frame_count == 0:
                # object has a name or is completely untied to anything named
                asset_name = object_names.get(i, dict(name=c.UNNAMED_ASSET_NAME))['name']

            name_count = name_counts.setdefault(asset_name, 0)
            name_counts[asset_name] += 1
            frame_count = max(0, object_frame_counts.get(i, frame_count) - 1)

            object_name = f"{asset_name}.{name_count:05}" if name_count else asset_name
            object_names[i] = dict(name=object_name, asset_name=asset_name, index=i)

            # populate maps to help name bitmaps
            obj            = objects[i]
            obj_flags      = getattr(obj, "flags", None)
            subobj_headers = tuple(getattr(obj.data, "sub_objects", ())) + (obj.sub_object_0, )
            for subobj_header in subobj_headers:
                texture_model_indices.setdefault(subobj_header.tex_index, set()).add(i)
                if getattr(obj_flags, "lmap", False):
                    lightmap_indices.add(subobj_header.lm_index)


        lightmap_indices = list(sorted(lightmap_indices))
        texture_model_indices = {k: list(sorted(v)) for k, v in texture_model_indices.items()}


        # reset for tracking bitmaps
        name_counts = {d['name']: 0 for d in object_names.values()}
        name_counts[c.LIGHTMAP_NAME] = 0

        # name the lightmaps
        for i in lightmap_indices:
            if i not in bitmap_names:
                asset_name = "%s.%s" % (c.LIGHTMAP_NAME, name_counts[c.LIGHTMAP_NAME])
                bitmap_names.setdefault(i, dict(index=i, name=asset_name))
                bitmap_names[i]["asset_name"] = asset_name
                name_counts[c.LIGHTMAP_NAME] += 1

        # make best guess at bitmap names
        frame_count, asset_name = 0, c.UNNAMED_ASSET_NAME
        for i in range(len(bitmaps)):
            bitm = bitmaps[i]
            if frame_count == 0:
                # either get the bitmaps actual name, the name of the model
                # that uses this texture, or __UNNAMED if all else fails
                obj_index  = texture_model_indices.get(i, [0xFFffFFff])[0]
                asset_name = bitmap_names.get(
                    i, object_names.get(obj_index, dict(name=c.UNNAMED_ASSET_NAME))
                    )['name']

            name_count = name_counts.setdefault(asset_name, 0)
            name_counts[asset_name] += 1
            frame_count = max(0, frame_count - 1 if frame_count else bitm.frame_count)

            if name_count or i not in bitmap_names:
                bitmap_name = f"{asset_name}.{name_count:05}"
            else:
                bitmap_name = asset_name

            bitmap_names.setdefault(i, dict(index=i, name=bitmap_name))
            bitmap_names[i]["asset_name"] = asset_name

        for names, blocks in ([object_names, objects], [bitmap_names, bitmaps]):
            for i in range(len(blocks)):
                name = f"{c.UNNAMED_ASSET_NAME}.{len(names)}"
                names.setdefault(i, dict(name=name, asset_name=name, index=i))

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
        '''
        NOTE: This function is only meant to work with v12 and v13 of the objects tag.
        '''
        header = self.data.header
        offset = offset + 160  # size of the header is 160 bytes

        if self.data.version_header.version.enum_name == "v12":
            subobj_size = 6
        elif self.data.version_header.version.enum_name == "v13":
            subobj_size = 8
        else:
            raise ValueError("Pointers can only be calculated for v12 and v13 objects.")

        # NOTE: we are intentionally serializing the object_defs and
        #       bitmap_defs before the sub_objects. Gauntlet doesn't
        #       seem to properly load player models containing a lot
        #       of data if the order mirrors existing objects files.
        obj_count = header.objects_count
        tex_count = header.bitmaps_count
        obj_def_count = header.object_defs_count
        tex_def_count = header.bitmap_defs_count

        #set the object and bitmap arrays pointers
        header.objects_pointer = offset
        offset += obj_count*64
        header.bitmaps_pointer = offset
        offset += tex_count*64

        #set the object_def and bitmap_def arrays pointers
        header.object_defs_pointer = offset
        offset += obj_def_count*24
        offset += calculate_padding(offset, 16) # 16byte align

        header.bitmap_defs_pointer = offset
        offset += tex_def_count*36
        offset += calculate_padding(offset, 16) # 16byte align 

        #loop over all objects and set the pointers of their subobjects
        header.sub_objects_pointer = offset
        for obj in self.data.objects:
            #null out the subobjects pointer if none exist
            if obj.sub_objects_count > 1:
                obj.sub_objects_pointer = offset
                offset += (obj.sub_objects_count-1)*subobj_size

        header.sub_objects_end = offset  #not 16 byte aligned
        offset += calculate_padding(offset, 16) # 16byte align 

        #loop over all objects and set the pointers of their geometry data
        for obj in self.data.objects:
            obj.sub_object_models_pointer = offset
            if obj.sub_objects_count < 2:
                obj.sub_objects_pointer = offset

            #increment the offset by the size of the model data
            for model in obj.data.sub_object_models:
                offset += 16*(model.qword_count + 1)

        offset += calculate_padding(offset, 16) # 16byte align 

        #set the file length
        header.obj_end = header.tex_bits = offset

    def serialize(self, **kwargs):
        if self.data.version_header.version.enum_name == "v4":
            raise ValueError("Cannot serialize v4 objects.")

        min_lm_index = len(self.data.bitmaps)
        max_lm_index = -1
        for obj in self.data.objects:
            if obj.flags.lmap:
                for subobj in (obj.sub_object_0,) + tuple(obj.data.sub_objects):
                    min_lm_index = min(min_lm_index, subobj.lm_index)
                    max_lm_index = max(max_lm_index, subobj.lm_index)

        if min_lm_index > max_lm_index:
            self.data.header.lm_tex_first = self.data.header.lm_tex_num = 0
        else:
            self.data.header.lm_tex_first = min_lm_index
            self.data.header.lm_tex_num   = 1 + (max_lm_index - min_lm_index)

        return GdlTag.serialize(self, **kwargs)
