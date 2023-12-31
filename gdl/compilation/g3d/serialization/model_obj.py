import pathlib
import urllib

from math import sqrt
from . import constants as c


def import_obj(model_cache, input_lines):
    # default tex_name to use if one isnt given
    tex_name = c.DEFAULT_TEX_NAME
    lm_name  = c.DEFAULT_LM_NAME
    idx_key  = c.DEFAULT_INDEX_KEY

    bounding_radius_square = 0.0
    tris = model_cache.tri_lists[idx_key]

    # collect all all tris, verts, uvw, normals, and texture indexes
    for line in input_lines:
        line = line.strip()
        
        if not len(line):
            continue
        elif line[0] == 'g':
            # dont need to worry about groups
            continue
        elif line[0] == '#':
            # this is either a comment, or an extra piece of data
            line = line[1:].strip()
            if line.startswith('$lod_k'):
                model_cache.lod_ks[idx_key] = int(line[6:])
            elif line.startswith('$lm_name'):
                lm_name = urllib.parse.unquote(line[9:].strip().upper())
                idx_key = (tex_name, lm_name)
            elif line.startswith("lmvt"):
                line = [v.strip() for v in line[5:].split(' ') if v]
                u, v = float(line[0]), 1 - float(line[1])
                model_cache.lm_uvs.append([u, v])
            elif line.startswith("vc"):
                line = [v.strip() for v in line[3:].split(' ') if v]
                r, g, b, a = float(line[0]), float(line[1]), float(line[2]), float(line[3])
                model_cache.colors.append([
                    max(min(r, 1.0), 0.0),
                    max(min(g, 1.0), 0.0),
                    max(min(b, 1.0), 0.0),
                    max(min(a, 1.0), 0.0)
                    ])
        elif line[:6] == 'usemtl':
            tex_name = urllib.parse.unquote(line[6:].strip().upper())

            idx_key = (tex_name, lm_name)
            # make a new triangle block if one for
            # this material doesnt already exist
            if idx_key not in model_cache.tri_lists:
                model_cache.tri_lists[idx_key] = []
                model_cache.lod_ks.setdefault(idx_key, c.DEFAULT_MOD_LOD_K)
            tris = model_cache.tri_lists[idx_key]
        elif line[0:2] == 'vt':
            line = [v.strip() for v in line[2:].split(' ') if v]
            u, v = float(line[0]), 1 - float(line[1])
            model_cache.uvs.append([u, v])
        elif line[0:2] == 'vn':
            line = [v.strip() for v in line[2:].split(' ') if v]
            # x-axis is reversed
            xn, yn, zn = -float(line[0]), float(line[1]), float(line[2])
            mag = sqrt(xn**2 + yn**2 + zn**2)
            if mag == 0:
                mag = 1.0

            model_cache.norms.append([
                max(min(xn/mag, 1.0), -1.0),
                max(min(yn/mag, 1.0), -1.0),
                max(min(zn/mag, 1.0), -1.0)
                ])
        elif line[0] == 'v':
            line = [v.strip() for v in line[1:].split(' ') if v]
            # x-axis is reversed
            x, y, z = -float(line[0]), float(line[1]), float(line[2])
            model_cache.verts.append([x, y, z])
            bounding_radius_square = max(x**2 + y**2 + z**2, bounding_radius_square)
        elif line[0] == 'f':
            line = [v.strip() for v in line[1:].split(' ') if v]
            v0   = tuple(int(i)-1 for i in line[0].split('/'))
            v1   = tuple(int(i)-1 for i in line[1].split('/'))
            v2   = tuple(int(i)-1 for i in line[2].split('/'))

            # TODO: Update this to handle the indices not being the same
            if set(len(set(v0)), len(set(v1)), len(set(v2))) != {1}:
                raise ValueError("Cannot import OBJ files with nonuniform vert indices.")

            tris.append((v0[0], v1[0], v2[0]))

    model_cache.bounding_radius = sqrt(bounding_radius_square)

    # if no untextured triangles exist, remove the entries
    if len(model_cache.tri_lists.get(c.DEFAULT_INDEX_KEY, [None])) == 0:
        del model_cache.tri_lists[c.DEFAULT_INDEX_KEY]


