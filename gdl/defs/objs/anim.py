from .tag import GdlTag

class AnimTag(GdlTag):

    @property
    def actor_names(self):
        return tuple(sorted(
            atree.name.upper().strip() for atree in self.data.atrees
            ))

    def parse(self, **kwargs):
        super().parse(**kwargs)
        self._calculate_sequence_info_data(calc_indices=True)

    def set_pointers(self, offset):
        # TODO: write pointer calculation code
        self._calculate_sequence_info_data(calc_indices=False)

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
                else:
                    if anim_type == "null":
                        anode.anim_seq_info_index  = 0
                        anode.anim_seq_info_offset = 0

                    continue

                if calc_indices:
                    item_offset = anode.anim_seq_info_offset - array_offset
                    assert item_offset % blocksize == 0
                    anode.anim_seq_info_index = item_offset // blocksize
                else:
                    anode.anim_seq_info_offset = (
                        anode.anim_seq_info_index*blocksize + array_offset
                        )
