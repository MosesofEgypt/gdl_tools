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

            fonts         = metadata.get("fonts", ())
            messages      = metadata.get("messages", ())
            message_lists = metadata.get("message_lists", ())

            font_scales  = {n: fonts[n].get("scale", 1.0)  for n in fonts}
            font_sscales = {n: fonts[n].get("sscale", 1.0) for n in fonts}

            new_fonts = []
            new_messages = dict()
            new_message_lists = dict()

            for font_name in sorted(fonts):
                if font_name not in new_fonts:
                    new_fonts.append(font_name)

            for name in sorted(message_lists):
                message_list = message_lists[name]
                name = name.upper().strip()
                if name in all_metadata["message_lists"]:
                    print(f"Skipping duplicate message list '{name}' in '{asset_filepath}'")
                else:
                    all_metadata["message_lists"][name] = message_list

            for name in sorted(messages):
                message = messages[name]
                font_name = message.get("font_name")
                name = name.upper().strip()
                if name in all_metadata["messages"]:
                    print(f"Skipping duplicate message '{name}' in '{asset_filepath}'")
                elif not font_name:
                    print(f"Skipping message '{name}' missing a font_name in '{asset_filepath}'")
                elif font_name not in new_fonts:
                    print(f"Skipping message '{name}' using unknown font '{font_name}' in '{asset_filepath}'")
                else:
                    message.setdefault("scale", 1.0)
                    message.setdefault("sscale", 1.0)
                    message["scale"]  *= font_scales.get(font_name, 1.0)
                    message["sscale"] *= font_sscales.get(font_name, 1.0)
                    all_metadata["messages"][name] = message

            all_metadata["fonts"].update(new_fonts)
            all_metadata["messages"].update(new_messages)
            all_metadata["message_lists"].update(new_message_lists)
        except Exception:
            print(format_exc())
            print(f"Could not load metadata file '{asset_filepath}'")

    all_metadata["fonts"] = tuple(sorted(all_metadata["fonts"]))  # force ordered
    return all_metadata


def decompile_messages_metadata(
        messages_tag, data_dir,
        asset_types=c.METADATA_ASSET_EXTENSIONS[0],
        overwrite=False, individual_meta=True
        ):
    if isinstance(asset_types, str):
        asset_types = (asset_types, )

    os.makedirs(data_dir, exist_ok=True)
    metadata = dict(
        fonts=dict(),
        messages=messages_tag.get_messages(),
        message_lists=messages_tag.get_message_lists(),
        )
    for font_name in messages_tag.get_fonts():
        metadata["fonts"][font_name] = dict(
            scale  = 1.0,
            sscale = 1.0
            )

    for message in metadata["messages"].values():
        if message.get("scale") == 1.0:
            del message["scale"]
        if message.get("sscale") == 1.0:
            del message["sscale"]

    metadata_groups = dict(messages=metadata)
    popped_messages = dict()
    if individual_meta:
        message_lists = metadata.pop("message_lists", ())
        for list_name in sorted(message_lists):
            fonts = {}
            messages = {}
            src_messages = metadata_groups["messages"]["messages"]
            metadata_groups[list_name] = dict(
                fonts=fonts,
                messages=messages,
                message_lists={ list_name: message_lists[list_name] },
                )

            for message_name in message_lists[list_name]:
                message = src_messages.pop(message_name, popped_messages.get(message_name, dict()))
                popped_messages[message_name] = message

                if not message:
                    print(f"Warning: Message list references non-existant message '{message_name}'.")
                else:
                    messages[message_name] = message
                    font_name = message.get("font_name")
                    if font_name not in fonts:
                        fonts[font_name] = metadata["fonts"][font_name]

    for group_name in metadata_groups:
        metadata = metadata_groups[group_name]
        for asset_type in asset_types:
            filepath = os.path.join(data_dir, "%s.%s" % (group_name, asset_type))
            util.dump_metadata(metadata, filepath, overwrite)
