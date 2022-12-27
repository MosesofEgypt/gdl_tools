from ..assets.model import Model, Geometry
from ...compilation.g3d.serialization.model import G3DModel


def load_model_from_objects_tag(objects_tag, model_name):
    model_name = model_name.upper().strip()
    obj_index = -1

    for b in objects_tag.data.object_defs:
        if b.name.upper().strip() == model_name and b.obj_index > -1:
            obj_index = b.obj_index
            break

    if obj_index < 0:
        return

    _, bitmap_names = objects_tag.get_cache_names()
    obj = objects_tag.data.objects[obj_index]

    flags    = getattr(obj, "flags", None)
    subobjs  = getattr(obj.data, "sub_objects", ())
    has_lmap = getattr(flags, "lmap", False)

    datas = [ m.data for m in obj.data.sub_object_models ]
    tex_names = [
        bitmap_names.get(h.tex_index, {}).get('name')
        for h in (obj.sub_object_0, *subobjs)
        ]
    lmap_names = [
        bitmap_names.get(h.lm_index, {}).get('name') if has_lmap else ""
        for h in (obj.sub_object_0, *subobjs)
        ]

    g3d_model = G3DModel()
    for data, tex_name, lmap_name in zip(datas, tex_names, lmap_names):
        g3d_model.import_g3d(
            data, tex_name=tex_name, lmap_name=lmap_name, headerless=True,
            )

    
    # TODO: finish this
