import os

from . import constants as c
from . import util


def compile_animations_metadata(data_dir, by_asset_name=False):
    return util.compile_metadata(data_dir, by_asset_name=by_asset_name)


def decompile_animations_metadata(
        anim_tag, data_dir="", objects_tag=None,
        asset_types=c.METADATA_ASSET_EXTENSIONS[0],
        overwrite=False, individual_meta=True
        ):
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    actors_metadata     = {}
    texmods_metadata    = {}
    psys_metadata       = {}

    actors_metadata_by_atree        = {}
    seq_metadata_by_atree_seq       = {}
    node_metadata_by_texmod_index   = {}

    object_name_asset_map = {}
    if objects_tag:
        object_assets, bitmap_assets = objects_tag.get_cache_names()
        for i, object_def in objects_tag.get_object_names().items():
            object_name_asset_map[object_def["name"]] = object_assets[i]["asset_name"]

    else:
        object_assets, bitmap_assets = {}, {}

    for i, atree in enumerate(anim_tag.data.atrees):
        meta = dict(
            prefix      = atree.atree_header.prefix.upper(),
            nodes       = [],
            sequences   = dict(),
            )

        name = atree.name.upper()
        if meta["prefix"] == name:
            del meta["prefix"]

        atree_data  = atree.atree_header.atree_data
        anode_infos = atree_data.anode_infos
        obj_anims   = atree_data.obj_anim_header.obj_anims
        for j, sequence in enumerate(atree_data.atree_sequences):
            seq_meta = dict(frame_rate = sequence.frame_rate)

            if sequence.repeat == "yes":
                seq_meta.update(repeat = True)

            if sequence.flags.play_reversed:
                seq_meta.update(reverse = True)

            meta["sequences"][sequence.name.upper()] = seq_meta
            seq_metadata_by_atree_seq[(i, j)]        = seq_meta

        seen_psys_ids   = {}
        for j, node in enumerate(anode_infos):
            node_meta   = dict(parent=node.parent_index)
            node_type   = node.anim_type.enum_name
            node_name   = node.mb_desc.upper()

            if node_type in ("null", "<INVALID>"):
                node_meta.update(is_null=True)
            elif node_type == "texture":
                node_metadata_by_texmod_index[node.anim_seq_info_index] = node_meta
            elif node_type == "object":
                obj_anims_meta = dict()
                node_meta.update(object_anims = obj_anims_meta)

                for k, sequence in enumerate(atree_data.atree_sequences):
                    try:
                        obj_anim = obj_anims[k + node.anim_seq_info_index]
                    except Exception:
                        continue

                    object_name = obj_anim.mb_desc.upper()
                    obj_anim_meta = dict(
                        object_name = object_name_asset_map.get(
                            object_name, object_name
                            ),
                        frame_count = obj_anim.frame_count,
                        )

                    if obj_anim.start_frame:
                        obj_anim_meta.update(start_frame = obj_anim.start_frame)

                    obj_anims_meta[sequence.name.upper()] = obj_anim_meta

            elif node_type == "particle_system":
                try:
                    psys = anim_tag.data.particle_systems[node.anim_seq_info_index]
                    psys_id = psys.id.enum_name
                    node_meta.update(particle_system_id = psys_id)
                except Exception:
                    pass

            if node_name:
                node_meta.update(name = node_name)

            x, y, z = node.init_pos
            if x**2 + y**2 + z**2:
                node_meta.update(pos_x=x, pos_y=y, pos_z=z)

            flags = node.mb_flags
            for flag in flags.NAME_MAP:
                if flags[flag]:
                    node_meta.setdefault("flags", {})[flag] = True

            meta["nodes"].append(node_meta)
            
        actors_metadata_by_atree[i] = meta
        actors_metadata[name]       = meta


    texmods_by_source_index = {}
    for i, texmod in enumerate(anim_tag.data.texmods):
        meta = dict()
        name = bitmap_assets.get(texmod.tex_index, {}).get(
            "asset_name", texmod.name
            ).upper()

        texmod_type     = texmod.type.transform.enum_name
        frame_rate      = 30 / (texmod.frame_count if texmod.frame_count else 1)
        tex_swap_rate   = 30 / max(1, texmod.frames_per_tex)
        transform_start = (texmod.start_frame / 30) * frame_rate
        is_texswap      = False


        if texmod_type in ("fade_in", "fade_out"):
            meta.update(fade_rate=frame_rate)
            if transform_start:
                meta.update(fade_start=transform_start)

        elif texmod_type in ("scroll_u", "scroll_v"):
            meta.update({f"{texmod_type}_rate": frame_rate})
            if transform_start:
                meta.update({f"{texmod_type}_start": transform_start})

        elif texmod_type == "external":
            meta.update(external=True)
        else:
            is_texswap = True
            meta.update(frame_rate=tex_swap_rate)
            if transform_start:
                meta.update(start_frame=texmod.tex_start_frame)

        if i in node_metadata_by_texmod_index:
            texmods_dict = node_metadata_by_texmod_index[i].setdefault("texmods", {})
        elif (texmod.atree, texmod.seq_index) in seq_metadata_by_atree_seq:
            texmods_dict = seq_metadata_by_atree_seq[
                (texmod.atree, texmod.seq_index)
                ].setdefault("texmods", {})
        elif texmod.atree in actors_metadata_by_atree:
            texmods_dict = actors_metadata_by_atree[texmod.atree]\
                           .setdefault("texmods", {})
        else:
            texmods_dict = texmods_metadata

        texmods_dict.setdefault(name, {}).update(meta)

        if is_texswap:
            texmods_by_source_index.setdefault(texmod.type.source_index.idx, {})\
                                   .setdefault(name, []).append(texmods_dict[name])

    # for texmods that share the same texture frames, we assign all the frames
    # to the alphabetically first in the array, and have the others reference it.
    for source_index, metas in texmods_by_source_index.items():
        source_name = sorted(metas)[0]
        for texmod_name, metas_array in metas.items():
            if texmod_name == source_name:
                continue

            for meta in metas_array:
                meta["source_name"] = source_name


    if hasattr(anim_tag.data.particle_systems, "__iter__"):
        for psys in anim_tag.data.particle_systems:
            psys_metadata[psys.id.enum_name] = decompile_psys_metadata(psys)


    if individual_meta:
        metadata_sets = {
            f"actor_{name}": dict(
                actors = { name: metadata }
                )
            for name, metadata in actors_metadata.items()
            }
    else:
        metadata_sets = dict(actors = dict(actors = actors_metadata))

    metadata_sets.update(
        texmods             = dict(texmods              = texmods_metadata),
        particle_systems    = dict(particle_systems     = psys_metadata),
        )


    os.makedirs(data_dir, exist_ok=True)
    for set_name in metadata_sets:
        for asset_type in asset_types:
            filepath = os.path.join(data_dir, "%s.%s" % (set_name, asset_type))
            util.dump_metadata(metadata_sets[set_name], filepath, overwrite)


