import direct
import traceback
import panda3d

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
    speed        = 10.0

    move_rate     = 1
    roll_rate     = 30
    look_rate_h   = 0.1
    look_rate_p   = 0.1
    speed_up_rate = 2

    _show_base = None
    _camera    = None
    _time      = 0
    _active    = False
    _enabled   = False
    _camera_control_delay = 0

    _center_x = 0
    _center_y = 0

    def __init__(self, show_base, camera):
        self._show_base = show_base
        self._camera    = camera
        self._time      = 0
        self._enabled   = self._active = False

    @property
    def active(self): return self._active

    def update_camera(self, delta_t):
        delta_x = delta_y = delta_z = 0
        delta_h = delta_p = delta_r = 0

        if self._camera_control_delay <= 1:
            window = self._show_base.win
            mouse_pointer = window.getPointer(0)
            if self._camera_control_delay == 0:
                delta_h -= (mouse_pointer.getX() - self._center_x) * self.look_rate_h
                delta_p -= (mouse_pointer.getY() - self._center_y) * self.look_rate_p

            # recenter the frame before we start camera control. we do this
            # to keep from jumping the curser on the frame it's still visible,
            # or jumping the camera on the first frame control is enabled
            window.movePointer(0, int(self._center_x), int(self._center_y))

        # decrement each cycle
        self._camera_control_delay = max(0, self._camera_control_delay - 1)

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
        # TODO: fix camera rotation fucking up
        self._camera.setH(render, self._camera.getH(render) + delta_h)
        self._camera.setP(self._camera, self._camera.getP(self._camera) + delta_p)
        self._camera.setR(self._camera, self._camera.getR(self._camera) + delta_r)

    def update_camera_task(self, task):
        if self._show_base.win.getProperties().getForeground() and self._enabled:
            try:
                self.update_camera(task.time - self._time)
            except Exception:
                print(traceback.format_exc())
        else:
            self._camera_control_delay = 2

            mouse_pointer = self._show_base.win.getPointer(0)
            self._center_x = mouse_pointer.getX()
            self._center_y = mouse_pointer.getY()

        self._time = task.time
        return direct.task.Task.cont

    def start(self):
        if self._active:
            return

        self._show_base.disableMouse()
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
