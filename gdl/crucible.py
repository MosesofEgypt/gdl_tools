import os

from .defs.objects import objects_ps2_def
from .compilation.g3d import model as model_comp
from .compilation.g3d import texture as texture_comp
from .compilation.g3d import cache as cache_comp
from .compilation.g3d import constants as c

class Crucible:
    target_dir = "."

    build_ngc_files = True
    build_ps2_files = True

    parallel_processing = False

    use_force_index_hack = True
    optimize_texture_format = False
    swap_lightmap_and_diffuse = False
    force_recompile = False

    overwrite = False
    individual_meta = True

    serialize_cache_files = True
    build_anim_cache = True
    build_texdef_cache = True
    
    def __init__(self, **kwargs):
        # simple initialization setup where kwargs are
        # copied into the attributes of this new class
        for k, v in kwargs.items():
            setattr(self, k, v)

    def compile_textures(self):
        asset_dir = os.path.join(self.target_dir, c.DATA_FOLDERNAME)
        for ngc, do_build in ((False, self.build_ps2_files),
                              (True, self.build_ngc_files)):
            if do_build:
                texture_comp.compile_textures(
                    asset_dir, target_ngc=ngc,
                    parallel_processing=self.parallel_processing,
                    force_recompile=self.force_recompile,
                    optimize_format=self.optimize_texture_format
                    )

    def compile_models(self):
        asset_dir = os.path.join(self.target_dir, c.DATA_FOLDERNAME)
        model_comp.compile_models(
            asset_dir, force_recompile=self.force_recompile,
            parallel_processing=self.parallel_processing,
            )

    def compile_cache(self):
        if not os.path.isdir(self.target_dir):
            return

        compilation_outputs = dict()
        for ngc, build in ((False, self.build_ps2_files),
                           (True, self.build_ngc_files)):
            comp_name = "NGC" if ngc else "PS2"
            if not build:
                continue

            compilation_outputs[comp_name] = cache_comp.compile_cache_files(
                self.target_dir, target_ngc=ngc,
                serialize_cache_files=self.serialize_cache_files,
                build_anim_cache=self.build_anim_cache,
                build_texdef_cache=self.build_texdef_cache and (not ngc),
                use_force_index_hack=self.use_force_index_hack
                )

        return compilation_outputs

    def extract_assets(self, **kwargs):
        kwargs.setdefault("overwrite", self.overwrite)
        kwargs.setdefault("individual_meta", self.individual_meta)
        kwargs.setdefault("parallel_processing", self.parallel_processing)
        kwargs.setdefault("swap_lightmap_and_diffuse", self.swap_lightmap_and_diffuse)

        ps2_filepath = os.path.join(self.target_dir,  "objects.ps2")
        ngc_filepath = os.path.join(self.target_dir,  "objects.ngc")

        if os.path.isfile(ps2_filepath):
            filepath = ps2_filepath
        elif os.path.isfile(ngc_filepath):
            filepath = ngc_filepath
        else:
            return

        objects_tag = objects_ps2_def.build(filepath=filepath)

        try:
            objects_tag.load_texdef_names()
        except Exception:
            print('Could not load texdefs. Names generated will be best guesses.')

        cache_comp.decompile_cache_files(objects_tag, **kwargs)