def decompile_psys_metadata(psys):
    meta = dict(
        particle_data = {},
        emitter_data  = {},
        )

    flags           = psys.flags
    enables         = psys.enables
    flag_enables    = psys.flag_enables
    for flag in flags.NAME_MAP:
        if not flags[flag]: continue
        meta.setdefault("flags", {})[flag] = True
        if not flag_enables[flag]:
            meta.setdefault("flag_disables", {})[flag] = False

    if enables.preset:  meta.update(preset=psys.preset.enum_name)
    if enables.max_p:   meta.update(max_p=psys.max_p)
    if enables.max_dir: meta.update(max_dir=psys.max_dir)
    if enables.max_pos: meta.update(max_pos=psys.max_pos)

    data = meta["emitter_data"]
    if enables.e_delay:     data.update(spawn_delay=round(psys.e_delay, 7))
    if enables.e_rate_rand: data.update(spawn_rate_rand=round(psys.e_rate_rand, 7))
    if enables.e_angle:     data.update(spawn_angle_rand=round(psys.e_angle, 7))

    if enables.e_life:
        if psys.e_life[0] > 0: data.update(phase_a_dur=round(psys.e_life[0], 7))
        if psys.e_life[1] > 0: data.update(phase_b_dur=round(psys.e_life[1], 7))

    if enables.e_dir:
        data.update(
            spawn_dir_i=round(psys.e_dir[0], 7),
            spawn_dir_j=round(psys.e_dir[1], 7),
            spawn_dir_k=round(psys.e_dir[2], 7)
            )

    if enables.e_vol:
        data.update(
            spawn_vol_width=round(psys.e_vol[0], 7),
            spawn_vol_height=round(psys.e_vol[1], 7),
            spawn_vol_length=round(psys.e_vol[2], 7)
            )

    if enables.e_rate:
        if (psys.e_rate[0] == psys.e_rate[1] and
            psys.e_rate[1] == psys.e_rate[2] and
            psys.e_rate[2] == psys.e_rate[3]):
            data.update(spawn_rate=round(psys.e_rate[0], 7))
        else:
            data.update({
                f"spawn_rate_{k}": round(v, 7) for k, v in
                _decompile_phase_property_metadata(psys.e_rate).items()
                })

    data = meta["particle_data"]
    if enables.p_texcnt:    data.update(tex_count=psys.p_texcnt)
    if enables.p_texname:   data.update(tex_name=psys.p_texname)
    if enables.p_gravity:   data.update(gravity=round(psys.p_gravity, 7))
    if enables.p_drag:      data.update(drag=round(psys.p_drag, 7))
    if enables.p_speed:     data.update(speed=round(psys.p_speed, 7))

    if enables.p_life:
        if psys.p_life[0] > 0: data.update(phase_a_dur=round(psys.p_life[0], 7))
        if psys.p_life[1] > 0: data.update(phase_b_dur=round(psys.p_life[1], 7))

    if enables.p_rgb or enables.p_alpha:
        colors = [tuple(v) for v in psys.p_color]
        if (colors[0] == colors[1] and
            colors[1] == colors[2] and
            colors[2] == colors[3]):
            color_tints = dict(color_tint=tuple(colors[0]))
        else:
            color_tints = {
                f"color_tint_{k}": v for k, v in
                _decompile_phase_property_metadata(colors).items()
                }

        if enables.p_rgb:
            color_tints = {k: (255, 255, 255, v[3]) for k, v in color_tints.items()}
        elif not enables.p_alpha:
            color_tints = {k: (v[0], v[1], v[2], 255) for k, v in color_tints.items()}

        data.update({
            k: bytes((v[0], v[1], v[2], v[3])).hex()
            for k, v in color_tints.items()
            })

    if enables.p_width:
        if (psys.p_width[0] == psys.p_width[1] and
            psys.p_width[1] == psys.p_width[2] and
            psys.p_width[2] == psys.p_width[3]):
            data.update(diameter=round(psys.p_width[0], 7))
        else:
            data.update({
                f"diameter_{k}": round(v, 7) for k, v in
                _decompile_phase_property_metadata(psys.p_width).items()
                })

    return meta


def _decompile_phase_property_metadata(prop):
    data = {}
    if prop[1] == prop[2]:
        if prop[0] == prop[1]:
            data.update(b_in=prop[2], b_out=prop[3])
        elif prop[2] == prop[3]:
            data.update(a_in=prop[0], a_out=prop[1])
        else:
            data.update(a_in=prop[0], a_out_b_in=prop[1], b_out=prop[3])
    elif prop[0] != prop[1] and prop[2] == prop[3]:
        data.update(a_in=prop[0], a_out=prop[1], b=prop[3])
    elif prop[0] == prop[1] and prop[2] != prop[3]:
        data.update(a=prop[0], b_in=prop[2], b_out=prop[3])
    else:
        data.update(a=prop[0], b=prop[2])

    return data
