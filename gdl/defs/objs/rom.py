from .wad import WadTag


class RomTag(WadTag):
    def _get_names_to_indices(self, names_or_indices=None,
                              want_message_list_names=False):
        all_names = (
            self.get_message_list_names() if want_message_list_names else
            self.get_message_names()
            )
        if names_or_indices is None:
            names_or_indices = tuple(range(len(all_names)))

        names_to_index = {}
        for val in names_or_indices:
            try:
                if isinstance(val, str):
                    idx  = all_names.index(val.upper())
                    name = val
                else:
                    idx  = val
                    name = all_names[val].upper()

                names_to_index[name] = idx
            except ValueError:
                pass

        return names_to_index

    def _get_strings(self, data_type, offsets_type):
        data_lump    = self.get_lump_of_type(data_type)
        offsets_lump = self.get_lump_of_type(offsets_type)

        data = data_lump[0] if data_lump else ''
        offsets = offsets_lump

        if offsets is None or offsets_type.lower() in ("loff", "toff"):
            offsets = offsets[0] if offsets else ()

        strings = []
        for start in offsets:
            end = data.find("\x00", start)
            strings.append(data[start: end])

        return strings

    def _add_strings(self, strings, data_type, offsets_type):
        data_lump    = self.get_or_add_lump_of_type(data_type)
        offsets_lump = self.get_or_add_lump_of_type(offsets_type)

        if not data_lump:
            data_lump.append()

        offsets = offsets_lump
        if offsets_type.lower() in ("loff", "toff"):
            if not offsets:
                offsets.append()

            offsets = offsets[0]

        for string in strings:
            offsets.append(len(data_lump[0]))
            data_lump[0] += string.strip("\x00") + "\x00"

    def get_fonts(self):
        fonts_lump = self.get_or_add_lump_of_type('font')
        # TODO: figure out if the font names should be uppercased
        return tuple(f.description for f in fonts_lump)

    def get_message_strings(self):
        return self._get_strings('text', 'toff')

    def get_message_names(self):
        return self._get_strings('defs', 'sdef')

    def get_message_list_names(self):
        return self._get_strings('defs', 'ldef')

    def get_messages(self, names_or_indices=None):
        fonts_lump    = self.get_lump_of_type('font')
        messages_lump = self.get_lump_of_type('strs')
        message_strings = self.get_message_strings()

        messages = {}
        names_to_indices = self._get_names_to_indices(names_or_indices, False)
        for name, i in names_to_indices.items():
            msg = messages_lump[i]
            if msg.font_id not in range(len(fonts_lump)):
                raise ValueError(
                    "font_id %s outside font array length of %s" %
                    (msg.font_id, len(fonts_lump))
                    )

            messages[name] = dict(
                font_name = fonts_lump[msg.font_id].description,
                scale   = msg.scale,
                sscale  = msg.sscale,
                strings = tuple(
                    s for s in message_strings[msg.first: msg.first + msg.num]
                    )
                )

        return messages

    def get_message_lists(self, names_or_indices=None):
        message_lists = {}
        message_names  = self.get_message_names()

        messages_lists_lump         = self.get_lump_of_type('list')
        message_list_indices_lump = self.get_lump_of_type('loff')
        if not messages_lists_lump or not message_list_indices_lump:
            return message_lists

        message_list_indices = message_list_indices_lump[0]
        names_to_indices = self._get_names_to_indices(names_or_indices, True)
        for name, i in names_to_indices.items():
            message_lists[name] = []

            lst = messages_lists_lump[i]
            for j in range(lst.first, lst.first + lst.num):
                message_name = message_names[message_list_indices[j]]
                message_lists[name].append(message_name)

        return message_lists

    def add_fonts(self, fonts):
        fonts_lump = self.get_or_add_lump_of_type('font')
        for font in fonts:
            fonts_lump.append()
            fonts_lump[-1].description = font
            fonts_lump[-1].font_id = len(fonts_lump) - 1

    def add_messages(self, messages):
        messages_lump     = self.get_or_add_lump_of_type('strs')
        text_offsets_lump = self.get_or_add_lump_of_type('toff')
        if not text_offsets_lump:
            text_offsets_lump.append()

        text_offsets = text_offsets_lump[0]
        font_ids_by_name = self.get_fonts()
        default_font = sorted(font_ids_by_name)[0] if font_ids_by_name else "unnamed"

        for name in sorted(messages.keys()):
            message = messages[name]
            font_name = message.get("font_name", default_font)
            if font_name not in font_ids_by_name:
                self.add_font(font_name)
                font_ids_by_name = self.get_fonts()

            strings_to_add = message.get("strings", ())

            messages_lump.append()
            messages_lump[-1].scale  = message.get("scale", 1.0)
            messages_lump[-1].sscale = message.get("sscale", 1.0)
            messages_lump[-1].num    = len(strings_to_add)
            messages_lump[-1].first  = len(text_offsets)

            self._add_strings(strings_to_add, 'text', 'toff')
            self._add_strings([name], 'defs', 'sdef')

    def add_message_lists(self, message_lists):
        message_names               = self.get_message_names()
        messages_lists_lump         = self.get_or_add_lump_of_type('list')
        message_list_indices_lump = self.get_or_add_lump_of_type('loff')
        if not message_list_indices_lump:
            message_list_indices_lump.append()

        message_list_indices = message_list_indices_lump[0]
        message_names_to_indices = self._get_names_to_indices(None, False)

        for list_name in sorted(message_lists.keys()):
            message_names = message_lists[list_name]

            messages_lists_lump.append()
            messages_lists_lump[-1].num   = len(message_names)
            messages_lists_lump[-1].first = len(message_list_indices)
            for msg_name in message_names:
                if msg_name not in message_names_to_indices:
                    raise ValueError(
                        "Cannot locate message '%s' to add to list." % msg_name
                        )
                message_list_indices.append(message_names_to_indices[msg_name])

            self._add_strings([list_name], 'defs', 'ldef')
