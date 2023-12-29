import pathlib

from . import constants as c
from . import util


def compile_animations_metadata(data_dir=".", cache_files=False):
    # TODO: update this to merge metadata together to allow separate animations
    #       to have separate metadata files, allowing easier editing
    return util.compile_metadata(data_dir=data_dir, cache_files=cache_files)


def decompile_animations_metadata(
        anim_tag, objects_tag=None,
        asset_types=c.METADATA_CACHE_EXTENSIONS,
        overwrite=False, data_dir=".", assets_dir=None, cache_dir=None
        ):
    actors_metadata     = {}
    texmods_metadata    = {}

    if objects_tag:
        object_assets, bitmap_assets = objects_tag.get_cache_names()
        object_asset_name_map = {
            obj_def["def_name"]: object_assets[i]["asset_name"]
            for i, obj_def in objects_tag.get_object_names().items()
            if "def_name" in obj_def
            }
    else:
        bitmap_assets = {}
        object_asset_name_map = {}

    texmods, particle_systems = anim_tag.data.texmods, anim_tag.data.particle_systems

    # decompile actors
    for i, atree in enumerate(anim_tag.data.atrees):
        node_names = anim_tag.get_actor_node_names(i)
        name, meta = decompile_atree_metadata(
            atree, texmods, node_names, bitmap_assets, object_asset_name_map
            )
        actors_metadata[name] = meta

    # decompile texmods
    texmods_by_source_index = {}
    for i, texmod in enumerate(texmods):
        if texmod.atree >= 0 or texmod.seq_index >= 0:
            # bound to a specific atree and/or sequence in it. skip
            continue

        name, meta = decompile_texmod_metadata(texmod, bitmap_assets)
        if name in texmods_metadata:
            texmods_metadata[name].update(meta)
            meta = texmods_metadata[name]

        texmods_metadata[name] = meta

        # existence of frame_rate indicates it's a tex-swap animation
        if "frame_rate" in meta:
            texmods_by_source_index.setdefault(texmod.type.source_index.idx, {})\
                                   .setdefault(name, []).append(meta)

    # for texmods that share the same texture frames, we assign all the frames
    # to the alphabetically first in the array, and have the others reference it.
    for source_index, metas in texmods_by_source_index.items():
        source_name = sorted(metas)[0]
        for texmod_name, metas_array in metas.items():
            if texmod_name == source_name:
                continue

            for meta in metas_array:
                meta["source_name"] = source_name

    # decompile particle systems
    psys_metadata = decompile_all_psys_metadata(anim_tag.data.particle_systems)

    metadata_sets = {
        f"{c.TEXMODS_FOLDERNAME}/_texmods": dict(texmods = texmods_metadata),
        f"{c.PSYS_FOLDERNAME}/_systems":    psys_metadata,
        **{
            f"{actor_name}/{actor_name}_actor": dict(
                actors = {actor_name: actors_metadata[actor_name]}
                )
            for actor_name in sorted(actors_metadata)
            }
        }

    util.dump_metadata_sets(
        metadata_sets, asset_types=asset_types, overwrite=overwrite,
        data_dir=data_dir, assets_dir=assets_dir, cache_dir=cache_dir,
        )


