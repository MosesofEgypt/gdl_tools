import os
import json
import yaml

from traceback import format_exc

from ..g3d.compilation import constants as c
from ..g3d.compilation import util
from ..g3d.compilation.metadata import *


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
        fonts=messages_tag.get_fonts(),
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
        if os.path.isfile(filepath) and not overwrite:
            continue
        elif asset_type in ("yaml", "yml"):
            with open(filepath, 'w') as f:
                yaml.safe_dump(metadata, f)
        elif asset_type in ("json"):
            with open(filepath, 'w') as f:
                json(metadata, f, sort_keys=True, indent=2)
