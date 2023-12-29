import os
import pathlib

from traceback import format_exc
from .serialization.animation import G3DAnimation
from .serialization.asset_cache import get_asset_checksum,\
     verify_source_file_asset_checksum
from .serialization.animation_cache import AnimationCache, Ps2AnimationCache,\
     AnimationCacheNode
from . import constants as c
from . import util

def compile_animation(kwargs):
    name             = kwargs.pop("name")
    cache_type       = kwargs.pop("cache_type")
    cache_filepath   = kwargs.pop("cache_filepath")
    asset_filepath   = kwargs.pop("asset_filepath")

    print("Compiling animation: %s" % name)
    g3d_animation = G3DAnimation()
    asset_type    = os.path.splitext(asset_filepath)[-1].strip(".")

    if asset_type == "jmm":
        g3d_animation.import_jmm(asset_filepath)
    else:
        raise NotImplementedError(f"Unknown asset type '{asset_type}'")

    animation_cache = g3d_animation.compile_g3d(cache_type)
    animation_cache.source_asset_checksum = get_asset_checksum(
        filepath=asset_filepath, algorithm=animation_cache.checksum_algorithm
        )
    animation_cache.serialize_to_file(cache_filepath)


def decompile_animation(kwargs):
    name            = kwargs["name"]
    animation_cache = kwargs["animation_cache"]
    asset_type      = kwargs["asset_type"]
    filepath        = kwargs["filepath"]

    print("Decompiling animation: %s" % name)

    if asset_type in c.ANIMATION_CACHE_EXTENSIONS:
        animation_cache.serialize_to_file(filepath)
        return

    g3d_animation = G3DAnimation()
    g3d_animation.import_g3d(animation_cache)
    if g3d_animation.compressed:
        print(f"Decompressing animation {name} for export...")
        g3d_animation.decompress()

    if asset_type == "jmm":
        g3d_animation.export_jmm(filepath)
    else:
        raise NotImplementedError(f"Unknown asset type '{asset_type}'")


def import_animations(
        anim_tag, objects_tag,
        data_dir=".", cache_dir=None
        ):
    # TODO: implement this
    pass


def export_animations(
        anim_tag, asset_types=c.ANIMATION_CACHE_EXTENSIONS,
        overwrite=False, parallel_processing=True,
        data_dir=".", assets_dir=None, cache_dir=None
        ):
    data_dir = pathlib.Path(data_dir)
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    for asset_type in asset_types:
        if asset_type not in (*c.ANIMATION_CACHE_EXTENSIONS,
                              *c.ANIMATION_ASSET_EXTENSIONS):
            raise ValueError("Unknown animation type '%s'" % asset_type)

    if not assets_dir: assets_dir  = data_dir
    if not cache_dir:  cache_dir   = data_dir.joinpath(c.IMPORT_FOLDERNAME)

    cache_types = sorted(set(
        typ for typ in asset_types
        if typ in c.ANIMATION_CACHE_EXTENSIONS
        ))
    cache_type  = cache_types[0] if len(cache_types) == 1 else None

    all_job_args = []

    # loop over each object
    for i, atree in enumerate(anim_tag.data.atrees):
        actor_name       = atree.name.upper()
        anim_cache, name = None, None
        try:
            node_names  = anim_tag.get_actor_node_names(i)
            for asset_type in asset_types:
                anim_caches = atree_to_animation_caches(atree, node_names, cache_type=asset_type)

                # generate animations for object anims
                if asset_type not in c.ANIMATION_CACHE_EXTENSIONS:
                    anim_caches += atree_to_obj_anim_caches(atree, node_names)

                for anim_cache in anim_caches:
                    name = f"{actor_name}_{anim_cache.name}"
                    export_dir  = (
                        cache_dir if asset_type in c.ANIMATION_CACHE_EXTENSIONS else
                        assets_dir
                        )
                    filepath    = pathlib.Path(
                        export_dir, actor_name, c.ANIM_FOLDERNAME, f"{name}.{asset_type}"
                        )
                    if filepath.is_file() and not overwrite:
                        continue

                    all_job_args.append(dict(
                        animation_cache=anim_cache, name=name,
                        asset_type=asset_type, filepath=filepath,
                        ))
        except:
            print(format_exc())
            print(f"The above error occurred while trying to export actor {i} as {asset_type}. "
                  f"actor_name: '{actor_name}', name: '{name}'"
                  )

    print("Decompiling %s animations in %s" % (
        len(all_job_args), "parallel" if parallel_processing else "series"
        ))
    util.process_jobs(
        decompile_animation, all_job_args,
        process_count=None if parallel_processing else 1
        )


