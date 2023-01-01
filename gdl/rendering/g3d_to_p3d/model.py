from panda3d.core import ModelNode, GeomNode, Geom,\
     GeomTriangles, GeomVertexData, GeomVertexWriter,\
     GeomVertexArrayFormat, GeomVertexFormat

from ..assets.shader import GeometryShader
from ..assets.model import Model, Geometry
from ...compilation.g3d.serialization.model import G3DModel


def _register_g3d_vertex_format():
    if "G3DVertexFormat" in globals():
        return G3DVertexFormat

    array = GeomVertexArrayFormat()
    array.addColumn("vertex", 3, Geom.NTFloat32, Geom.CPoint)
    array.addColumn("normal", 3, Geom.NTFloat32, Geom.CNormal)
    array.addColumn("color", 3, Geom.NTFloat32, Geom.CColor)
    array.addColumn("texcoord", 2, Geom.NTFloat32, Geom.CTexcoord)
    array.addColumn("texcoord.lm", 2, Geom.NTFloat32, Geom.CTexcoord)

    vformat = GeomVertexFormat()
    vformat.addArray(array)
    return GeomVertexFormat.registerFormat(vformat)


def load_geom_from_g3d_model(g3d_model, geom_shader):
    vdata = GeomVertexData('', G3DVertexFormat, Geom.UHDynamic)
    vdata.setNumRows(len(g3d_model.verts))

    verts  = GeomVertexWriter(vdata, 'vertex')
    norms  = GeomVertexWriter(vdata, 'normal')
    uvs    = GeomVertexWriter(vdata, 'texcoord')
    lmuvs  = GeomVertexWriter(vdata, 'texcoord.lm')
    colors = GeomVertexWriter(vdata, 'color')

    for x, y, z in g3d_model.verts:
        # rotate coordinates
        verts.addData3f(x, z, y)

    for i, j, k in g3d_model.norms:
        norms.addData3f(i, k, j)

    for r, g, b, a in g3d_model.colors:
        colors.addData4f(r, g, b, a)

    # NOTE: uvs will be 3 component for DEMO level items
    for uv in g3d_model.uvs:
        uvs.addData2f(uv[0], 1.0 - uv[1])

    for s, t in g3d_model.lm_uvs:
        lmuvs.addData2f(s, 1.0 - t)

    tris = GeomTriangles(Geom.UHDynamic)
    for tri_list in g3d_model.tri_lists.values():
        for tri in tri_list:
            tris.addVertices(tri[0], tri[3], tri[6])

    p3d_geometry = GeomNode("")
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    p3d_geometry.addGeom(geom)

    return Geometry(
        p3d_geometry=p3d_geometry, shader=geom_shader,
        )


def load_model_from_objects_tag(objects_tag, model_name, textures=()):
    if not textures:
        textures = {}

    model_name = model_name.upper().strip()
    _, bitmap_name_by_index = objects_tag.get_cache_names()
    object_indices_by_name, _ = objects_tag.get_cache_names(by_name=True)
    obj_index = object_indices_by_name.get(model_name, {}).get("index", -1)

    flags = None
    if obj_index >= 0:
        obj = objects_tag.data.objects[obj_index]

        flags    = getattr(obj, "flags", None)
        subobjs  = getattr(obj.data, "sub_objects", ())
        has_lmap = getattr(flags, "lmap", False)
        bnd_rad  = obj.bnd_rad

        datas = [ m.data for m in obj.data.sub_object_models ]
        tex_names = [
            bitmap_name_by_index.get(h.tex_index, {}).get('name')
            for h in (obj.sub_object_0, *subobjs)
            ]
        lm_names = [
            bitmap_name_by_index.get(h.lm_index, {}).get('name') if has_lmap else ""
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
        geom_shader = GeometryShader(
            diff_texture=textures.get(tex_name),
            lm_texture=textures.get(lm_name)
            )
        geom_shader.sharp      = getattr(flags, "sharp", False)
        geom_shader.blur       = getattr(flags, "blur", False)
        geom_shader.chrome     = getattr(flags, "chrome", False)
        geom_shader.alpha      = getattr(flags, "alpha", False)
        geom_shader.sort       = getattr(flags, "sort", False)
        geom_shader.sort_alpha = getattr(flags, "sort_a", False)

        model.add_geometry(load_geom_from_g3d_model(g3d_model, geom_shader))

    return model


G3DVertexFormat = _register_g3d_vertex_format()
