# EXPERIMENTAL!!! borrowing halo ce animation
# format if the reclaimer module is available

from . import constants as c

halo_anim = None
if c.JMM_SUPPORT:
    from reclaimer.animation import jma as halo_anim


def import_jmm_to_g3d(animation_cache):
    if halo_anim is None:
        raise NotImplementedError(
            "Could not locate reclaimer animation module. Cannot import jmm."
            )
    raise NotImplementedError("Write this")


def export_g3d_to_jmm(g3d_animation):
    if halo_anim is None:
        raise NotImplementedError(
            "Could not locate reclaimer animation module. Cannot export jmm."
            )
    raise NotImplementedError("Write this")
