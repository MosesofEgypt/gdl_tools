from binilla.widgets.field_widget_picker import *
from binilla.widgets.field_widgets import *
from ..field_types import *

__all__ = ("WidgetPicker", "def_widget_picker", "add_widget",
           "GdlWidgetPicker", "def_gdl_widget_picker")

class GdlWidgetPicker(WidgetPicker):
    pass

def_gdl_widget_picker = dgdlwp = GdlWidgetPicker()

dgdlwp.copy_widget(LumpArray, Array)
