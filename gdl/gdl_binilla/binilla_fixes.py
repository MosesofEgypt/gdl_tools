from binilla.widgets.binilla_widget import BinillaWidget
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


orig_fix_filedialog_style = BinillaWidget.fix_filedialog_style
def fixed_fix_filedialog_style(self):
    try:
        orig_fix_filedialog_style(self)
    except AttributeError:
        pass

# NOTE: this is a hack to prevent crashing on linux. the reason for the
#       crash is complicated, but it can be boiled down to LegendViewer
#       using a BinillaWidget, without itself being a BinillaWidget.
#       Poor programming on younger me's part
BinillaWidget.fix_filedialog_style = fixed_fix_filedialog_style
