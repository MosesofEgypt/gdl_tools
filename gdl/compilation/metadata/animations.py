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
    psys_metadata       = {}

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


    actors_metadata_by_atree    = {}
    actor_specific_texmods      = {}
    texmods, particle_systems   = anim_tag.data.texmods, anim_tag.data.particle_systems
    for i, atree in enumerate(anim_tag.data.atrees):
        name, meta = decompile_atree_metadata(
            atree, i, texmods, particle_systems,
            bitmap_assets, object_asset_name_map, actor_specific_texmods
            )
        actors_metadata_by_atree[i] = meta
        actors_metadata[name]       = meta


    texmods_by_source_index   = {}
    for i, texmod in enumerate(anim_tag.data.texmods):
        name, meta = actor_specific_texmods.get(i, (None, None))
        if meta is None:
            name, new_meta = decompile_texdef_metadata(texmod, bitmap_assets)
            actor_meta = actors_metadata_by_atree.get(texmod.atree)
            if actor_meta is not None:
                meta = actor_meta.setdefault("texmods", {}).setdefault(name, {})
            else:
                meta = texmods_metadata.setdefault(name, {})

            meta.update(new_meta)

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

    if hasattr(anim_tag.data.particle_systems, "__iter__"):
        for psys in anim_tag.data.particle_systems:
            psys_metadata[psys.id.enum_name] = decompile_psys_metadata(psys)


    animations_metadata = {}
    for actor_name, actor_metadata in actors_metadata.items():
        sequences = actor_metadata.pop("sequences", None)
        if not sequences:
            continue

        root_nodes = actor_metadata.get("nodes", ())
        for seq_name, seq_meta in sequences.items():
            anim_nodes = []
            animations_metadata[(actor_name, seq_name)] = dict(
                sequences = { seq_name: seq_meta },
                nodes     = anim_nodes
                )

            node_copy_pairs = [(anim_nodes, root_nodes)]
            while node_copy_pairs:
                next_node_copy_pairs = []
                for dst_children, src_children in node_copy_pairs:
                    for src_node in src_children:
                        dst_node = {}
                        dst_node.update({
                            k: v for k, v in src_node.items()
                            if k not in ("children", "object_anims")
                            })
                        dst_children.append(dst_node)
                        object_anims = src_node.get("object_anims", {})
                        if seq_name in object_anims:
                            dst_node.update(
                                object_anims = { seq_name: object_anims[seq_name] }
                                )

                        if src_node.get("children"):
                            dst_node.update(children = [])
                            next_node_copy_pairs.append((
                                dst_node["children"], src_node["children"]
                                ))

                node_copy_pairs = next_node_copy_pairs


        for node in root_nodes:
            if not node.get("object_anims"):
                node.pop("object_anims", None)


    metadata_sets = {
        "_texmods":          dict(texmods          = texmods_metadata),
        "_particle_systems": dict(particle_systems = psys_metadata),
        **{
            f"{actor_name}/{actor_name}_actor": dict(
                actors = {actor_name: actors_metadata[actor_name]}
                )
            for actor_name in sorted(actors_metadata)
            },
        **{
            f"{actor_name}/animations/{seq_name}": dict(
                actors = {actor_name: animations_metadata[(actor_name, seq_name)]}
                )
            for actor_name, seq_name in sorted(animations_metadata)
            },
        }

    util.dump_metadata_sets(
        metadata_sets, asset_types=asset_types, overwrite=overwrite,
        data_dir=data_dir, assets_dir=assets_dir, cache_dir=cache_dir,
        )


def decompile_atree_metadata(
        atree, atree_index, texmods, particle_systems,
        bitmap_assets, object_asset_name_map, actor_specific_texmods
        ):
    meta    = dict(
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
    for i, sequence in enumerate(atree_data.atree_sequences):
        seq_meta = dict(frame_rate = sequence.frame_rate)

        if sequence.repeat == "yes":
            seq_meta.update(repeat = True)

        if sequence.flags.play_reversed:
            seq_meta.update(reverse = True)

        meta["sequences"][sequence.name.upper()] = seq_meta

        for j in range(sequence.texmod_count):
            j += sequence.texmod_index
            if j in range(len(texmods)):
                texmod = texmods[j]
                name, texmod_meta = decompile_texdef_metadata(texmod, bitmap_assets)
                actor_specific_texmods[j] = (name, texmod_meta)
                seq_meta.setdefault("texmods", {})\
                        .setdefault(name, {})\
                        .update(texmod_meta)

    seen_psys_ids   = {}
    nodes_by_index  = {}
    for i, node in enumerate(anode_infos):
        node_meta   = dict(parent=node.parent_index, index=i)
        node_type   = node.anim_type.enum_name
        node_name   = node.mb_desc.upper()

        if node_type in ("null", "<INVALID>"):
            node_meta.update(is_null=True)
        elif node_type == "texture":
            if node.anim_seq_info_index in range(len(texmods)):
                texmod = texmods[node.anim_seq_info_index]

                name, texmod_meta = decompile_texdef_metadata(texmod, bitmap_assets)
                actor_specific_texmods[node.anim_seq_info_index] = (name, texmod_meta)

                node_meta.setdefault("texmods", {})\
                        .setdefault(name, {})\
                        .update(texmod_meta)
        elif node_type == "object":
            obj_anims_meta = dict()
            node_meta.update(object_anims = obj_anims_meta)

            for j, sequence in enumerate(atree_data.atree_sequences):
                try:
                    obj_anim = obj_anims[j + node.anim_seq_info_index]
                except Exception:
                    continue

                object_name = obj_anim.mb_desc.upper()
                obj_anim_meta = dict(
                    object_name = object_asset_name_map.get(
                        object_name, object_name
                        )
                    )

                if obj_anim.start_frame:
                    obj_anim_meta.update(start_frame = obj_anim.start_frame)

                obj_anims_meta[sequence.name.upper()] = obj_anim_meta

        elif node_type == "particle_system":
            try:
                psys = particle_systems[node.anim_seq_info_index]
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

        nodes_by_index[i] = node_meta

    if nodes_by_index:
        for i in sorted(nodes_by_index):
            node_meta    = nodes_by_index[i]
            parent_index = node_meta.pop("parent")
            if parent_index == -1:
                meta["nodes"].append(node_meta)
                continue

            parent_meta  = nodes_by_index.get(parent_index)
            if not parent_meta:
                raise ValueError("Node parent does not exist. Cannot extract node graph.")

            parent_meta.setdefault("children", []).append(node_meta)

    return name, meta


def decompile_texdef_metadata(texmod, bitmap_assets):
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
