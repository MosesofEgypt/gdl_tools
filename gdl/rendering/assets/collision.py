import panda3d


class Collision:
    _name = ""
    _p3d_nodepath = None

    def __init__(self, **kwargs):
        self._name    = kwargs.pop("name", self._name).upper().strip()
        p3d_collision = kwargs.pop("p3d_collision", None)
        if p3d_collision is None:
            p3d_collision = panda3d.core.CollisionNode(self.name)

        if not isinstance(p3d_collision, panda3d.core.CollisionNode):
            raise TypeError(
                f"p3d_collision must be of type panda3d.core.CollisionNode, not {type(p3d_collision)}"
                )

        self._p3d_nodepath = panda3d.core.NodePath(p3d_collision)

    @property
    def p3d_collision(self): return self._p3d_nodepath.node()
    @property
    def p3d_nodepath(self): return self._p3d_nodepath

    @property
    def name(self): return self._name


class CollisionObject:
    _scene_object = None
    _tris = ()
    _radius_sq = 0.0

    def __init__(self, **kwargs):
        self._scene_object  = kwargs.pop("scene_object", self._scene_object)
        self._tris      = tuple(kwargs.pop("tris", self._tris))
        self._radius_sq = float(kwargs.pop("radius_sq", self._radius_sq))

    @property
    def radius_sq(self): return self._radius_sq
    @property
    def tris(self): return self._tris

    @property
    def scene_object(self): return self._scene_object
    @scene_object.setter
    def scene_object(self, scene_object):
        self._scene_object = scene_object


class CollisionObjectGrid:
    _rows = ()
    _grid_size = 1.0
    _min_x = 0
    _min_z = 0
    _width  = 0
    _height = 0

    _dyn_collision_objects = None

    def __init__(self, **kwargs):
        self._min_x     = int(kwargs.pop("min_x",  self._min_x))
        self._min_z     = int(kwargs.pop("min_z",  self._min_z))
        self._width     = int(kwargs.pop("width",  self._width))
        self._height    = int(kwargs.pop("height", self._height))
        self._grid_size = max(1, kwargs.pop("grid_size", self._grid_size))
        self._dyn_collision_objects = dict(kwargs.pop("dyn_collision_objects", {}))
        self._rows = tuple(
            tuple(
                dict() # just use a simple dict. will map world
                #        object names to CollisionObject instances
                for x in range(self._width)
                )
            for z in range(self._height)
            )

    def grid_pos_to_world_pos(self, x, z):
        return (
            x * self._grid_size + self._min_x,
            z * self._grid_size + self._min_z,
            )

    def world_pos_to_grid_pos(self, x, z):
        # TODO: fix this so it's accurate. some things aren't snapping that should
        return (
            int((x - self._min_x) / self._grid_size),
            int((z - self._min_z) / self._grid_size),
            )

    def get_collision_cell_at_world_pos(self, x, z):
        return self.get_collision_cell_at_grid_pos(
            *self.world_pos_to_grid_pos(x, z)
            )

    def get_collision_cell_at_grid_pos(self, x, z):
        try:
            return self._rows[z][x]
        except IndexError:
            return dict()

    def add_dynamic_collision_object(self, coll_object, name):
        name = name.upper().strip()
        self._dyn_collision_objects[name] = coll_object

    @property
    def dyn_collision_objects(self): return dict(self._dyn_collision_objects)
    @property
    def grid_size(self): return self._grid_size
    @property
    def width(self): return self._width
    @property
    def height(self): return self._height

    def snap_pos_to_grid(self, x, y, z, root_nodepath, max_dist=float("inf")):
        min_dist = max_dist
        new_pos = None
        orig_pos = (x, y, z)

        # test against static collision
        for obj_name, coll_obj in self.get_collision_cell_at_world_pos(x, z).items():
            for tri in coll_obj.tris:
                # test the point against every triangle and snap
                # to the one with the shortest distance to travel.
                new_y = tri.snap_to_y_plane(x, y, z, max_dist)
                dist  = min_dist if new_y is None else (new_y - y)**2
                if dist < min_dist:
                    min_dist = dist
                    new_pos = (x, new_y, z)

        # test against dynamic collision
        for obj_name, coll_obj in self._dyn_collision_objects.items():
            if coll_obj.scene_object is None:
                # scene object never got attached
                continue

            # NOTE: x, y, z are world-relative coordinates. for dynamic objects,
            #       they need to be converted to be relative to the collision objects
            #       position, and then converted back to world when returned
            coll_obj_nodepath = panda3d.core.NodePath(coll_obj.scene_object.p3d_node)
            # TODO: update this to pass the calculated "up" vector
            px, pz, py = coll_obj_nodepath.getPos(root_nodepath)

            # since we're snapping infinitely far vertically, we
            # don't wanna consider y dist when considering radius
            dist_sq = (x - px)**2 + (z - pz)**2
            if dist_sq > coll_obj.radius_sq:
                # too far away to test against. skip
                continue

            # convert provided coordinate to position relative to collision object
            # NOTE: This ONLY works if the object hasn't rotated.
            # TODO: Need to make this work when the dynamic object rotates
            x1, y1, z1 = x-px, y-py, z-pz

            for tri in coll_obj.tris:
                # test the point against every triangle and snap
                # to the one with the shortest distance to travel.
                new_y1 = tri.snap_to_y_plane(x1, y1, z1, max_dist)
                dist   = min_dist if new_y1 is None else (new_y1 - y1)**2
                if dist < min_dist:
                    min_dist = dist
                    new_pos = (x, y+(new_y1-y1), z)

            x, y, z = orig_pos

        return new_pos
