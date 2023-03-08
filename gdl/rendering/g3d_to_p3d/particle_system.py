from direct.particles import Particles
from ..assets.particle_system import ParticleSystem


DEFAULT_TEXTURE_NAME = "AAAWHITE"


def load_particle_system_from_block(name_prefix, psys_block, textures):
    enables = psys_block.enables
    
    texname = psys_block.p_texname if enables.p_texname else None
    psys_flags = {
        n: bool(psys_block.flags[n])
        for n in psys_block.flags.NAME_MAP
        if psys_block.flag_enables[n]
        }
    psys_data = dict(
        preset    = (psys_block.preset.enum_name if enables.preset else None),
        p_color   = tuple(tuple((v / 255) for v in color) for color in psys_block.p_color),
        p_rgb     = bool(enables.p_rgb),
        p_alpha   = bool(enables.p_alpha),
        texture   = textures.get(texname, textures.get(DEFAULT_TEXTURE_NAME))
    )
    psys_data.update({
        name: psys_block[name]
        for name in ("maxp", "maxdir", "maxpos", "e_angle", "e_rate_rand",
                     "p_gravity", "p_drag", "p_speed", "p_texcnt", "e_delay")
        if enables[name]
        })
    psys_data.update({
        name: tuple(psys_block[name])
        for name in ("e_life", "p_life", "e_dir", "e_vol", "e_rate", "p_width")
        if enables[name]
        })

    def config_loader(peffect, flags=psys_flags, data=psys_data):
        #peffect.loadConfig("test.ptf")
        #texture = data["texture"].p3d_texture
        #peffect.getParticlesList()[0].renderer.setTexture(texture)
        return

        # TODO: configure peffect with psys_block settings
        peffect.reset()
        peffect.setPos(0.000, 0.000, 0.000)
        peffect.setHpr(0.000, 0.000, 0.000)
        peffect.setScale(1.000, 1.000, 1.000)

        for i in range(4 if "e_rate" in data else 1):
            part = Particles.Particles(f'p{i}')
            # Particles parameters
            part.setFactory("factory")
            part.setRenderer("renderer")
            part.setEmitter("emitter")
            fact, rend, emit = part.factory, part.renderer, part.emitter

            # Factory parameters

            # Renderer parameters

            # Emitter parameters

            peffect.addParticles(part)

    return ParticleSystem(
        name=name_prefix + psys_block.id.enum_name,
        config_loader=config_loader, unique_instances=False,
        )


def load_particle_systems_from_worlds_tag(worlds_tag, world_name="", textures=()):
    if not textures:
        textures = {}

    psys_by_name = {}
    name_prefix = world_name.upper() + "PSYS"
    for psys_block in worlds_tag.data.particle_systems:
        psys = load_particle_system_from_block(name_prefix, psys_block, textures)
        if psys.name in psys_by_name:
            print(f"Warning: Duplicate particle system '{psys.name}' detected. Skipping.")
        else:
            psys_by_name[psys.name] = psys

    return psys_by_name


def load_particle_systems_from_animations_tag(anim_tag, resource_name="", textures=()):
    if not textures:
        textures = {}

    psys_by_index = []
    name_prefix = resource_name.upper() + "PSYS"
    try:
        psys_array = list(anim_tag.data.particle_systems)
    except TypeError:
        psys_array = []

    for psys_block in psys_array:
        psys = load_particle_system_from_block(name_prefix, psys_block, textures)
        psys_by_index.append(psys)

    return psys_by_index
