import pathlib

from traceback import format_exc
from supyr_struct import FieldType

from .tag import GdlTag
from ..anim import anim_def
from ..texdef import texdef_def
from ...compilation import util
from ...compilation.g3d import constants as c


class ObjectsTag(GdlTag):
    anim_tag    = None
    texdef_tag  = None

    _anim_tag_load_attempted = False
    _texdef_tag_load_attempted = False

    _object_assets_by_name  = None
    _bitmap_assets_by_name  = None
    _object_assets_by_index = None
    _bitmap_assets_by_index = None

    _texdef_names_by_pixels_pointer = None

    _lightmap_names = None
    _object_names   = None
    _bitmap_names   = None
    _texdef_names   = None
    _obj_def_names  = None

    @property
    def texdef_names_by_pixels_pointer(self):
        return self._texdef_names_by_pixels_pointer or {}

    def load_anim_tag(self, filepath=None, recache=False):
        if (self.anim_tag and not recache) or self._anim_tag_load_attempted:
            return self.anim_tag

        if filepath is None:
            filepath = util.locate_objects_dir_files(
                pathlib.Path(self.filepath).parent
                )['anim_filepath']

        if filepath:
            self.anim_tag = anim_def.build(filepath=filepath)

        self._anim_tag_load_attempted = True
        return self.anim_tag

    def load_texdef_tag(self, filepath=None, recache=False):
        if (self.texdef_tag and not recache) or self._texdef_tag_load_attempted:
            return self.texdef_tag

        if filepath is None:
            filepath = util.locate_objects_dir_files(
                pathlib.Path(self.filepath).parent
                )['texdef_filepath']

        if filepath:
            try:
                # so strangely, some of the dreamcast texdefs are big endian
                if util.get_is_big_endian_texdef(filepath):
                    FieldType.force_big()
                self.texdef_tag = texdef_def.build(filepath=filepath)
            finally:
                FieldType.force_normal()

        self._texdef_tag_load_attempted = True
        return self.texdef_tag

    def load_texmod_sequences(self, filepath=None, recache=False):
        if self.load_anim_tag(filepath, recache):
            self.anim_tag.load_texmod_sequences(recache)

    def load_objanim_sequences(self, filepath=None, recache=False):
        if self.load_anim_tag(filepath, recache):
            self.anim_tag.load_objanim_sequences(recache)

    def load_actor_object_assets(self, filepath=None, recache=False):
        if self.load_anim_tag(filepath, recache):
            self.anim_tag.load_actor_object_assets(recache)

    def load_texdef_names(self, filepath=None, recache=False):
        if self._texdef_names_by_pixels_pointer is not None and not recache:
            return

        self._texdef_names_by_pixels_pointer = {}

        if self.load_texdef_tag(filepath, recache):
            self._texdef_names_by_pixels_pointer.update({
                bitmap.tex_pointer: bitmap_def.name
                for bitmap, bitmap_def in zip(
                    self.texdef_tag.data.bitmaps,
                    self.texdef_tag.data.bitmap_defs
                    )
                if bitmap_def.name
                })

    def get_texmod_names(self, recache=False):
        return self.anim_tag.get_texmod_names(recache) if self.anim_tag else {}

    def get_objanim_seqs(self, recache=False):
        if recache and self.anim_tag:
            self.anim_tag.load_objanim_sequences(recache)
        return self.anim_tag.objanim_seqs if self.anim_tag else {}

    def get_actorobj_map(self, recache=False):
        if recache and self.anim_tag:
            self.anim_tag.load_actor_object_assets(recache)
        return self.anim_tag.actorobj_map if self.anim_tag else {}

    def get_particle_map(self, recache=False):
        if recache and self.anim_tag:
            self.anim_tag.load_particle_map(recache)
        return self.anim_tag.particle_map if self.anim_tag else {}

    def get_object_names(self, recache=False):
        if not recache and self._object_names is not None:
            return dict(self._object_names)

        # fill in object names from definitions
        object_names = self.get_object_def_names(recache)
        object_count = len(self.data.objects)

        # fill in object animation frame names
        objanim_names       = {}
        object_data_by_name = { v["name"]: v for v in object_names.values()}
        for objdef_name, seq_data in self.get_objanim_seqs(recache).items():
            if objdef_name not in object_data_by_name:
                print(f"Error: Could not locate '{objdef_name}' in object defs.")
                continue

            start       = object_data_by_name[objdef_name]["index"]
            asset_name  = seq_data["name"]
            actor       = seq_data["actor"]
            for i, name in enumerate(util.generate_sequence_names(
                    asset_name, seq_data["count"],
                    )):
                i += start
                object_names[i] = dict(
                    name        = name,
                    asset_name  = asset_name,
                    def_name    = objdef_name,
                    index       = i,
                    actor       = actor
                    )

        # fill in object names that couldn't be determined
        unnamed = 0
        for i, obj in enumerate(self.data.objects):
            if i not in object_names:
                name = ".".join((
                    c.UNNAMED_ASSET_NAME,
                    util.index_count_to_string(unnamed, object_count)
                    ))
                object_names[i] = dict(asset_name=name, name=name, index=i)
                unnamed += 1

            if not object_names[i].get("actor"):
                object_names[i].pop("actor", None)

        self._object_names = object_names
        return dict(self._object_names)

    def get_object_def_names(self, recache=False):
        if not recache and self._obj_def_names is not None:
            return dict(self._obj_def_names)

        self.load_actor_object_assets(recache=recache)

        obj_def_names = {}
        actorobj_map = {} if self.anim_tag is None else self.anim_tag.actorobj_map
        for obj_def in self.data.object_defs:
            obj_index   = obj_def.obj_index
            obj_frames  = max(0, obj_def.frames) + 1
            asset_name  = obj_def.name.strip().upper()
            for i in range(obj_index, obj_index + obj_frames):
                name = (
                    asset_name if i == obj_index else
                    ".".join((name, util.index_count_to_string(i, obj_frames)))
                    )
                obj_def_names[i] = dict(
                    name        = name,
                    asset_name  = asset_name,
                    def_name    = name,
                    index       = i,
                    )
                if actorobj_map.get(name):
                    obj_def_names[i].update(actor=actorobj_map[name])

        self._obj_def_names = obj_def_names
        return dict(self._obj_def_names)

    def get_bitmap_def_names(self, recache=False):
        if not recache and self._bitmap_names is not None:
            return dict(self._bitmap_names)

        # determine which bitmaps are for particles
        particle_bitmaps = set(self.get_particle_map().values())

        self._bitmap_names = {}
        for b in self.data.bitmap_defs:
            name = b.name.upper().strip()
            if name:
                self._bitmap_names[b.tex_index] = dict(
                    name=name, asset_name=name, def_name=name, index=b.tex_index,
                    **({"actor": "_particles"} if name in particle_bitmaps else {})
                    )

        return dict(self._bitmap_names)

    def get_texdef_names(self, recache=False):
        if not recache and self._texdef_names is not None:
            return dict(self._texdef_names)

        texdef_names     = {}
        names_by_pointer = dict(self.texdef_names_by_pixels_pointer)

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

                suffix      = object_names.get(i, {}).get('name', '')
                fake_index  = -(i+1) # to identify which object its from, we'll negate it
                lightmap_names[fake_index] = dict(
                    index       = fake_index,
                    name        = "_".join((c.LIGHTMAP_NAME, suffix)),
                    asset_name  = c.LIGHTMAP_NAME,
                    )

        # name the lightmaps
        for i, tex_index in enumerate(sorted(lightmap_names)):
            if "name" not in lightmap_names[tex_index]:
                lightmap_names[tex_index].update(
                    name        = f"{c.LIGHTMAP_NAME}.{i}",
                    asset_name  = c.LIGHTMAP_NAME,
                    )

        self._lightmap_names = lightmap_names
        return dict(self._lightmap_names)

    def get_model_bitmap_names(self):
        is_vif  = self.data.version_header.version.enum_name in ("v4", "v12", "v13")

        bitmap_names = {}
        object_names = self.get_object_names()

        # loop over all objects and create a hash to map all texture
        # indices to the assets of each actor that use them
        bitmap_indices_by_actor_asset = {}
        for i, obj in enumerate(self.data.objects):
            indices = bitmap_indices_by_actor_asset\
                      .setdefault(object_names[i].get("actor", ""), {})\
                      .setdefault(object_names[i]["asset_name"], set())
            if is_vif and getattr(obj, "sub_objects_count", 1):
                # populate maps to help name bitmaps
                subobj_headers = (obj.sub_object_0, )
                if hasattr(obj.data, "sub_objects"):
                    subobj_headers += tuple(obj.data.sub_objects)

                for header in subobj_headers:
                    indices.add(header.tex_index)

        # now that we know what textures are used by each model, we'll
        # determine names for those bitmaps using the objects as a base
        for actor in sorted(bitmap_indices_by_actor_asset):
            for asset_name, indices in bitmap_indices_by_actor_asset[actor].items():
                for i, tex_index in enumerate(sorted(indices)):
                    bitmap_names.setdefault(
                        tex_index, dict(
                            asset_name  = asset_name,
                            index       = tex_index,
                            name        = ".".join((
                                asset_name, util.index_count_to_string(i, len(indices))
                                )),
                            )
                        )
                    if actor:
                        bitmap_names[tex_index].setdefault("actor", actor)

        return bitmap_names

    def generate_cache_names(self):
        version = self.data.version_header.version.enum_name
        is_vif  = version in ("v4", "v12", "v13")

        bitmap_names = {}
        object_names = self.get_object_names()
        bitmap_count = len(self.data.bitmaps)

        for other_bitmap_names in (
                self.get_model_bitmap_names(),  # get names from looking at parent object names
                self.get_lightmap_names(),      # generate names of lightmaps
                self.get_texdef_names(),        # grab names from texdefs
                self.get_bitmap_def_names(),    # grab names from bitmap_defs
                self.get_texmod_names(),        # use texmod frame names
                ):
            for k, v in other_bitmap_names.items():
                bitmap_names.setdefault(k, {}).update(v)

        seen_names   = {}
        for k, v in bitmap_names.items():
            name = v.get("name")
            seen_index = seen_names.get(name, None)
            if seen_index != k and seen_index is not None:
                print(f"Fixing conflict with name '{name}' between index {k} and {seen_index}")
                new_name = name
                i = 1
                while new_name in seen_names:
                    new_name = ".".join((
                        name, util.index_count_to_string(i, bitmap_count)
                        ))
                    i += 1

                v.update(name=new_name)

            seen_names[name] = k

        # fill in bitmap names that couldn't be determined
        unnamed = 0
        for i, bitm in enumerate(self.data.bitmaps):
            if i not in bitmap_names:
                name = ".".join((
                    c.UNNAMED_ASSET_NAME,
                    util.index_count_to_string(unnamed, bitmap_count)
                    ))
                bitmap_names[i] = dict(asset_name=name, name=name, index=i)
                unnamed += 1

            if not bitmap_names[i].get("actor"):
                bitmap_names[i].pop("actor", None)

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
        offset += util.calculate_padding(offset, alignment) # align

        header.bitmap_defs_pointer = offset
        offset += len(bitmap_defs) * bitmap_def_size
        offset += util.calculate_padding(offset, alignment) # align

        if version in ("v12", "v13"):
            # calculate subobject header and model pointers
            header.sub_objects_pointer = offset
            for obj in objects:
                obj.sub_objects_pointer = offset
                offset += max(0, obj.sub_objects_count-1) * subobj_size

            header.sub_objects_end = offset  # not aligned
            offset += util.calculate_padding(offset, alignment) # align

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
            offset += util.calculate_padding(offset, alignment) # align
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
            # keep a cache of all unique data chunks written to the file.
            # if a chunk we're about to write has already been written,
            # we'll reuse the pointer instead of writing it again.
            # TODO: see if this concept can be successfully extended to
            #       the other objects versions, and to the bitmaps too.
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
                    offset += util.calculate_padding(offset, alignment) # align

                if data.tri_data in pointers_by_data:
                    header.tris_pointer = pointers_by_data[data.tri_data]
                else:
                    pointers_by_data[data.tri_data] = offset
                    header.tris_pointer = offset
                    offset += len(data.tri_data)
                    offset += util.calculate_padding(offset, alignment) # align

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

                offset += util.calculate_padding(offset, alignment) # align

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