def decompile_atree_metadata(
        atree, texmods, node_names, bitmap_assets, object_asset_name_map
        ):

    atree_data  = atree.atree_header.atree_data
    anode_infos = atree_data.anode_infos
    obj_anims   = atree_data.obj_anim_header.obj_anims
    seq_metas   = []
    meta        = dict(
        prefix      = atree.atree_header.prefix.upper().strip(),
        nodes       = [None] * len(anode_infos),
        sequences   = dict(),
        )

    atree_name = atree.name.upper().strip()
    if meta["prefix"] == atree_name:
        del meta["prefix"]

    for i, seq in enumerate(atree_data.atree_sequences):
        seq_name = seq.name.upper().strip()
        seq_meta = meta["sequences"][seq_name] = dict(
            frame_rate = seq.frame_rate,
            node_compression = dict()
            )
        seq_metas.append(seq_meta)

        if seq.repeat == "yes":
            seq_meta.update(repeat = True)

        if seq.flags.play_reversed:
            seq_meta.update(reverse = True)

        if seq.texmod_index <= 0:
            continue

        for j in range(seq.texmod_index, seq.texmod_index + seq.texmod_count):
            if j not in range(len(texmods)):
                continue

            texmod = texmods[j]
            name, texmod_meta = decompile_texmod_metadata(texmod, bitmap_assets)
            seq_meta.setdefault("texmods", {})\
                    .setdefault(name, {})\
                    .update(texmod_meta)

    seen_nodes  = {}
    for i, node in enumerate(anode_infos):
        node_type   = node.anim_type.enum_name
        node_name   = node_names[i]
        node_meta   = dict(
            type = node_type,
            name = node_name,
            )

        if node.parent_index >= 0:
            node_meta.update(parent=node.parent_index)

        if node_type == "null":
            node_meta.update(is_null=True)
        elif node_type == "texture":
            if node.anim_seq_info_index in range(len(texmods)):
                _, texmod_meta = decompile_texmod_metadata(
                    texmods[node.anim_seq_info_index], bitmap_assets
                    )
                meta.setdefault("texmods", {})[node_name] = texmod_meta

        elif node_type == "object":
            for j, seq in enumerate(atree_data.atree_sequences):
                try:
                    obj_anim = obj_anims[j + node.anim_seq_info_index]
                except Exception:
                    continue

                object_name = obj_anim.mb_desc.upper().strip()
                seq_name    = seq.name.upper().strip()
                obj_anim_meta = dict(
                    object_name = object_asset_name_map.get(
                        object_name, object_name
                        )
                    )

                if obj_anim.start_frame:
                    obj_anim_meta.update(start_frame = obj_anim.start_frame)

                meta["sequences"][seq_name].setdefault("obj_anims", {})[node_name] = obj_anim_meta
        else:
            for seq_info, seq_meta in zip(node.anim_seq_infos, seq_metas):
                seq_meta.update(
                    node_compression = {
                        i: bool(seq_info.type.compressed_data),
                        **seq_meta["node_compression"]
                        }
                    )

        seen_nodes.setdefault(node_name, []).append(i)

        flags = node.mb_flags
        for flag in flags.NAME_MAP:
            if flags[flag]:
                node_meta.setdefault("flags", {})[flag] = True

        meta["nodes"][i] = node_meta
        if "parent" in node_meta and node_meta["parent"] not in range(len(meta["nodes"])):
            raise ValueError("Node parent does not exist. Cannot extract node graph.")


    for j, seq_meta in enumerate(seq_metas):
        node_comp = seq_meta["node_compression"]
        compress = sum(
            1 if compressed else -1
            for compressed in node_comp.values()
            ) >= 0

        # set default compression and remove per-node overrides that match it
        seq_meta["compress"] = compress
        [node_comp.__delitem__(v) for v in tuple(node_comp.values()) if v != compress]
        if not node_comp:
            del seq_meta["node_compression"]

    return atree_name, meta


def decompile_texmod_metadata(texmod, bitmap_assets):
    meta = dict()
    name = bitmap_assets.get(texmod.tex_index, {}).get(
        "asset_name", texmod.name
        ).upper()

    texmod_type     = texmod.type.transform.enum_name
    frame_rate      = 30 / (texmod.frame_count if texmod.frame_count else 1)
    tex_swap_rate   = 30 / max(1, texmod.frames_per_tex)
    transform_start = (texmod.start_frame / 30) * frame_rate

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
        meta.update(frame_rate=tex_swap_rate)
        if transform_start:
            meta.update(start_frame=texmod.tex_start_frame)

    return name, meta


def decompile_all_psys_metadata(particle_systems):
    psys_metadata = {}
    # decompile particle systems
    if hasattr(particle_systems, "__iter__"):
        for psys in particle_systems:
            psys_metadata[psys.id.enum_name] = decompile_psys_metadata(psys)

    return dict(particle_systems=psys_metadata)


def decompile_psys_metadata(psys):
    meta = dict(
        particle_data = {},
        emitter_data  = {},
        )

    flags        = psys.flags
    enables      = psys.enables
    flag_enables = psys.flag_enables
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
    if enables.p_gravity:   data.update(gravity_mul=round(psys.p_gravity, 7))
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
