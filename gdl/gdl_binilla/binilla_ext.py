from binilla.widgets.field_widgets.container_frame import ContainerFrame


def fixed_container_load_child_node_data(self):
    '''
    fixed variant that adds a try/catch around sub_node retrieval
    '''
    desc = self.desc
    sub_node = None
    for wid in self.f_widgets:
        # try and load any existing FieldWidgets with appropriate node data
        w = self.f_widgets[wid]
        attr_index = self.f_widget_ids_map_inv.get(wid)
        if attr_index is None:
            return True
        elif self.node:
            try:
                sub_node = self.node[attr_index]
            except Exception:
                pass

        if w.load_node_data(self.node, sub_node, attr_index):
            # descriptor is different. gotta repopulate self
            return True

    return False

ContainerFrame.load_child_node_data = fixed_container_load_child_node_data
