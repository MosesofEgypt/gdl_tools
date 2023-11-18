import array
import hashlib
import pathlib
import urllib

from math import sqrt

from .stripify import Stripifier
from .model_cache import ModelCache, Ps2ModelCache, XboxModelCache,\
     GamecubeModelCache, DreamcastModelCache, ArcadeModelCache
from . import model_vif
from . import constants as c


class G3DModel():

    def __init__(self, optimize_for_ps2=False, optimize_for_ngc=False,
                 optimize_for_xbox=False):
        self.stripifier = Stripifier()
        self.stripifier.degen_link = False
        self.stripifier.max_strip_len = (
            c.PS2_MAX_STRIP_LEN if optimize_for_ps2 else
            c.NGC_MAX_STRIP_LEN if optimize_for_ngc else
            c.XBOX_MAX_STRIP_LEN if optimize_for_xbox else
            c.RETAIL_MAX_STRIP_LEN
            )

        #set up the instance variables
        self.clear()

    def clear(self):
        # Stores the unorganized verts, norms, and uvs
        self.verts  = []
        self.norms  = []
        self.uvs    = []
        self.lm_uvs = []
        self.colors = []

        self.lod_ks   = {c.DEFAULT_INDEX_KEY: c.DEFAULT_MOD_LOD_K}
        self.tri_lists = {c.DEFAULT_INDEX_KEY: []}
        
        self.all_dont_draws   = {}
        self.all_vert_maxs    = {}
        self.all_uv_shifts    = {}
        self.all_lm_uv_shifts = {}
        self.all_uv_maxs      = {}

        self.bounding_radius = 0.0

    def make_strips(self):
        # load the triangles into the stripifier, calculate
        # strips, and link them together as best as possible
        self.stripifier.load_mesh(self.tri_lists)
        self.stripifier.make_strips()
        self.stripifier.link_strips()

        vert_data  = self.stripifier.vert_data
        all_strips = self.stripifier.all_strips

        self.all_dont_draws   = {idx_key: [] for idx_key in all_strips}
        self.all_vert_maxs    = {idx_key: [] for idx_key in all_strips}
        self.all_uv_maxs      = {idx_key: [] for idx_key in all_strips}
        self.all_uv_shifts    = {idx_key: [] for idx_key in all_strips}
        self.all_lm_uv_shifts = {idx_key: [] for idx_key in all_strips}

        # calculate the max vert and uv sizes for each strip
        # and calculate the dont_draws from the all_degens lists
        for idx_key, strips in all_strips.items():
            degens = self.stripifier.all_degens[idx_key]

            #loop over each strip
            for i in range(len(strips)):

                # flag all degen tris and as not drawn
                d_draw = [0] * len(strips[i])
                self.all_dont_draws[idx_key].append(d_draw)

                # first 2 are never rendered cause theres not 3 verts yet.
                for d in (0, 1, *degens[i]):
                    d_draw[d] = 1

                uv_max_x    = uv_max_y    = vert_max = 0
                uv_min_x    = uv_min_y    = 0xffFFffFF
                lm_uv_min_x = lm_uv_min_y = 0xffFFffFF
                #calcualte the vert and uv maxs
                for v_i in strips[i]:
                    vert = vert_data[v_i]
                    pos_index, uv_index = vert[:2]

                    #get the largest axis values for this verts position and uvs
                    vert_max = max(
                        max(self.verts[pos_index]),
                        -min(self.verts[pos_index]),
                        vert_max
                        )
                    if self.uvs:
                        uv_min_x    = min(self.uvs[uv_index][0], uv_min_x)
                        uv_max_x    = max(self.uvs[uv_index][0], uv_max_x)
                        uv_min_y    = min(self.uvs[uv_index][1], uv_min_y)
                        uv_max_y    = max(self.uvs[uv_index][1], uv_max_y)

                    if self.lm_uvs:
                        lm_uv_min_x = min(self.lm_uvs[uv_index][0], lm_uv_min_x)
                        lm_uv_min_y = min(self.lm_uvs[uv_index][1], lm_uv_min_y)

                # uv_shift is expected to be negative, as we add it to
                # the uvs to shift them to the [0, 1] uv range
                # NOTE: converting to int to only shift whole canvas steps
                uv_shift_x    = -int(uv_min_x)
                uv_shift_y    = -int(uv_min_y)
                lm_uv_shift_x = -int(lm_uv_min_x)
                lm_uv_shift_y = -int(lm_uv_min_y)

                self.all_uv_shifts[idx_key].append((uv_shift_x, uv_shift_y))
                self.all_lm_uv_shifts[idx_key].append((lm_uv_shift_x, lm_uv_shift_y))
                self.all_vert_maxs[idx_key].append(vert_max)
                self.all_uv_maxs[idx_key].append(max(
                    uv_max_x + uv_shift_x,
                    uv_max_y + uv_shift_y
                    ))

    def import_obj(self, input_lines):
        # when importing an obj, we have to clear the existing data
        self.clear()

        # default tex_name to use if one isnt given
        tex_name = c.DEFAULT_TEX_NAME
        lm_name  = c.DEFAULT_LM_NAME
        idx_key  = c.DEFAULT_INDEX_KEY

        bounding_radius_square = 0.0
        tris = self.tri_lists[idx_key]

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
                    self.lod_ks[idx_key] = int(line[6:])
                elif line.startswith('$lm_name'):
                    lm_name = urllib.parse.unquote(line[9:].strip().upper())
                    idx_key = (tex_name, lm_name)
                elif line.startswith("lmvt"):
                    line = [v.strip() for v in line[5:].split(' ') if v]
                    u, v = float(line[0]), 1 - float(line[1])
                    self.lm_uvs.append([u, v])
                elif line.startswith("vc"):
                    line = [v.strip() for v in line[3:].split(' ') if v]
                    r, g, b, a = float(line[0]), float(line[1]), float(line[2]), float(line[3])
                    self.colors.append([
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
                if idx_key not in self.tri_lists:
                    self.tri_lists[idx_key] = []
                    self.lod_ks.setdefault(idx_key, c.DEFAULT_MOD_LOD_K)
                tris = self.tri_lists[idx_key]
            elif line[0:2] == 'vt':
                line = [v.strip() for v in line[2:].split(' ') if v]
                u, v = float(line[0]), 1 - float(line[1])
                self.uvs.append([u, v])
            elif line[0:2] == 'vn':
                line = [v.strip() for v in line[2:].split(' ') if v]
                # x-axis is reversed
                xn, yn, zn = -float(line[0]), float(line[1]), float(line[2])
                mag = sqrt(xn**2 + yn**2 + zn**2)
                if mag == 0:
                    mag = 1.0

                self.norms.append([
                    max(min(xn/mag, 1.0), -1.0),
                    max(min(yn/mag, 1.0), -1.0),
                    max(min(zn/mag, 1.0), -1.0)
                    ])
            elif line[0] == 'v':
                line = [v.strip() for v in line[1:].split(' ') if v]
                # x-axis is reversed
                x, y, z = -float(line[0]), float(line[1]), float(line[2])
                self.verts.append([x, y, z])
                bounding_radius_square = max(x**2 + y**2 + z**2, bounding_radius_square)
            elif line[0] == 'f':
                line = [v.strip() for v in line[1:].split(' ') if v]
                v0   = tuple(int(i)-1 for i in line[0].split('/'))
                v1   = tuple(int(i)-1 for i in line[1].split('/'))
                v2   = tuple(int(i)-1 for i in line[2].split('/'))
                # TODO: Update this to handle the indices not being the same
                tris.append((v0[0], v1[0], v2[0]))

        self.bounding_radius = sqrt(bounding_radius_square)

        # if no untextured triangles exist, remove the entries
        if len(self.tri_lists.get(c.DEFAULT_INDEX_KEY, [None])) == 0:
            del self.tri_lists[c.DEFAULT_INDEX_KEY]

    def export_obj(self, output_filepath, texture_assets={}, swap_lightmap_and_diffuse=False):
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
        if swap_lightmap_and_diffuse and self.lm_uvs and self.uvs:
            obj_str += '\n#lightmap_diffuse_swapped'
            uv_template, lmuv_template = lmuv_template, uv_template

        obj_str += '\n\n'
        obj_str += '\n'.join((
            'v %.7f %.7f %.7f' % (-v[0], v[1], v[2]) for v in self.verts
            ))
        obj_str += '\n'
        obj_str += '\n'.join((
            'vn %.7f %.7f %.7f' % (-n[0], n[1], n[2]) for n in self.norms
            ))
        obj_str += '\n'
        obj_str += '\n'.join((
            uv_template % (uv[0], 1 - uv[1]) for uv in self.uvs
            ))
        obj_str += '\n'
        obj_str += '\n'.join((
            lmuv_template % (lm_uv[0], 1 - lm_uv[1]) for lm_uv in self.lm_uvs
            ))
        obj_str += '\n'
        obj_str += '\n'.join((
            '#vc %.7f %.7f %.7f %.7f' % tuple(color[:4]) for color in self.colors
            ))
        obj_str += '\n'

        seen_bitmaps = set()
        for idx_key in sorted(self.tri_lists):
            if not self.tri_lists[idx_key]:
                continue

            for bitmap_name in idx_key:
                bitmap_name = bitmap_name.upper()
                bitmap_filepath = texture_assets.get(bitmap_name)
                if bitmap_name in seen_bitmaps:
                    continue
                elif not bitmap_filepath:
                    # TODO: write a shared function to handle this naming
                    for suffix in ("00", ".0001", ".0002"):
                        temp_name = bitmap_name + suffix
                        if temp_name in texture_assets:
                            bitmap_filepath = texture_assets[temp_name]
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
        uv_and_norm = bool(self.uvs and self.norms)
        norm_only   = bool(self.norms)
        uv_only     = bool(self.uvs)
        for idx_key in sorted(self.tri_lists):
            tris = self.tri_lists[idx_key]
            if not tris:
                continue

            tex_name, lm_name = idx_key
            lod_k = self.lod_ks.get(idx_key, c.DEFAULT_MOD_LOD_K)
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

    def import_g3d(self, model_cache):
        self.clear()
        if isinstance(model_cache, Ps2ModelCache):
            for geom in model_cache.geoms:
                idx_key  = (geom["tex_name"].upper(),
                            geom["lm_name"].upper())
                parsed_data = model_vif.import_vif_to_g3d(
                    geom["vif_rawdata"], start_vert=len(self.verts),
                    )

                # if nothing was imported, remove the triangles
                if len(parsed_data["tris"]) == 0:
                    continue

                self.tri_lists.setdefault(idx_key, []).extend(parsed_data["tris"])
                self.lod_ks[idx_key] = geom.get("lod_k", c.DEFAULT_MOD_LOD_K)
                self.verts.extend(parsed_data["verts"])
                self.norms.extend(parsed_data["norms"])
                self.colors.extend(parsed_data["colors"])
                self.uvs.extend(parsed_data["uvs"])
                self.lm_uvs.extend(parsed_data["lm_uvs"])

                self.bounding_radius = max(parsed_data["bounding_radius"], self.bounding_radius)
        elif isinstance(model_cache, DreamcastModelCache):
            lm_name = model_cache.lightmap_name.upper()
            vdata_float = array.array("f", model_cache.verts_rawdata)
            vdata_int16 = array.array("h", model_cache.verts_rawdata)
            tdata_int16 = array.array("H", model_cache.tris_rawdata)
            ndata_float = array.array("f", model_cache.norms_rawdata)

            if not model_cache.verts_rawdata:
                # temporary hack till compressed verts are understood
                del tdata_int16[:]

            self.verts      = [
                tuple(vdata_float[i:i+3])
                for i in range(0, len(vdata_float), 6)
                ]
            if model_cache.has_lmap:
                self.uvs   = [
                    (vdata_int16[i]/1024, vdata_int16[i+1]/1024)
                    for i in range(6, len(vdata_int16), 12)
                    ]
                self.lm_uvs = [
                    (vdata_int16[i]/1024, vdata_int16[i+1]/1024)
                    for i in range(8, len(vdata_int16), 12)
                    ]
                # TODO: determine if normals are stored in the last 4 bytes of the
                #       vertex data as a compressed ijk_11_11_10 triple
            else:
                self.uvs    = [
                    (vdata_float[i]/1024, vdata_float[i+1]/1024)
                    for i in range(0, len(vdata_float), 6)
                    ]
                self.norms  = [
                    tuple(ndata_float[i:i+3])
                    for i in range(0, len(ndata_float), 3)
                    ]

            flip            = False
            stripped        = True# False
            get_tri_list    = self.tri_lists.setdefault
            get_tex_name    = {
                i: n.upper() for i, n in
                enumerate(model_cache.texture_names)
                }.get
            # TODO: figure this out the rest of the way(determine purpose of bit14)
            for i, tri_tex_idx in enumerate(tdata_int16[3::4]):
                tex_idx         = tri_tex_idx & 0x3FFF
                strip_bits      = tri_tex_idx >> 14
                cont_strip      = strip_bits & 2
                #toggle_stripped = strip_bits & 1
                idx_key         = (get_tex_name(tex_idx, c.DEFAULT_TEX_NAME), lm_name)
                tris            = get_tri_list(idx_key, [])

                #if toggle_stripped:
                #    stripped = not stripped

                v0, v1, v2 = tdata_int16[i*4: i*4+3]
                if not stripped:
                    flip = not flip

                tris.append(
                    (v0, v2, v1) if flip else
                    (v0, v1, v2)
                    )

                if stripped:
                    flip = (not flip) if cont_strip else False
        else:
            raise NotImplementedError()

    def compile_g3d(self, cache_type):
        texture_names = set()
        for tex_name, lm_name in self.stripifier.all_strips:
            texture_names.update((tex_name.upper(), lm_name.upper()))

        model_cache = ModelCache.get_cache_class_from_cache_type(cache_type)()
        if isinstance(model_cache, Ps2ModelCache):
            self.make_strips()

            # loop over each subobject
            for idx_key in self.stripifier.all_strips.keys():
                vif_data = model_vif.export_g3d_to_vif(self, idx_key)

                model_cache.vert_count += vif_data.pop("vert_count", 0)
                model_cache.tri_count  += vif_data.pop("tri_count",  0)
                model_cache.geoms.append(vif_data)

            model_cache.is_fifo2 = False
        elif isinstance(model_cache, DreamcastModelCache):
            raise NotImplementedError()
        elif isinstance(model_cache, ArcadeModelCache):
            raise NotImplementedError()
        else:
            raise ValueError(f"Unexpected cache type '{cache_type}'")

        model_cache.bounding_radius = self.bounding_radius
        model_cache.texture_names   = list(sorted(texture_names))
        
        model_cache.has_normals = bool(self.norms)
        model_cache.has_colors  = bool(self.colors)
        model_cache.has_lmap    = bool(self.lm_uvs)

        return model_cache
