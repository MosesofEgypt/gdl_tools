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

    _, bitmap_assets = objects_tag.get_cache_names()

    for i, atree in enumerate(anim_tag.data.atrees):
        meta = dict(
            prefix      = atree.atree_header.prefix.upper(),
            nodes       = dict(),
            sequences   = dict(),
            )

        name = atree.name.upper()
        if meta["prefix"] == name:
            del meta["prefix"]

        atree_data  = atree.atree_header.atree_data
        anode_infos = atree_data.anode_infos
        obj_anims   = atree_data.obj_anim_header.obj_anims
        for j, sequence in enumerate(atree_data.atree_sequences):
            seq_meta = dict()
            if sequence.frame_rate != 30:
                seq_meta.update(frame_rate = sequence.frame_rate)

            if sequence.repeat == "yes":
                seq_meta.update(repeat = True)

            if sequence.flags.play_reversed:
                seq_meta.update(play_reversed = True)

            meta["sequences"][sequence.name.upper()] = seq_meta
            seq_metadata_by_atree_seq[(i, j)]        = seq_meta

        for j, node in enumerate(anode_infos):
            node_meta   = dict()
            node_type   = node.anim_type.enum_name
            if node.anim_type.enum_name not in ("null", "<INVALID>"):
                node_meta.update(type=node_type)

            if node_type == "texture":
                node_metadata_by_texmod_index[node.anim_seq_info_index] = node_meta
            elif node_type == "object":
                obj_anims_meta = dict()
                node_meta.update(object_anims = obj_anims_meta)

                for k, sequence in enumerate(atree_data.atree_sequences):
                    try:
                        obj_anim = obj_anims[k + node.anim_seq_info_index]
                    except Exception:
                        continue

                    obj_anim_meta = dict(
                        object_name = obj_anim.mb_desc.upper(),
                        frame_count = obj_anim.frame_count,
                        )
                    if obj_anim.start_frame:
                        obj_anim_meta.update(obj_anim.start_frame)

                    obj_anims_meta[sequence.name.upper()] = obj_anim_meta

            elif node_type == "particle_system":
                try:
                    psys = anim_tag.data.particle_systems[node.anim_seq_info_index]
                except Exception:
                    continue

                node_meta.update(particle_system_id = psys.id.enum_name)

            x, y, z = node.init_pos
            if x**2 + y**2 + z**2:
                node_meta.update(pos_x=x, pos_y=y, pos_z=z)

            if node.parent_index in range(len(anode_infos)):
                node_meta.update(
                    parent=anode_infos[node.parent_index].mb_desc.upper()
                    )

            flags = node.mb_flags
            for flag in flags.NAME_MAP:
                if flags[flag]:
                    node_meta.setdefault("flags", {})[flag] = True

            meta["nodes"][node.mb_desc.upper()] = node_meta
            
        actors_metadata_by_atree[i] = meta
        actors_metadata[name]       = meta


    for i, texmod in enumerate(anim_tag.data.texmods):
        meta = dict()
        name = bitmap_assets.get(texmod.tex_index, {}).get(
            "asset_name", texmod.name
            ).upper()

        texmod_type     = texmod.type.transform.enum_name
        frame_rate      = 30 / (texmod.frame_count if texmod.frame_count else 1)
        tex_swap_rate   = 30 / max(1, texmod.frames_per_tex)
        transform_start = (texmod.start_frame / 30) * frame_rate


        if texmod_type in ("fade_in", "fade_out"):
            meta.update(
                fade_rate   = frame_rate,
                fade_start  = transform_start,
                )
        elif texmod_type in ("scroll_u", "scroll_v"):
            meta.update({
                f"{texmod_type}_rate": frame_rate,
                f"{texmod_type}_start": transform_start,
                })
        elif texmod_type == "external":
            meta.update(external=True)
        else:
            meta.update(
                tex_swap_rate           = tex_swap_rate,
                tex_swap_start_frame    = texmod.tex_start_frame,
                )

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
    if enables.e_delay:     data.update(delay=psys.e_delay)
    if enables.e_rate_rand: data.update(rate_randomness=psys.e_rate_rand)
    if enables.e_angle:     data.update(angle=psys.e_angle)

    '''if enables.e_life:
        data.update()

    if enables.e_dir:
        data.update()

    if enables.e_vol:
        data.update()

    if enables.e_rate:
        data.update()'''

    data = meta["particle_data"]
    if enables.p_texcnt:    data.update(tex_count=psys.p_texcnt)
    if enables.p_texname:   data.update(tex_name=psys.p_texname)
    if enables.p_gravity:   data.update(gravity=psys.p_gravity)
    if enables.p_drag:      data.update(drag=psys.p_drag)
    if enables.p_speed:     data.update(speed=psys.p_speed)

    '''if enables.p_life:
        data.update()

    if enables.p_color:
        data.update()

    if enables.p_width:
        data.update()'''

    return meta
