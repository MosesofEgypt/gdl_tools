import traceback

from .tag import GdlTag
from ...compilation.util import calculate_padding

class AnimTag(GdlTag):
    _node_names_by_atree = None

    @property
    def actor_names(self):
        return tuple(
            atree.name.upper().strip() for atree in self.data.atrees
            )

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
                            node_names[node_i] = f"{name}.{j+1:06}"

            self._node_names_by_atree = node_names_by_atree

        if atree_index is None:
            return {k: list(v) for k, v in self._node_names_by_atree.items()}

        return list(self._node_names_by_atree.get(atree_index, []))

    def generate_cache_names(self):
        self.get_actor_node_names()

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
                    frame_data_size += calculate_padding(frame_data_size, 4) # 4byte align

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
