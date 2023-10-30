from panda3d.core import ModelNode, GeomNode, Geom,\
     GeomTriangles, GeomVertexData, GeomVertexWriter,\
     GeomVertexArrayFormat, GeomVertexFormat

from ..assets.shader import GeometryShader
from ..assets.model import Model, ObjectAnimModel, Geometry
from ...compilation.g3d.serialization.model import G3DModel
from ...compilation.g3d.model import object_to_model_cache, Ps2ModelCache


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


def load_geometries_from_g3d_model(
        g3d_model, textures, billboard_fixup=False, shader_flags=()
        ):
    vdata = GeomVertexData('', G3DVertexFormat, Geom.UHDynamic)
    vdata.setNumRows(len(g3d_model.verts))

    vertsAddData  = GeomVertexWriter(vdata, 'vertex').addData3f
    normsAddData  = GeomVertexWriter(vdata, 'normal').addData3f
    uvsAddData    = GeomVertexWriter(vdata, 'texcoord').addData2f
    lmuvsAddData  = GeomVertexWriter(vdata, 'texcoord.lm').addData2f
    colorsAddData = GeomVertexWriter(vdata, 'color').addData4f

    # rotate y and z coordinates. for the billboard fixup, we're
    # doing a bit of a hack. panda3d's billboard effect wants to
    # face the object away from the camera, so to rotate it 180
    # degrees we'll simply reverse the x and y axis.
    if billboard_fixup:
        for x, y, z in g3d_model.verts:
            vertsAddData(-x, -z, y)

        for i, j, k in g3d_model.norms:
            normsAddData(-i, -k, j)
    else:
        for x, y, z in g3d_model.verts:
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

    geometries = {}
    for idx_key in g3d_model.tri_lists:
        tex_name, lm_name = idx_key
        p3d_geometry = GeomNode("")
        geom         = Geom(vdata)

        tris        = GeomTriangles(Geom.UHDynamic)
        addVertices = tris.addVertices
        geom_shader = GeometryShader(
            diff_texture=textures.get(tex_name),
            lm_texture=textures.get(lm_name)
            )
        for name in shader_flags:
            setattr(geom_shader, name, shader_flags[name])

        for tri in g3d_model.tri_lists[idx_key]:
            addVertices(tri[0], tri[3], tri[6])

        geom.addPrimitive(tris)

        p3d_geometry.addGeom(geom)
        geometries[idx_key] = Geometry(
            p3d_geometry=p3d_geometry, shader=geom_shader,
            )
    return geometries


def load_model_from_objects_tag(
        objects_tag, model_name, textures=(),
        global_tex_anims=(), seq_tex_anims=(), shape_morph_anims=(),
        p3d_model=None, is_static=False, is_obj_anim=False,
        billboard_fixup=False
        ):
    if not textures:
        textures = {}

    model_name = model_name.upper().strip()
    _, bitmap_name_by_index   = objects_tag.get_cache_names()
    object_indices_by_name, _ = objects_tag.get_cache_names(by_name=True)
    obj_index = object_indices_by_name.get(model_name, {}).get("index", -1)

    g3d_model = G3DModel()
    shader_flags = {}
    if obj_index >= 0 and not is_obj_anim:
        obj     = objects_tag.data.objects[obj_index]
        flags   = getattr(obj, "flags", None)
        g3d_model.import_g3d(
            object_to_model_cache(obj, bitmap_assets=bitmap_name_by_index)
            )
        shader_flags.update(
            sharp      = getattr(flags, "sharp",  False),
            blur       = getattr(flags, "blur",   False),
            chrome     = getattr(flags, "chrome", False),
            alpha      = getattr(flags, "alpha",  False),
            sort       = getattr(flags, "sort",   False),
            sort_alpha = getattr(flags, "sort_a", False)
            )

    model = (ObjectAnimModel if is_obj_anim else Model)(
        name=model_name, p3d_model=p3d_model,
        bounding_radius=g3d_model.bounding_radius
        )
    geometries = load_geometries_from_g3d_model(
        g3d_model, textures, billboard_fixup=billboard_fixup,
        shader_flags=shader_flags
        )

    for idx_key, geometry in geometries.items():
        tex_name, lm_name = idx_key
        geometry.apply_shader()

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
