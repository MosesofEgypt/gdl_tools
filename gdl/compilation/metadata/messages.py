import os

from traceback import format_exc
from . import constants as c
from . import util


def compile_messages_metadata(data_dir):
    all_assets = util.locate_metadata(data_dir)
    all_metadata = dict(
        fonts=set(),
        messages=dict(),
        message_lists=dict(),
        )

    for metadata_name in sorted(all_assets):
        asset_filepath = all_assets[metadata_name]
        try:
            metadata = util.load_metadata(asset_filepath)
            message_lists = metadata.get("message_lists", ())
            messages = metadata.get("messages", ())
            for name in sorted(message_lists):
                message_list = message_lists[name]
                name = name.upper().strip()
                if name in all_metadata["message_lists"]:
                    print(f"Skipping duplicate message list '{name}' in '{asset_filepath}'")
                else:
                    all_metadata["message_lists"][name] = message_list

            for name in sorted(messages):
                message = messages[name]
                name = name.upper().strip()
                if name in all_metadata["messages"]:
                    print(f"Skipping duplicate message '{name}' in '{asset_filepath}'")
                elif "font_name" not in message:
                    print(f"Skipping message '{name}' missing a font_name in '{asset_filepath}'")
                else:
                    all_metadata["messages"][name] = message
                    all_metadata["fonts"].add(message["font_name"])

        except Exception:
            print(format_exc())
            print(f"Could not load metadata file '{asset_filepath}'")

    all_metadata["fonts"] = tuple(sorted(all_metadata["fonts"]))  # force ordered
    return all_metadata


def decompile_messages_metadata(
        messages_tag, data_dir,
        asset_types=c.METADATA_ASSET_EXTENSIONS[0], overwrite=False
        ):
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    for asset_type in asset_types:
        if asset_type not in c.METADATA_ASSET_EXTENSIONS:
            raise ValueError("Unknown metadata type '%s'" % asset_type)

    os.makedirs(data_dir, exist_ok=True)
    metadata = dict(
        # fonts isn't necessary since they're specified per message
        #fonts=messages_tag.get_fonts(),
        messages=messages_tag.get_messages(),
        message_lists=messages_tag.get_message_lists(),
        )
    for message in metadata["messages"].values():
        if message.get("scale") == 1.0:
            del message["scale"]
        if message.get("sscale") == 1.0:
            del message["sscale"]

    for asset_type in asset_types:
        filepath = os.path.join(data_dir, "messages.%s" % asset_type)
        util.dump_metadata(metadata, filepath, overwrite)
