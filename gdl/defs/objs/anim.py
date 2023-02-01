from .tag import GdlTag

class AnimTag(GdlTag):

    @property
    def actor_names(self):
        return tuple(sorted(
            atree.name.upper().strip() for atree in self.data.atrees
            ))
