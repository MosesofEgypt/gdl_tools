import traceback

from .tag import GdlTag
from ...compilation import util

class AnimTag(GdlTag):
    _actor_names = None
    _node_names_by_atree = None

    _texmod_seqs    = None
    _objanim_seqs   = None
    _actorobj_map   = None
    _particle_map   = None

    _texmod_names   = None

    @property
    def texmod_seqs(self): return {k: dict(v) for k, v in (self._texmod_seqs or {}).items()}
    @property
    def objanim_seqs(self): return {k: dict(v) for k, v in (self._objanim_seqs or {}).items()}
    @property
    def actorobj_map(self): return dict(self._actorobj_map or {})
    @property
    def particle_map(self): return dict(self._particle_map or {})

    def load_texmod_sequences(self, recache=False):
        if self._texmod_seqs is not None and not recache:
            return

        self._texmod_seqs = {
            i: dict(
                atree       = texmod.atree,
                seq_index   = texmod.seq_index,
                tex_index   = texmod.tex_index,
                index       = i,
                start       = texmod.type.source_index.idx,
                count       = abs(texmod.frame_count),
                name        = texmod.name.upper().strip(),
                source      = texmod.source_name.upper().strip(),
                )
            for i, texmod in enumerate(self.data.texmods)
            if texmod.type.source_index.idx >= 0
            }

    def load_objanim_sequences(self, recache=False):
        if self._objanim_seqs is not None and not recache:
            return

        self._objanim_seqs = {}

        for atree in self.data.atrees:
            prefix     = atree.atree_header.prefix.upper().strip()
            atree_data = atree.atree_header.atree_data
            obj_anims  = atree_data.obj_anim_header.obj_anims
            if not obj_anims:
                continue

            seq_names = [seq.name.upper().strip()
                         for seq in atree_data.atree_sequences]
            for node in atree_data.anode_infos:
                if node.anim_type.enum_name != "object":
                    continue

                node_name       = node.mb_desc.upper().strip()
                object_prefix   = f"{prefix}{node_name}"
                for seq_name, obj_anim in zip(
                        seq_names, obj_anims[node.anim_seq_info_index:]
                        ):
                    objdef_name = obj_anim.mb_desc.upper().strip()
                    if not objdef_name:
                        continue

                    self._objanim_seqs.update({
                        objdef_name: dict(
                            start = obj_anim.start_frame,
                            count = abs(obj_anim.frame_count),
                            name  = f"{object_prefix}_{seq_name}",
                            actor = prefix
                            )
                        })

    def load_particle_map(self, recache=False):
        if self._particle_map is not None and not recache:
            return

        self._particle_map = {}

        if not hasattr(self.data.particle_systems, "__iter__"):
            return

        for psys in self.data.particle_systems:
            name = psys.p_texname.upper().strip()
            if psys.enables.p_texname and name:
                self._particle_map.setdefault(psys.id.enum_name, name)

    def load_actor_object_assets(self, recache=False):
        if self._actorobj_map is not None and not recache:
            return

        self._actorobj_map = {}

        for atree in self.data.atrees:
            prefix  = atree.atree_header.prefix.upper().strip()
            for node in atree.atree_header.atree_data.anode_infos:
                if (node.anim_type.enum_name not in ("skeletal", "null") or
                    node.flags.no_object_def):
                    continue

                node_name   = node.mb_desc.upper().strip()
                object_name = f"{prefix}{node_name}"
                self._actorobj_map[object_name] = prefix

    def get_actor_names(self, recache=False):
        if recache or self._actor_names is None:
            self._actor_names = tuple(
                atree.name.upper().strip() for atree in self.data.atrees
                )
        return self._actor_names

    def get_actor_node_names(self, atree_index=None, recache=False):
        if recache or self._node_names_by_atree is None:
            node_names_by_atree = {}
            atrees  = self.data.atrees
            
            for i, atree in enumerate(atrees):
                nodes       = atree.atree_header.atree_data.anode_infos
                occurrances = {}
                node_names  = node_names_by_atree[i] = [None] * len(nodes)
                for j, node in enumerate(nodes):
                    node_type = node.anim_type.enum_name

                    if node_type == "particle_system":
                        name = "PSYS"
                    elif node_type == "texture":
                        name = "TEXMOD"
                    else:
                        name = node.mb_desc.upper().strip()

                    occurrances.setdefault(name, []).append(
                        (j, node.flags.no_object_def == False)
                        )

                for name, instances in occurrances.items():
                    for j, inst in enumerate(instances):
                        node_i, has_object_def = inst
                        # if the node actually uses the object
                        # model, it cant be renamed
                        if has_object_def or len(instances) == 1:
                            node_names[node_i] = name
                        else:
                            node_names[node_i] = ".".join((
                                name, util.index_count_to_string(j+1, len(instances)+1)
                                ))

            self._node_names_by_atree = node_names_by_atree

        if atree_index is None:
            return {k: list(v) for k, v in self._node_names_by_atree.items()}

        return list(self._node_names_by_atree.get(atree_index, []))

    def get_texmod_names(self, recache=False):
        if not recache and self._texmod_names is not None:
            return dict(self._texmod_names)

        actor_names      = {i: n for i, n in enumerate(self.get_actor_names())}
        texmod_seqs      = self.texmod_seqs
        bitmap_assets    = {}
        texmods_by_index = {}
        texmods_by_start = {}

        for i in sorted(texmod_seqs):
            # atree       = texmod.atree,
            # seq_index   = texmod.seq_index,
            # tex_index   = texmod.tex_index,
            # start       = texmod.type.source_index.idx,
            # count       = abs(texmod.frame_count),
            # name        = texmod.name.upper().strip(),
            # source      = texmod.source_name.upper().strip()
            seq_data = texmod_seqs[i]
            texmods_by_start.setdefault(seq_data["start"], {})\
                            .setdefault(seq_data["tex_index"], [])\
                            .append(texmod_seqs[i])
            texmods_by_index.setdefault(seq_data["tex_index"], {})\
                            .setdefault(seq_data["start"], [])\
                            .append(texmod_seqs[i])

        complete_sequences = []

        for start, seq_datas_by_index in texmods_by_start.items():
            # for texmods that share the same texture frames, we try to find
            # a common prefix among one of them and the source_name. from
            # this common prefix, we generate a series of texture frame names
            source = actor = prefix = ""

            # find defaults if some sequences are corrupt
            for index in sorted(seq_datas_by_index):
                for seq_data in seq_datas_by_index[index]:
                    if seq_data["name"]:
                        source  = source or seq_data["source"]
                        actor   = actor  or actor_names.get(seq_data["atree"])
                        prefix  = prefix or util.get_sequence_prefix(seq_data["name"], source)

            for index in sorted(seq_datas_by_index):
                for seq_data in seq_datas_by_index[index]:
                    tmp_name  = seq_data["name"] or name
                    # create the bitmap_name for the animation this texmod uses
                    complete_sequences.append(dict(
                        name   = tmp_name,
                        start  = seq_data["start"],
                        count  = seq_data["count"],
                        source = (seq_data["source"] or source),
                        actor  = (actor_names.get(seq_data["atree"]) or actor),
                        # default to the name if we failed to find a common prefix
                        prefix = ((util.get_sequence_prefix(tmp_name, source) or prefix) or tmp_name),
                        ))

        # for texmods that share the same name, we need to stitch
        # together the frames and determine the complete sequence
        for index, seq_datas_by_starts in texmods_by_index.items():

            # NOTE: doing this sorted to ensure any frames that later sequences
            #       explicitly name are overwritten with the canonical name
            for start in sorted(seq_datas_by_starts):

                # find defaults if sub-sequences are corrupt
                source  = actor = name  = prefix = ""
                for seq_data in seq_datas_by_starts[start]:
                    name    = name   or seq_data["name"]
                    source  = source or seq_data["source"]
                    prefix  = prefix or util.get_sequence_prefix(name, source)
                    actor   = actor  or actor_names.get(seq_data["atree"])

                for seq_data in seq_datas_by_starts[start]:
                    tmp_name = seq_data["name"] or name
                    complete_sequences.append(dict(
                        name   = tmp_name,
                        start  = seq_data["start"],
                        count  = seq_data["count"],
                        source = (seq_data["source"] or source),
                        actor  = (actor_names.get(seq_data["atree"]) or actor),
                        # default to the name if we failed to find a common prefix
                        prefix = ((util.get_sequence_prefix(tmp_name, source) or prefix) or tmp_name),
                        ))

        for seq in complete_sequences:
            asset_base = dict(asset_name=seq["name"], actor=seq["actor"] or "_texmods")

            # generate the names of the frames
            for i, name in enumerate(util.generate_sequence_names(
                    seq["prefix"], seq["count"], start_name=seq["source"],
                    )):
                i += seq["start"]
                bitmap_assets[i] = dict(name=name, index=i, **asset_base)


        self._texmod_names = bitmap_assets
        return dict(self._texmod_names)

    def _calculate_sequence_info_data(self, calc_indices=True):
        '''
        This method serves to calculate the offsets that are serialized to
        disk, as well as indices into the associated array. The indices are
        useful when actually operating on the data after it's been parsed.
        '''
        texmod_pointer_base = getattr(self.data.atree_list_header, "texmod_pointer", 0)
        psys_pointer_base   = getattr(self.data.atree_list_header, "particle_system_pointer", 0)

        for atree in self.data.atrees:
            atree_data = atree.atree_header.atree_data

            # fuck you for doing this, Midway
            atree_seq_pointer     = atree_data.atree_sequences.get_meta('POINTER')
            skeletal_array_offset = atree_data.anim_header.sequence_info_pointer
            object_array_offset   = atree_data.obj_anim_header.obj_anim_pointer
            texmod_array_offset   = texmod_pointer_base - atree_seq_pointer
            psys_array_offset     = psys_pointer_base   - atree_seq_pointer

            for anode in atree_data.anode_infos:
                anim_type  = anode.anim_type.enum_name
                if anim_type == "skeletal":
                    blocksize, array_offset = 8, skeletal_array_offset
                elif anim_type == "object":
                    blocksize, array_offset = 40, object_array_offset
                elif anim_type == "texture":
                    blocksize, array_offset = 88, texmod_array_offset
                elif anim_type == "particle_system":
                    blocksize, array_offset = 312, psys_array_offset
                elif anim_type == "null":
                    anode.anim_seq_info_index  = 0
                    anode.anim_seq_info_offset = 0
                    continue
                else:
                    continue

                if calc_indices:
                    item_offset = anode.anim_seq_info_offset - array_offset
                    assert item_offset % blocksize == 0
                    anode.anim_seq_info_index = item_offset // blocksize
                elif anode.anim_seq_info_index is not None:
                    anode.anim_seq_info_offset = (
                        anode.anim_seq_info_index*blocksize + array_offset
                        )

    def parse(self, **kwargs):
        # whether or not to allow corrupt tags to be built.
        # this is a debugging tool.
        allow_corrupt = kwargs.get('allow_corrupt')
        try:
            super().parse(**kwargs)
            self._calculate_sequence_info_data(calc_indices=True)
        except OSError:
            # file was likely not found, or something similar
            raise
        except Exception:
            if not allow_corrupt:
                raise
            print(traceback.format_exc())

    def set_pointers(self, offset):
        header = self.data.atree_list_header
        offset += 24 if self.data.version.enum_name == "v8" else 16

        self.data.atree_infos_pointer = offset
        offset += 36 * self.data.atree_count

        header.texmod_pointer = offset
        offset += 88 * header.texmod_count

        if self.data.version.enum_name == "v8":
            header.particle_system_pointer = offset
            offset += 312 * header.particle_system_count

        # now for the grimy animation pointers
        for atree in self.data.atrees:
            atree.offset = offset

            atree_header = atree.atree_header
            atree_data   = atree_header.atree_data
            anim_header  = atree_data.anim_header
            comp_data    = atree_data.compressed_data

            atree_offset = 56 # size of atree_header is 56 bytes
            atree_header.atree_seq_pointer = atree_offset
            atree_offset += 48 * atree_header.atree_seq_count

            atree_header.anode_info_pointer = atree_offset
            atree_offset += 60 * atree_header.anode_count

            atree_header.anim_header_pointer = atree_offset

            # calculate anim_data_size and anim_header pointers
            anim_header_size = 28 # size of anim_header
            anim_header.comp_ang_pointer    = anim_header_size if comp_data.comp_angles else 0
            anim_header_size += len(comp_data.comp_angles)    * comp_data.comp_angles.itemsize

            anim_header.comp_pos_pointer    = anim_header_size if comp_data.comp_positions else 0
            anim_header_size += len(comp_data.comp_positions) * comp_data.comp_positions.itemsize

            anim_header.comp_scale_pointer  = anim_header_size if comp_data.comp_scales else 0
            anim_header_size += len(comp_data.comp_scales)    * comp_data.comp_scales.itemsize

            # calculate pointers for all frame data
            frame_data_size = 0
            anode_infos = list(atree_data.anode_infos) # faster iteration over list
            # NOTE: doing iteration like this to mimic the order they're stored in the
            #       original game files. This helps with debugging pointer calculations
            for i in range(atree_header.atree_seq_count):
                for anode_info in anode_infos:
                    if i not in range(len(anode_info.anim_seq_infos)):
                        continue
    
                    anim_seq_info = anode_info.anim_seq_infos[i]
                    frame_data = anim_seq_info.frame_data
                    anim_seq_info.data_offset = frame_data_size

                    assert len(frame_data.frame_header_flags) % 4 == 0, "Header flags not padded to multiple of 4"

                    frame_data_size += (
                        len(frame_data.frame_header_flags) + len(frame_data.comp_frame_data) +
                        len(frame_data.initial_frame_data) * frame_data.initial_frame_data.itemsize +
                        len(frame_data.uncomp_frame_data)  * frame_data.uncomp_frame_data.itemsize
                        )
                    frame_data_size += util.calculate_padding(frame_data_size, 4) # 4byte align

            # calculate pointers for all sequence infos and obj_anims
            anim_header.sequence_info_pointer = anim_header_size
            anim_header_size += 8 * anim_header.sequence_count * anim_header.object_count
            anim_header.blocks_pointer = anim_header_size

            atree_offset += anim_header_size + frame_data_size
            atree_header.obj_anim_header_pointer = atree_offset

            atree_data.obj_anim_header.obj_anim_pointer = 8  # size of header
            atree_offset += 8 + 40 * atree_data.obj_anim_header.obj_anim_count

            offset += atree_offset

        # finally calculate the sequence info pointers
        self._calculate_sequence_info_data(calc_indices=False)
