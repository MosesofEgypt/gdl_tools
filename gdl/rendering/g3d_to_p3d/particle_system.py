import math
import panda3d

from ..assets import particle_system

DEFAULT_TEX_NAME = "000GRID"


def load_particle_system_from_block(name_prefix, psys_block, textures, tex_anims):
    texname = psys_block.part_texname if psys_block.enables.part_texname else None

    if texname in tex_anims:
        texture = None
    else:
        default_texture = textures.get(DEFAULT_TEX_NAME)
        texture = (
            default_texture if texname is None else
            textures.get(texname, default_texture)
            )

    emit_lives = (
        tuple(max(0, v) for v in psys_block.emit_life)
        if psys_block.enables.emit_life else
        (particle_system.DEFAULT_EMITTER_LIFE, particle_system.DEFAULT_EMITTER_LIFE)
        )
    particle_lives = (
        tuple(max(0, v) for v in psys_block.part_life)
        if psys_block.enables.part_life else
        (particle_system.DEFAULT_PARTICLE_LIFE, particle_system.DEFAULT_PARTICLE_LIFE)
        )

    psys_data = dict(
        texture        = texture,
        max_particles  = psys_block.max_particles if psys_block.enables.max_particles else 10000,
        emit_range     = psys_block.emit_angle    if psys_block.enables.emit_angle    else 0,
        emit_delay     = psys_block.emit_delay    if psys_block.enables.emit_delay    else 0, # TODO: determine purpose
        part_gravity   = psys_block.part_gravity  if psys_block.enables.part_gravity  else 0,
        part_speed     = psys_block.part_speed    if psys_block.enables.part_speed    else 0,
        emit_lives     = emit_lives,
        particle_lives = particle_lives,
        emit_dir = (
            psys_block.emit_dir[0],
            psys_block.emit_dir[2],
            psys_block.emit_dir[1]
            ) if psys_block.enables.emit_dir else (0.0, 0.0, 1.0),
        emit_vol = (
            psys_block.emit_vol[0],
            psys_block.emit_vol[2],
            psys_block.emit_vol[1]
            ) if psys_block.enables.emit_vol else (0.0, 0.0, 0.0),
        flags = {
            n: bool(psys_block.flags[n] and psys_block.flag_enables[n])
            for n in (
                "gravity", "sort", "no_tex_rgb", "no_tex_a",
                "fb_add", "fb_mul", "no_z_test", "no_z_write"
                )
            }
        )

    for phase in "ab":
        psys_data[phase] = dict()
        rates  = psys_block[f"emit_rate_{phase}"]
        widths = psys_block[f"part_width_{phase}"]
        colors = psys_block[f"part_color_{phase}"]

        for point in ("in", "out"):
            b, g, r, a = colors[point]

            if not psys_block.enables.part_rgb:   b = g = r = 255
            if not psys_block.enables.part_alpha: a = 255

            psys_data[f"{phase}_{point}_rate"]  = rates[point]  if psys_block.enables.emit_rate  else particle_system.DEFAULT_EMIT_RATE
            psys_data[f"{phase}_{point}_width"] = widths[point] if psys_block.enables.part_width else particle_system.DEFAULT_PARTICLE_WIDTH
            psys_data[f"{phase}_{point}_color"] = (r/255, g/255, b/255, a/255)

    psys = particle_system.ParticleSystemFactory(
        name=name_prefix + psys_block.id.enum_name, **psys_data
        )
    if texname in tex_anims:
        tex_anims[texname].psys_bind(psys)

    return psys


def load_particle_systems_from_worlds_tag(
        worlds_tag, world_name="", textures=(), tex_anims=(),
        ):
    if not textures:  textures  = {}
    if not tex_anims: tex_anims = {}

    psys_by_name = {}
    name_prefix = world_name.upper() + "PSYS"
    for psys_block in worlds_tag.data.particle_systems:
        psys = load_particle_system_from_block(
            name_prefix, psys_block, textures, tex_anims
            )
        if psys.name in psys_by_name:
            print(f"Warning: Duplicate particle system '{psys.name}' detected. Skipping.")
        else:
            psys_by_name[psys.name] = psys

    return psys_by_name


def load_particle_systems_from_animations_tag(
        anim_tag, resource_name="", textures=(), tex_anims=(),
        ):
    if not textures:  textures  = {}
    if not tex_anims: tex_anims = {}

    psys_by_index = []
    name_prefix = resource_name.upper() + "PSYS"
    try:
        psys_array = list(anim_tag.data.particle_systems)
    except TypeError:
        psys_array = []

    for psys_block in psys_array:
        psys = load_particle_system_from_block(
            name_prefix, psys_block, textures, tex_anims
            )
        psys_by_index.append(psys)

    return psys_by_index
