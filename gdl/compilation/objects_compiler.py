import pathlib

from .g3d import cache as cache_comp
from .g3d import constants as c

class ObjectsCompiler:
    target_dir = "."

    build_ngc_files = True
    build_ps2_files = True
    build_xbox_files = True
    build_arcade_files = False
    build_dreamcast_files = False

    parallel_processing = False

    optimize_models      = True
    optimize_textures    = True
    force_recompile      = False
    swap_lightmap_and_diffuse = False  # debug feature

    overwrite = False
    individual_meta = True

    serialize_cache_files = True
    build_texdef_cache = True
    
    def __init__(self, **kwargs):
        # simple initialization setup where kwargs are
        # copied into the attributes of this new class
        for k, v in kwargs.items():
            setattr(self, k, v)

    def compile_animations(self):
        asset_dir = pathlib.Path(self.target_dir, c.DATA_FOLDERNAME)
        if not asset_dir.is_dir():
            return
        elif not(self.build_ngc_files or self.build_ps2_files or
                 self.build_xbox_files or self.build_arcade_files or
                 self.build_dreamcast_files):
            return

        kwargs = dict(
            parallel_processing=self.parallel_processing,
            force_recompile=self.force_recompile,
            )
        if self.build_ps2_files:
            cache_comp.compile_animations(asset_dir, target_ps2=True, **kwargs)

        if self.build_ngc_files:
            cache_comp.compile_animations(asset_dir, target_ngc=True, **kwargs)

        if self.build_xbox_files:
            cache_comp.compile_animations(asset_dir, target_xbox=True, **kwargs)

        if self.build_arcade_files:
            cache_comp.compile_animations(asset_dir, target_arcade=True, **kwargs)

        if self.build_dreamcast_files:
            cache_comp.compile_animations(asset_dir, target_dreamcast=True, **kwargs)

    def compile_textures(self):
        asset_dir = pathlib.Path(self.target_dir, c.DATA_FOLDERNAME)
        if not asset_dir.is_dir():
            return
        elif not(self.build_ngc_files or self.build_ps2_files or
                 self.build_xbox_files or self.build_arcade_files or
                 self.build_dreamcast_files):
            return

        kwargs = dict(
            parallel_processing=self.parallel_processing,
            force_recompile=self.force_recompile,
            optimize_format=self.optimize_textures,
            )
        if self.build_ps2_files:
            cache_comp.compile_textures(asset_dir, target_ps2=True, **kwargs)

        if self.build_ngc_files:
            cache_comp.compile_textures(asset_dir, target_ngc=True, **kwargs)

        if self.build_xbox_files:
            cache_comp.compile_textures(asset_dir, target_xbox=True, **kwargs)

        if self.build_arcade_files:
            cache_comp.compile_textures(asset_dir, target_arcade=True, **kwargs)

        if self.build_dreamcast_files:
            cache_comp.compile_textures(asset_dir, target_dreamcast=True, **kwargs)

    def compile_models(self):
        asset_dir = pathlib.Path(self.target_dir, c.DATA_FOLDERNAME)
        if not asset_dir.is_dir():
            return
        elif not(self.build_ngc_files or self.build_ps2_files or
                 self.build_xbox_files or self.build_arcade_files or
                 self.build_dreamcast_files):
            return

        kwargs = dict(
            force_recompile=self.force_recompile,
            parallel_processing=self.parallel_processing,
            optimize_strips=self.optimize_models,
            )
        if self.build_ps2_files:
            cache_comp.compile_models(asset_dir, target_ps2=True, **kwargs)

        if self.build_ngc_files:
            cache_comp.compile_models(asset_dir, target_ngc=True, **kwargs)

        if self.build_xbox_files:
            cache_comp.compile_models(asset_dir, target_xbox=True, **kwargs)

        if self.build_arcade_files:
            cache_comp.compile_models(asset_dir, target_arcade=True, **kwargs)

        if self.build_dreamcast_files:
            cache_comp.compile_models(asset_dir, target_dreamcast=True, **kwargs)

    def compile(self):
        if not pathlib.Path(self.target_dir).is_dir():
            return
        elif not(self.build_ngc_files or self.build_ps2_files or
                 self.build_xbox_files or self.build_arcade_files):
            return

        comp_kwargs = []
        if self.build_ps2_files:
            comp_kwargs.append(dict(name="PS2",  target_ps2=True))

        if self.build_ngc_files:
            comp_kwargs.append(dict(name="NGC",  target_ngc=True))

        if self.build_xbox_files:
            comp_kwargs.append(dict(name="XBOX", target_xbox=True))

        if self.build_arcade_files:
            comp_kwargs.append(dict(name="ARC", target_arcade=True))

        if self.build_dreamcast_files:
            comp_kwargs.append(dict(name="DC", target_dreamcast=True))

        compilation_outputs = dict()
        for kwargs in comp_kwargs:
            name = kwargs.pop("name")
            compilation_outputs[name] = cache_comp.compile_cache_files(
                self.target_dir, **kwargs,
                serialize_cache_files=self.serialize_cache_files,
                build_texdef_cache=(self.build_texdef_cache and name == "PS2")
                )

        return compilation_outputs

    def decompile(self, **kwargs):
        kwargs.setdefault("overwrite", self.overwrite)
        kwargs.setdefault("individual_meta", self.individual_meta)
        kwargs.setdefault("parallel_processing", self.parallel_processing)
        kwargs.setdefault("swap_lightmap_and_diffuse", self.swap_lightmap_and_diffuse)

        cache_comp.decompile_cache_files(self.target_dir, **kwargs)