def export_obj(model_cache, output_filepath, texture_assets={}, swap_lightmap_and_diffuse=False):
    output_filepath = pathlib.Path(output_filepath)
    obj_dirname     = output_filepath.parent
    mtl_filename    = pathlib.PurePosixPath(
        "mtl", urllib.parse.quote(output_filepath.stem) + ".mtl"
        )

    mtl_filepath  = obj_dirname.joinpath(mtl_filename)

    uv_template   = "vt %.7f %.7f"
    lmuv_template = "#lmvt %.7f %.7f"

    mtl_str = '\n'.join((
        '# Gauntlet Dark Legacy material library',
        '#     Extracted by Moses',
        ))

    obj_str = '\n'.join((
        '# Gauntlet Dark Legacy 3d model',
        '#     Extracted by Moses',
        'mtllib %s' % mtl_filename
        ))
    if swap_lightmap_and_diffuse and model_cache.lm_uvs and model_cache.uvs:
        obj_str += '\n#lightmap_diffuse_swapped'
        uv_template, lmuv_template = lmuv_template, uv_template

    obj_str += '\n\n'
    obj_str += '\n'.join((
        'v %.7f %.7f %.7f' % (-v[0], v[1], v[2]) for v in model_cache.verts
        ))
    obj_str += '\n'
    obj_str += '\n'.join((
        'vn %.7f %.7f %.7f' % (-n[0], n[1], n[2]) for n in model_cache.norms
        ))
    obj_str += '\n'
    obj_str += '\n'.join((
        uv_template % (uv[0], 1 - uv[1]) for uv in model_cache.uvs
        ))
    obj_str += '\n'
    obj_str += '\n'.join((
        lmuv_template % (lm_uv[0], 1 - lm_uv[1]) for lm_uv in model_cache.lm_uvs
        ))
    obj_str += '\n'
    obj_str += '\n'.join((
        '#vc %.7f %.7f %.7f %.7f' % tuple(color[:4]) for color in model_cache.colors
        ))
    obj_str += '\n'

    seen_bitmaps = set()
    for idx_key in sorted(model_cache.tri_lists):
        if not model_cache.tri_lists[idx_key]:
            continue

        for bitmap_name in idx_key:
            bitmap_name = bitmap_name.upper()
            bitmap_filepath = texture_assets.get(bitmap_name)
            if bitmap_name in seen_bitmaps:
                continue
            elif not bitmap_filepath:
                # TODO: write a shared function to handle this naming
                for key in texture_assets:
                    if (bitmap_name and key.startswith(bitmap_name) and
                        set(key.split(bitmap_name, 1)[-1]).lstrip("._").issubset("0123456789")):
                        bitmap_filepath = texture_assets[key]
                        break

            if not bitmap_filepath:
                continue

            mtl_str += '\n'.join((
                '',
                'newmtl %s' % urllib.parse.quote(bitmap_name),
                'map_Kd %s' % bitmap_filepath.as_posix(),
                ))
            seen_bitmaps.add(bitmap_name)

    # collect all all tris, verts, uvw, normals, and texture indexes
    i = 0
    uv_and_norm = bool(model_cache.uvs and model_cache.norms)
    norm_only   = bool(model_cache.norms)
    uv_only     = bool(model_cache.uvs)
    for idx_key in sorted(model_cache.tri_lists):
        tris = model_cache.tri_lists[idx_key]
        if not tris:
            continue

        tex_name, lm_name = idx_key
        lod_k = model_cache.lod_ks.get(idx_key, c.DEFAULT_MOD_LOD_K)
        if swap_lightmap_and_diffuse:
            tex_name, lm_name = lm_name, tex_name

        obj_str += '\n'.join((
            '',
            '#$lm_name %s' % urllib.parse.quote(lm_name),
            '#$lod_k %s' % lod_k,
            'usemtl %s' % urllib.parse.quote(tex_name),
            'g %s' % i
            ))
        obj_str += '\n'
        i += 1

        # write the triangles
        for tri in tris:
            v0, v1, v2 = tuple(i+1 for i in tri)  # obj indices are ones based
            if uv_and_norm:
                obj_str += 'f %s/%s/%s %s/%s/%s %s/%s/%s\n' % (
                    v0,v0,v0, v1,v1,v1, v2,v2,v2
                    )
            elif uv_only:
                obj_str += 'f %s/%s %s/%s %s/%s\n' % (v0,v0, v1,v1, v2,v2)
            elif norm_only:
                obj_str += 'f %s//%s %s//%s %s//%s\n' % (v0,v0, v1,v1, v2,v2)
            else:
                obj_str += 'f %s %s %s\n' % (v0, v1, v2)

    mtl_bytes = mtl_str.encode()
    obj_bytes = obj_str.encode()

    mtl_filepath.parent.mkdir(parents=True, exist_ok=True)
    with mtl_filepath.open('wb+') as out_file:
        out_file.write(mtl_bytes)

    output_filepath.parent.mkdir(parents=True, exist_ok=True)
    with output_filepath.open('wb+') as out_file:
        out_file.write(obj_bytes)
