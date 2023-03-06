from ..assets.particle_system import ParticleSystem


def load_particle_system_from_block(name_prefix, psys_block):
    def config_loader(peffect):
        # TODO: configure peffect with psys_block settings
        pass

    return ParticleSystem(
        name=name_prefix + psys_block.id.enum_name,
        config_loader=config_loader
        )


def load_particle_systems_from_worlds_tag(worlds_tag, world_name=""):
    psys_by_name = {}
    name_prefix = world_name.upper() + "PSYS"
    for psys_block in worlds_tag.data.particle_systems:
        psys = load_particle_system_from_block(name_prefix, psys_block)
        if psys.name in psys_by_name:
            print(f"Warning: Duplicate particle system '{psys.name}' detected. Skipping.")
        else:
            psys_by_name[psys.name] = psys

    return psys_by_name


def load_particle_systems_from_animations_tag(anim_tag, resource_name=""):
    psys_by_index = []
    name_prefix = resource_name.upper() + "PSYS"
    try:
        psys_array = list(anim_tag.data.particle_systems)
    except TypeError:
        psys_array = []

    for psys_block in psys_array:
        psys = load_particle_system_from_block(name_prefix, psys_block)
        psys_by_index.append(psys)

    return psys_by_index
