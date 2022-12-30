import panda3d
import direct

class FreeCamera(direct.showbase.DirectObject.DirectObject):
    forward      = False
    backward     = False
    left         = False
    right        = False
    up           = False
    down         = False
    roll_left    = False
    roll_right   = False
    speed_up     = False
    speed_down   = False
    speed       = 5.0

    move_rate     = 1
    roll_rate     = 10
    look_rate_h   = 0.1
    look_rate_p   = 0.1
    speed_up_rate = 1

    _camera  = None
    _time    = 0
    _enabled = False

    def __init__(self, show_base, camera):
        self.show_base = show_base
        self._camera = camera
        self._time = 0

        self.accept("space", self.toggle, [])

    def update_camera(self, task):
        delta_t = (task.time - self._time) / 1000
        delta_x = delta_y = delta_z = 0
        delta_h = delta_p = delta_r = 0

        win_props = self.show_base.win.getProperties()
        if win_props.getForeground():
            center_x = win_props.getXSize() // 2
            center_y = win_props.getYSize() // 2

            delta_h -= (self.show_base.win.getPointer(0).getX() - center_x) * self.look_rate_h
            delta_p -= (self.show_base.win.getPointer(0).getY() - center_y) * self.look_rate_p
            self.show_base.win.movePointer(0, center_x, center_y)

            if self.speed_up:   self.speed += self.speed_up_rate
            if self.speed_down: self.speed -= self.speed_up_rate
            self.speed = max(0, self.speed)
            self.speed_up    = False
            self.speed_down  = False

            if self.left:       delta_x -= self.move_rate * delta_t * self.speed
            if self.right:      delta_x += self.move_rate * delta_t * self.speed
            if self.forward:    delta_y += self.move_rate * delta_t * self.speed
            if self.backward:   delta_y -= self.move_rate * delta_t * self.speed
            if self.up:         delta_z += self.move_rate * delta_t * self.speed
            if self.down:       delta_z -= self.move_rate * delta_t * self.speed
            if self.roll_left:  delta_r -= self.roll_rate * delta_t# * self.speed
            if self.roll_right: delta_r += self.roll_rate * delta_t# * self.speed

            self._camera.setX(self._camera, self._camera.getX(self._camera) + delta_x)
            self._camera.setY(self._camera, self._camera.getY(self._camera) + delta_y)
            self._camera.setZ(render, self._camera.getZ(render) + delta_z)
            self._camera.setH(render, self._camera.getH(render) + delta_h)
            self._camera.setP(self._camera, self._camera.getP(self._camera) + delta_p)
            self._camera.setR(self._camera, self._camera.getR(self._camera) + delta_r)

        self.time = task.time
        return direct.task.Task.cont

    def start(self):
        self.show_base.disableMouse()

        props = panda3d.core.WindowProperties()
        props.setCursorHidden(True)
        self.show_base.win.requestProperties(props)

        center_x = self.show_base.win.getProperties().getXSize() // 2
        center_y = self.show_base.win.getProperties().getYSize() // 2
        self.show_base.win.movePointer(0, center_x, center_y)
        self.show_base.taskMgr.add(self.update_camera, 'HxMouseLook::update_camera')

        for template, delta in [("%s", True), ("%s-up", False)]:
            for key, action in [("w", "forward"),      ("s", "backward"), ("r", "up"),
                                ("a", "left"),         ("d", "right"),    ("f", "down"),
                                ("q", "roll_left"),    ("e", "roll_right"),
                                ]:
                self.accept(template % key, setattr, [self, action, delta])

        self.accept("wheel_up",   setattr, [self, "speed_up",   True])
        self.accept("wheel_down", setattr, [self, "speed_down", True])
        self._enabled = True

    def stop(self):
        self.show_base.taskMgr.remove("HxMouseLook::update_camera")

        props = panda3d.core.WindowProperties()
        props.setCursorHidden(False)
        self.show_base.win.requestProperties(props)

        mat = panda3d.core.LMatrix4f(
            self._camera.getTransform(render).getMat()
            )
        mat.invertInPlace()
        self._camera.setMat(panda3d.core.LMatrix4f.identMat())
        self.show_base.mouseInterfaceNode.setMat(mat)
        self.show_base.enableMouse()

        self.left        = False
        self.right       = False
        self.forward     = False
        self.backward    = False
        self.up          = False
        self.down        = False
        self.roll_left   = False
        self.roll_right  = False
        self.speed_up    = False
        self.speed_down  = False

        for template in ["%s", "%s-up"]:
            for key in ("w", "a", "s", "d", "r", "f", "q", "e"):
                self.ignore(template % key)

        for key in ("wheel_up", "wheel_down"):
            self.ignore(key)

        self._enabled = False

    def toggle(self):
        if self._enabled:
            self.stop()
        else:
            self.start()
