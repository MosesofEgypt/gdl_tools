import hashlib
import os
import urllib

from math import sqrt

from .stripify import Stripifier
from . import model_vif
from . import constants as c


class G3DModel():

    source_file_hash = b'\x00'*16

    def __init__(self, target_ps2=False, target_ngc=False, target_xbox=False):
        self.stripifier = Stripifier()
        self.stripifier.degen_link = False
        self.stripifier.max_strip_len = (
            c.PS2_MAX_STRIP_LEN if target_ps2 else
            c.NGC_MAX_STRIP_LEN if target_ngc else
            c.XBOX_MAX_STRIP_LEN if target_xbox else
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

        self.bnd_rad = 0.0

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

    def import_obj(self, input_lines, source_file_hash=b'\x00'*16):
        # when importing an obj, we have to clear the existing data 
        self.clear()

        # default tex_name to use if one isnt given
        tex_name = c.DEFAULT_TEX_NAME
        lm_name  = c.DEFAULT_LM_NAME
        idx_key  = c.DEFAULT_INDEX_KEY

        bnd_rad_square = 0.0
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
                bnd_rad_square = max(x**2 + y**2 + z**2, bnd_rad_square)
            elif line[0] == 'f':
                line = [v.strip() for v in line[1:].split(' ') if v]
                tris.append((tuple(int(i)-1 for i in line[0].split('/')),
                             tuple(int(i)-1 for i in line[1].split('/')),
                             tuple(int(i)-1 for i in line[2].split('/'))))

        self.bnd_rad = sqrt(bnd_rad_square)
        self.source_file_hash = source_file_hash

        # if no untextured triangles exist, remove the entries
        if len(self.tri_lists.get(c.DEFAULT_INDEX_KEY, [None])) == 0:
            del self.tri_lists[c.DEFAULT_INDEX_KEY]

    def export_obj(self, output_filepath, texture_assets={}, swap_lightmap_and_diffuse=False):
        obj_dirname = os.path.dirname(output_filepath)
        mtl_filename = urllib.parse.quote(os.path.basename(output_filepath))

        mtl_filename = "mtl/%s.mtl" % os.path.splitext(mtl_filename)[0]
        mtl_filepath = os.path.join(obj_dirname, mtl_filename)

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
                    for suffix in ("00", ".00001", ".00002"):
                        temp_name = bitmap_name + suffix
                        if temp_name in texture_assets:
                            bitmap_filepath = texture_assets[temp_name]
                            break

                if not bitmap_filepath:
                    continue

                mtl_str += '\n'.join((
                    '',
                    'newmtl %s' % urllib.parse.quote(bitmap_name),
                    'map_Kd %s' % bitmap_filepath.replace("\\", "/"),
                    ))
                seen_bitmaps.add(bitmap_name)

        # collect all all tris, verts, uvw, normals, and texture indexes
        i = 0
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
                tri = tuple(i+1 for i in tri)  # obj indices are ones based
                if len(tri) == 3:
                    obj_str += 'f %s %s %s\n' % tri
                elif len(tri) == 6:
                    obj_str += 'f %s/%s %s/%s %s/%s\n' % tri
                elif len(tri) == 9:
                    obj_str += 'f %s/%s/%s %s/%s/%s %s/%s/%s\n' % tri
                else:
                    raise ValueError("Expected either 3, 6, or 9 items in tri, not %s" % len(tri))

        mtl_bytes = mtl_str.encode()
        obj_bytes = obj_str.encode()

        os.makedirs(os.path.dirname(mtl_filepath), exist_ok=True)
        with open(mtl_filepath, 'wb+') as out_file:
            out_file.write(mtl_bytes)

        with open(output_filepath, 'wb+') as out_file:
            out_file.write(obj_bytes)

        digester = hashlib.md5(obj_bytes)
        self.source_file_hash = digester.digest()

    def import_g3d(
            self, input_buffer, headerless=False, stream_len=-1, **kwargs
            ):
        return model_vif.import_vif_to_g3d(
            self, input_buffer, headerless, stream_len, **kwargs
            )

    def export_g3d(self, output_buffer, headerless=False, **kwargs):
        return model_vif.export_g3d_to_vif(
            self, output_buffer, headerless, **kwargs
            )
