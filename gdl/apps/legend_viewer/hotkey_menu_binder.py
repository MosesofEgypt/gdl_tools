import tkinter

# NOTE: these hotkey binds only work when the render window is the one in focus
class HotkeyMenuBinder:
    _hotkey_menu_binds = ()
    menus = None

    def generate_menu(self):
        if self.menus is not None:
            return

        root_menu = tkinter.Menu(self)
        self.config(menu=root_menu)

        self.menus = {"": root_menu}
        for hk in self._hotkey_menu_binds:
            if "name" not in hk:
                continue

            names = list(n.strip() for n in hk["name"].split("|"))
            cmd_name = names.pop(-1)

            # get/create the parent menu(s)
            parent_menu = root_menu
            for i in range(len(names)):
                menu_fullname = "|".join(names[:i+1]).lower()

                if menu_fullname not in self.menus:
                    self.menus[menu_fullname] = tkinter.Menu(parent_menu, tearoff=0)
                    parent_menu.add_cascade(label=names[i], menu=self.menus[menu_fullname])

                parent_menu = self.menus[menu_fullname]

            # add the command/separator
            if cmd_name:
                parent_menu.add_command(
                    label=cmd_name, accelerator=hk.get("key", "").capitalize(),
                    command=lambda func=eval(hk["func"]), args=hk["args"]: func(*args)
                    )
            else:
                parent_menu.add_separator()

    def bind_hotkeys(self, scene):
        if not scene: return
        for hk in self._hotkey_menu_binds:
            if "key" in hk:
                scene.accept(hk["key"], eval(hk["func"]), hk["args"])

    def unbind_hotkeys(self, scene):
        if not scene: return
        for hk in self._hotkey_menu_binds:
            if "key" in hk:
                scene.ignore(hk["key"])
