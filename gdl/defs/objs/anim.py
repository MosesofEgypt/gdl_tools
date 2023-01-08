from .tag import GdlTag

class AnimTag(GdlTag):
    _node_name_map = None

    def get_model_node_name_map(self, actor_name, recache=False):
        if self._node_name_map is None or recache:
            self._node_name_map = {}
            for atree in self.data.atrees:
                model_names = []
                node_names  = []
                for anode in atree.atree_header.atree_data.anode_infos:
                    if not anode.flags.no_object_def:
                        model_names.append(atree.atree_header.prefix + anode.mb_desc)
                        node_names.append(anode.mb_desc)

                self._node_name_map[atree.name.upper().strip()] = (
                    tuple(model_names), tuple(node_names)
                    )

        return self._node_name_map.get(
            actor_name.upper().strip(), ((), ())
            )

    @property
    def actor_names(self):
        if self._node_name_map is None:
            self.get_model_node_name_map("", recache=True)

        return tuple(sorted(self._node_name_map.keys()))
