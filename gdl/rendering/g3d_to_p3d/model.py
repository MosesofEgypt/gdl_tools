from panda3d.core import ModelNode, GeomNode, Geom,\
     GeomTriangles, GeomVertexData, GeomVertexWriter,\
     GeomVertexArrayFormat, GeomVertexFormat

from ..assets.shader import GeometryShader
from ..assets.model import Model, ObjectAnimModel, Geometry
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

    vertsAddData  = GeomVertexWriter(vdata, 'vertex').addData3f
    normsAddData  = GeomVertexWriter(vdata, 'normal').addData3f
    uvsAddData    = GeomVertexWriter(vdata, 'texcoord').addData2f
    lmuvsAddData  = GeomVertexWriter(vdata, 'texcoord.lm').addData2f
    colorsAddData = GeomVertexWriter(vdata, 'color').addData4f

    tris = GeomTriangles(Geom.UHDynamic)
    addVertices   = tris.addVertices

    for x, y, z in g3d_model.verts:
        # rotate coordinates
        vertsAddData(x, z, y)

    for i, j, k in g3d_model.norms:
        normsAddData(i, k, j)

    for r, g, b, a in g3d_model.colors:
        colorsAddData(r, g, b, a)

    # NOTE: uvs will be 3 component for DEMO level items
    for uv in g3d_model.uvs:
        uvsAddData(uv[0], 1.0 - uv[1])

    for s, t in g3d_model.lm_uvs:
        lmuvsAddData(s, 1.0 - t)

    for tri_list in g3d_model.tri_lists.values():
        for tri in tri_list:
            addVertices(tri[0], tri[3], tri[6])

    p3d_geometry = GeomNode("")
    geom = Geom(vdata)
    geom.addPrimitive(tris)
    p3d_geometry.addGeom(geom)

    return Geometry(
        p3d_geometry=p3d_geometry, shader=geom_shader,
        )


def load_model_from_objects_tag(objects_tag, model_name, textures=(),
                                global_tex_anims=(), seq_tex_anims=(),
                                shape_morph_anims=(), p3d_model=None,
                                is_static=False, is_obj_anim=False):
    if not textures:
        textures = {}

    model_name = model_name.upper().strip()
    _, bitmap_name_by_index = objects_tag.get_cache_names()
    object_indices_by_name, _ = objects_tag.get_cache_names(by_name=True)
    obj_index = object_indices_by_name.get(model_name, {}).get("index", -1)

    flags = None
    if is_obj_anim or obj_index < 0:
        bnd_rad = 0
        datas = tex_names = lm_names = ()
    else:
        obj = objects_tag.data.objects[obj_index]

        flags    = getattr(obj, "flags", None)
        subobjs  = (obj.sub_object_0, *getattr(obj.data, "sub_objects", ()))
        has_lmap = getattr(flags, "lmap", False)
        bnd_rad  = obj.bnd_rad

        datas = [ m.data for m in obj.data.sub_object_models ]
        tex_names = [
            bitmap_name_by_index.get(h.tex_index, {}).get('name')
            for h in subobjs
            ]
        lm_names = [
            bitmap_name_by_index.get(h.lm_index, {}).get('name') if has_lmap else ""
            for h in subobjs
            ]

    model_class = ObjectAnimModel if is_obj_anim else Model
    model = model_class(
        name=model_name, p3d_model=p3d_model, bounding_radius=bnd_rad
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

        geometry = load_geom_from_g3d_model(g3d_model, geom_shader)
        model.add_geometry(geometry)
        if tex_name in global_tex_anims:
            global_tex_anims[tex_name].bind(geometry)
            is_static = False

        if tex_name in seq_tex_anims:
            for tex_anim in seq_tex_anims[tex_name]:
                tex_anim.bind(geometry)
                is_static = False

    if is_obj_anim and model_name in shape_morph_anims:
        for shape_morph_anim in shape_morph_anims[model_name]:
            shape_morph_anim.bind(model)
            is_static = False

    if is_static:
        model.p3d_model.set_preserve_transform(ModelNode.PT_drop_node)
    else:
        model.p3d_model.set_preserve_transform(ModelNode.PT_no_touch)

    return model


G3DVertexFormat = _register_g3d_vertex_format()
