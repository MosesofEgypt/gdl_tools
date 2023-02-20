from .tag import GdlTag
from ...compilation.util import calculate_padding
from ...compilation.g3d.serialization import constants as serial_const
from ...compilation.g3d.serialization.collision import CollisionTriangle


class WorldsTag(GdlTag):
    _collision_grid_tris = None

    def get_collision_tris(self, rebuild=False):
        if self._collision_grid_tris is None or rebuild:
            # scale to world units
            unit_scale = 1 / serial_const.COLL_SCALE
            self._collision_grid_tris = tuple(
                CollisionTriangle(
                    min_y = tri.min_y * unit_scale,
                    max_y = tri.max_y * unit_scale,
                    scale = tri.scale,
                    norm  = tri.norm,
                    v0    = tri.v0,
                    v1_xz = (tri.v1_x * unit_scale, tri.v1_z * unit_scale),
                    v2_xz = (tri.v2_x * unit_scale, tri.v2_z * unit_scale),
                    )
                for tri in self.data.coll_tris
                )

        return self._collision_grid_tris

    def set_pointers(self, offset):
        header = self.data.header
        offset += 120 # size of header is 120 bytes

        # set array pointers
        header.world_objects_pointer = offset
        offset += 60 * header.world_objects_count
        header.coll_tri_pointer = offset
        offset += 40 * header.coll_tri_count

        # grid list and related data is the first of the difficult things
        # to calculate. need to calculate the pointers for each grid_entry
        # while at the same time calculating the size of all the data.
        dyn_objects = self.data.dynamic_grid_objects
        grid_rows   = self.data.grid_rows

        # sizes are in entries, not bytes
        grid_entry_list_size = 1
        grid_entry_data_size = dyn_objects.header.size
        grid_entry_rows_size = len(grid_rows)

        dyn_objects.header.offset = 0
        for grid_row in grid_rows:
            grid_row.offset = grid_entry_list_size
            grid_entry_list_size += len(grid_row.grid_entries)

            for grid_entry in grid_row.grid_entries:
                grid_entry.header.offset = 2 * grid_entry_data_size # to bytes

                grid_entry_data_size += sum(
                    # add 2 for header values(coll object index and size)
                    2 + lst.size for lst in grid_entry.grid_entry_list
                    )

        header.grid_list_pointer = offset
        offset += 2 * grid_entry_data_size
        offset += calculate_padding(offset, 4) # 4byte align
        header.grid_entry_pointer = offset
        offset += 4 * grid_entry_list_size

        header.grid_row_pointer = offset
        offset += 8 * grid_entry_rows_size

        # calculate item pointers now
        header.item_info_pointer = offset
        offset += 80 * header.item_info_count
        header.item_instance_pointer = offset
        offset += 60 * header.item_instance_count

        header.locator_pointer = offset
        offset += 28 * header.locator_count

        # now comes the animations....
        anim_header = self.data.world_anims.anim_header
        comp_data   = self.data.world_anims.compressed_data

        anim_header_size = 28 # size of anim_header
        anim_header.comp_ang_pointer = anim_header_size if comp_data.comp_angles else 0
        if anim_header.comp_ang_pointer:
            anim_header_size += 4 * len(comp_data.comp_angles)

        anim_header.comp_pos_pointer = anim_header_size if comp_data.comp_positions else 0
        if anim_header.comp_pos_pointer:
            anim_header_size += 4 * len(comp_data.comp_positions)

        anim_header.comp_scale_pointer = anim_header_size if comp_data.comp_scales else 0
        if anim_header.comp_scale_pointer:
            anim_header_size += 4 * len(comp_data.comp_scales)

        # calculate pointers for all sequence infos and data
        anim_header.sequence_info_pointer = anim_header_size
        frame_data_size = 0
        for world_anim in self.data.world_anims.animations:
            world_anim.seq_info_pointer = offset + anim_header_size
            anim_header_size += 8 # add size of seq_info struct

            frame_data = world_anim.anim_seq_info.frame_data
            world_anim.anim_seq_info.data_offset = frame_data_size

            assert len(frame_data.frame_header_flags) % 4 == 0, "Header flags not padded to multiple of 4"

            frame_data_size += (
                len(frame_data.frame_header_flags) + len(frame_data.comp_frame_data) +
                4 * (len(frame_data.initial_frame_data) + len(frame_data.uncomp_frame_data))
                )

        anim_header.blocks_pointer = anim_header_size

        header.animation_header_pointer = offset
        offset += anim_header_size + frame_data_size

        header.animations_pointer = offset
        offset += 16 * header.animations_count

        header.particle_systems_pointer = offset
        # aaaaand we're done
