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
    speed        = 5.0

    move_rate     = 1
    roll_rate     = 10
    look_rate_h   = 0.1
    look_rate_p   = 0.1
    speed_up_rate = 1

    _show_base = None
    _camera    = None
    _time      = 0
    _active    = False
    _enabled   = False
    _camera_control_delay = 0

    def __init__(self, show_base, camera):
        self._show_base = show_base
        self._camera    = camera
        self._time      = 0
        self._enabled   = self._active = False

    def update_camera(self, delta_t):
        delta_x = delta_y = delta_z = 0
        delta_h = delta_p = delta_r = 0

        win = self._show_base.win
        center_x = win.getProperties().getXSize() // 2
        center_y = win.getProperties().getYSize() // 2

        if not self._camera_control_delay:
            delta_h -= (win.getPointer(0).getX() - center_x) * self.look_rate_h
            delta_p -= (win.getPointer(0).getY() - center_y) * self.look_rate_p

        if self._camera_control_delay <= 1:
            # recenter the frame before we start camera control. we do this
            # to keep from jumping the curser on the frame it's still visible,
            # or jumping the camera on the first frame control is enabled
            win.movePointer(0, center_x, center_y)

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

        # decrement each cycle
        self._camera_control_delay = max(0, self._camera_control_delay - 1)

    def update_camera_task(self, task):
        if self._show_base.win.getProperties().getForeground() and self._enabled:
            self.update_camera((task.time - self._time) / 1000)
        else:
            self._camera_control_delay = 3

        self.time = task.time
        return direct.task.Task.cont

    def start(self):
        if self._active:
            return

        self.disableMouse()
        for template, delta in [("%s", True), ("%s-up", False)]:
            for key, action in [("w", "forward"),      ("s", "backward"), ("r", "up"),
                                ("a", "left"),         ("d", "right"),    ("f", "down"),
                                ("q", "roll_left"),    ("e", "roll_right"),
                                ]:
                self.accept(template % key, setattr, [self, action, delta])

        for i in range(1, 4):
            self.accept("mouse%s" % i,    self.set_enabled, [True])
            self.accept("mouse%s-up" % i, self.set_enabled, [False])

        self.accept("wheel_up",   setattr, [self, "speed_up",   True])
        self.accept("wheel_down", setattr, [self, "speed_down", True])
        self._show_base.taskMgr.add(self.update_camera_task, 'HxMouseLook::update_camera_task')
        self._active = True

    def stop(self):
        if not self._active:
            return

        for template in ["%s", "%s-up"]:
            for key in ("w", "a", "s", "d", "r", "f", "q", "e", "mouse1", "mouse2"):
                self.ignore(template % key)

        for i in range(1, 4):
            self.ignore("mouse%s" % i)
            self.ignore("mouse%s-up" % i)

        for key in ("wheel_up", "wheel_down"):
            self.ignore(key)

        mat = panda3d.core.LMatrix4f(
            self._camera.getTransform(render).getMat()
            )
        mat.invertInPlace()
        self._camera.setMat(panda3d.core.LMatrix4f.identMat())
        self._show_base.mouseInterfaceNode.setMat(mat)
        self._show_base.taskMgr.remove("HxMouseLook::update_camera_task")
        self._active = False

    def set_enabled(self, enable):
        enable = bool(enable)
        if enable == bool(self._enabled):
            return

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

        props = panda3d.core.WindowProperties()
        props.setCursorHidden(enable)
        self._show_base.win.requestProperties(props)
        self._enabled = enable
        self._camera_control_delay = 3
