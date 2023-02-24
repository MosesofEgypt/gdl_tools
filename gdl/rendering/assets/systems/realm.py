
class RealmLevel:
    _name  = ""
    _title = ""
    _boss_type = ""
    _enemy_type_boss      = ""
    _enemy_type_golem     = ""
    _enemy_type_general   = ""
    _enemy_type_gargoyle  = ""
    _enemy_type_aux       = ""
    _enemy_type_gen_small = ""
    _enemy_type_gen_large = ""
    _enemy_types_special  = ()

    def __init__(self, **kwargs):
        self._name  = kwargs.pop("name",  self._name).upper().strip()
        self._title = kwargs.pop("title", self._title).upper().strip()
        self._enemy_type_boss      = kwargs.pop("enemy_type_boss",      self._enemy_type_boss).upper().strip()
        self._enemy_type_golem     = kwargs.pop("enemy_type_golem",     self._enemy_type_golem).upper().strip()
        self._enemy_type_general   = kwargs.pop("enemy_type_general",   self._enemy_type_general).upper().strip()
        self._enemy_type_gargoyle  = kwargs.pop("enemy_type_gargoyle",  self._enemy_type_gargoyle).upper().strip()
        self._enemy_type_aux       = kwargs.pop("enemy_type_aux",       self._enemy_type_aux).upper().strip()
        self._enemy_type_gen_small = kwargs.pop("enemy_type_gen_small", self._enemy_type_gen_small).upper().strip()
        self._enemy_type_gen_large = kwargs.pop("enemy_type_gen_large", self._enemy_type_gen_large).upper().strip()
        self._enemy_types_special  = tuple(kwargs.pop("enemy_types_special",  self._enemy_types_special))

    @property
    def name(self): return self._name
    @property
    def title(self): return self._title
    @property
    def boss_type(self): return self._boss_type
    @property
    def enemy_type_boss(self): return self._enemy_type_boss
    @property
    def enemy_type_golem(self): return self._enemy_type_golem
    @property
    def enemy_type_general(self): return self._enemy_type_general
    @property
    def enemy_type_gargoyle(self): return self._enemy_type_gargoyle
    @property
    def enemy_type_aux(self): return self._enemy_type_aux
    @property
    def enemy_type_gen_small(self): return self._enemy_type_gen_small
    @property
    def enemy_type_gen_large(self): return self._enemy_type_gen_large
    @property
    def enemy_types_special(self): return self._enemy_types_special


class Realm:
    _name = ""
    _type = ""
    _levels = ()

    def __init__(self, **kwargs):
        self._name  = kwargs.pop("name", self._name).upper().strip()
        self._type  = kwargs.pop("type", self._type).upper().strip()
        self._levels = tuple(kwargs.pop("levels", self._levels))
        for level in self.levels:
            if not isinstance(level, RealmLevel):
                raise TypeError(
                    f"level must be of type RealmLevel, not {type(level)}"
                    )

    @property
    def name(self): return self._name
    @property
    def type(self): return self._type
    @property
    def levels(self): return self._levels
