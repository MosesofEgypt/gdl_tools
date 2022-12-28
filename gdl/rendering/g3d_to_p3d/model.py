from panda3d.core import ModelNode, GeomNode, Geom,\
     GeomTriangles, GeomVertexWriter, GeomVertexFormat, GeomVertexData

from ..assets.model import Model, Geometry
from ...compilation.g3d.serialization.model import G3DModel


def load_geom_from_g3d_model(g3d_model):
    geometry = Geometry(
        p3d_geometry=GeomNode("")
        )
    vformat = GeomVertexFormat.getV3n3cpt2()
    vdata = GeomVertexData('', vformat, Geom.UHDynamic)
    vdata.setNumRows(len(g3d_model.verts))

    verts  = GeomVertexWriter(vdata, 'vertex')
    norms  = GeomVertexWriter(vdata, 'normal')
    uvs    = GeomVertexWriter(vdata, 'texcoord')

    for x, y, z in g3d_model.verts:
        # rotate coordinates
        verts.addData3f(x, z, y)

    for i, j, k in g3d_model.norms:
        norms.addData3f(i, k, j)

    for u, v in g3d_model.uvs:
        uvs.addData2f(u, v)

    if g3d_model.colors:
        colors = GeomVertexWriter(vdata, 'color')
        for r, g, b, a in g3d_model.colors:
            colors.addData4f(r, g, b, a)

    if g3d_model.lm_uvs:
        lmuvs = GeomVertexWriter(vdata, 'texcoord')
        for s, t in g3d_model.lm_uvs:
            lmuvs.addData2f(s, t)

    tris = GeomTriangles(Geom.UHDynamic)
    for tri_list in g3d_model.tri_lists.values():
        for tri in tri_list:
            tris.addVertices(tri[0], tri[3], tri[6])

    geom = Geom(vdata)
    geom.addPrimitive(tris)

    geometry.p3d_geometry.addGeom(geom)
    return geometry


def load_model_from_objects_tag(
        objects_tag, model_name, textures_filepath=None
        ):
    model_name = model_name.upper().strip()
    obj_index = -1

    for b in objects_tag.data.object_defs:
        if b.name.upper().strip() == model_name and b.obj_index > -1:
            obj_index = b.obj_index
            break

    if obj_index >= 0:
        _, bitmap_names = objects_tag.get_cache_names()
        obj = objects_tag.data.objects[obj_index]

        flags    = getattr(obj, "flags", None)
        subobjs  = getattr(obj.data, "sub_objects", ())
        has_lmap = getattr(flags, "lmap", False)
        bnd_rad  = obj.bnd_rad

        datas = [ m.data for m in obj.data.sub_object_models ]
        tex_names = [
            bitmap_names.get(h.tex_index, {}).get('name')
            for h in (obj.sub_object_0, *subobjs)
            ]
        lm_names = [
            bitmap_names.get(h.lm_index, {}).get('name') if has_lmap else ""
            for h in (obj.sub_object_0, *subobjs)
            ]
    else:
        bnd_rad = 0
        datas = tex_names = lm_names = ()

    model = Model(
        name=model_name,
        p3d_model=ModelNode(model_name),
        bounding_radius=bnd_rad
        )
    for data, tex_name, lm_name in zip(datas, tex_names, lm_names):
        g3d_model = G3DModel()
        g3d_model.import_g3d(
            data, tex_name=tex_name, lm_name=lm_name, headerless=True,
            )
        model.add_geometry(load_geom_from_g3d_model(g3d_model))

    return model