def atree_to_animation_caches(atree, node_names, cache_type=None):
    anim_cache_class = (
        AnimationCache.get_cache_class_from_cache_type(cache_type)
        if cache_type in c.ANIMATION_CACHE_EXTENSIONS else
        Ps2AnimationCache
        )

    atree_data      = atree.atree_header.atree_data
    prefix          = atree.atree_header.prefix.upper()
    comp_angles     = tuple(atree_data.compressed_data.comp_angles)
    comp_positions  = tuple(atree_data.compressed_data.comp_positions)
    comp_scales     = tuple(atree_data.compressed_data.comp_scales)

    anim_caches     = [None] * len(atree_data.atree_sequences)
    for i, sequence in enumerate(atree_data.atree_sequences):
        anim_caches[i] = anim_cache = anim_cache_class()

        anim_cache.prefix           = prefix
        anim_cache.name             = sequence.name.upper()
        anim_cache.frame_count      = sequence.frame_count
        anim_cache.frame_rate       = sequence.frame_rate
        anim_cache.comp_angles      = comp_angles
        anim_cache.comp_positions   = comp_positions
        anim_cache.comp_scales      = comp_scales

    for i, anode_info in enumerate(atree_data.anode_infos):
        init_pos    = tuple(anode_info.init_pos)
        node_type   = anode_info.anim_type.enum_name
        parent      = anode_info.parent_index

        seq_infos   = anode_info.anim_seq_infos
        for j, anim_cache in enumerate(anim_caches):
            anim_node = AnimationCacheNode()
            anim_cache.nodes += (anim_node, )

            anim_node.name      = node_names[i]
            anim_node.parent    = parent
            anim_node.init_pos  = init_pos

            if node_type == "skeletal" and j not in range(len(seq_infos)):
                print("Warning: skeletal node missing sequence info. Changing to null.")
                node_type = "null"

            anim_node.type_name = node_type
            if node_type == "skeletal":
                seq_info                    = seq_infos[j]
                frame_data                  = seq_info.frame_data
                anim_node.flags             = seq_info.type.data
                anim_node.frame_flags       = frame_data.frame_header_flags
                anim_node.initial_keyframe  = frame_data.initial_frame_data
                anim_node.keyframe_data     = (
                    frame_data.comp_frame_data if anim_node.compressed else
                    frame_data.uncomp_frame_data
                    )

    #for anim_cache in anim_caches:
    #    anim_cache.reduce_compressed_data()

    return anim_caches


def atree_to_obj_anim_caches(atree, node_names):
    atree_data      = atree.atree_header.atree_data
    prefix          = atree.atree_header.prefix.upper().strip()

    obj_anims       = tuple(atree_data.obj_anim_header.obj_anims)
    all_sequences   = [
        dict(
            name        = seq.name.upper().strip(),
            frame_count = seq.frame_count,
            frame_rate  = seq.frame_rate,
            )
        for seq in atree_data.atree_sequences
        ]

    anim_caches = []
    for anode_info in atree_data.anode_infos:
        if anode_info.anim_type.enum_name != "object":
            continue

        init_pos    = tuple(anode_info.init_pos)
        seq_index   = anode_info.anim_seq_info_index
        node_name   = anode_info.mb_desc.upper().strip()
        for i, sequence in enumerate(all_sequences):
            # NOTE: for object animations being extracted to a non-cache
            #       format, we convert it into a series of nodes, one for
            #       each frame. the scale of each node is set to 0, except
            #       on the frame that model is supposed to be visible.
            try:
                obj_anim = obj_anims[i + seq_index]
            except Exception:
                print("Warning: Could not get object animation for "
                      f"node '{node_name}' in actor '{prefix}'.")
                continue

            anim_cache = Ps2AnimationCache()
            # TODO: make utility functions for generating identifier names like this
            anim_cache.name         = f"{node_name}_{sequence['name']}"
            anim_cache.frame_count  = sequence['frame_count']
            anim_cache.frame_rate   = sequence['frame_rate']

            # NOTE: abusing things a bit by adding new properties to the
            #       class, which are being consumed in the loop below
            anim_cache.obj_frame_count  = obj_anim.frame_count
            anim_cache.obj_start_frame  = obj_anim.start_frame
            anim_cache.init_pos         = init_pos

            anim_caches.append(anim_cache)

    # generate animations for object anims
    for anim_cache in anim_caches:
        anim_cache.nodes = util.generate_obj_anim_nodes(
            anim_cache.obj_frame_count, AnimationCacheNode, anim_cache.name
            )
        # shift the root bone to where the obj anim node is
        anim_cache.nodes[0].init_pos = anim_cache.init_pos
        for i, node in enumerate(anim_cache.nodes[1:]):
            frame_index     = i + obj_anim.start_frame
            frame_count     = anim_cache.frame_count
            keyframe_data   = [-1, -1, -1] * frame_count # -1.0 to subtract scale to 0.0
            frame_flags     = [0xFF]*((frame_count+7)//8)

            keyframe_data[frame_index*3: (frame_index+1)*3] = (0, 0, 0)
            if frame_count % 8:
                frame_flags[-1] = (1<<(frame_count%8))-1

            node.scale_x = node.scale_y = node.scale_z = True
            node.frame_flags    = frame_flags
            node.keyframe_data  = keyframe_data

    return anim_caches
