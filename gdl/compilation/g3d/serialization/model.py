from .stripify import Stripifier
from .model_cache import ModelCache, Ps2ModelCache, XboxModelCache,\
     GamecubeModelCache, DreamcastModelCache, ArcadeModelCache, RawModelCache
from . import model_obj
from . import model_raw
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

    def import_asset(self, filepath):
        asset_type = filepath.suffix.strip(".").lower()
        self.clear()

        if asset_type == "obj":
            with open(filepath, "r") as f:
                model_obj.import_obj(self, f)
        else:
            raise NotImplementedError(f"Unknown asset type '{asset_type}'")

    def export_asset(self, filepath, texture_assets):
        asset_type = filepath.suffix.strip(".").lower()
        if asset_type == "obj":
            model_obj.export_obj(self, filepath, texture_assets)
        else:
            raise NotImplementedError(f"Unknown asset type '{asset_type}'")

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
                self.verts.extend(parsed_data["verts"])
                self.norms.extend(parsed_data["norms"])
                self.colors.extend(parsed_data["colors"])
                self.uvs.extend(parsed_data["uvs"])
                self.lm_uvs.extend(parsed_data["lm_uvs"])

                self.bounding_radius = max(parsed_data["bounding_radius"], self.bounding_radius)
        elif isinstance(model_cache, RawModelCache):
            if getattr(model_cache, "fifo_rawdata", None):
                raise NotImplementedError()
            else:
                parsed_data = model_raw.import_raw_to_g3d(
                    model_cache, start_vert=len(self.verts)
                    )

            for idx_key, tris in parsed_data["tri_lists"].items():
                self.tri_lists.setdefault(idx_key, []).extend(tris)

            self.verts.extend(parsed_data["verts"])
            self.norms.extend(parsed_data["norms"])
            self.colors.extend(parsed_data["colors"])
            self.uvs.extend(parsed_data["uvs"])
            self.lm_uvs.extend(parsed_data["lm_uvs"])

            self.bounding_radius = max(parsed_data["bounding_radius"], self.bounding_radius)
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
