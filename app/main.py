import json
from pathlib import Path

import requests
import ttkbootstrap as ttk
from ttkbootstrap.dialogs.colorchooser import ColorChooserDialog
from ttkbootstrap.dialogs.dialogs import Messagebox
from yeelight import Bulb

# https://www.pythontutorial.net/tkinter/
# https://ttkbootstrap.readthedocs.io/en/latest/
# https://yeelight.readthedocs.io/en/latest/
# https://iconarchive.com/

BASE_PATH = Path(__file__).parent
IOT_JSON_FILE = "iot_devices.json"


class MainWindow:
    def __init__(self, primary) -> None:
        self.primary = primary
        self.primary.title("IoT Controller")
        self.primary.geometry("450x350")
        self.primary.minsize(350, 250)
        self.primary.iconbitmap(Path(BASE_PATH, "resources", "window.ico"))

        self.frame = ttk.Frame(self.primary, padding=10)
        self.frame.grid_columnconfigure(0, weight=1, minsize=200)
        self.frame.pack(fill="both", expand=1, padx=10, pady=10)

        title = ttk.Label(self.frame, text="Welcome to IoT Controller")
        title.grid(column=0, row=0, columnspan=2, padx=5, pady=5)
        self.icon_cog = ttk.PhotoImage(file=Path(BASE_PATH, "resources", "cog.png"))

        row_number = 1
        with Path(BASE_PATH, IOT_JSON_FILE).open("r") as filehandle:
            data = json.load(filehandle)
            for device in data["iot"]["devices"]:
                if (
                    device["type"] == "tasmota-plug"
                    or device["type"] == "tasmota-switch"
                ):
                    btn = ttk.Button(
                        self.frame,
                        text=f"{device['name']} -  Toggle",
                        command=lambda ip=device["ip"], confirm=device[
                            "confirm"
                        ]: self.tasmota_smart_plug_toogle(ip, confirm),
                        bootstyle="outline",  # type: ignore
                    )
                    btn.grid(
                        column=0,
                        columnspan=1,
                        row=row_number,
                        sticky="ew",
                        padx=5,
                        pady=8,
                    )
                    row_number += 1
                elif device["type"] == "yeelight-bulb":
                    btn = ttk.Button(
                        self.frame,
                        text=f"{device['name']} Toggle",
                        command=lambda ip=device["ip"], confirm=device[
                            "confirm"
                        ]: self.yeelight_toggle(ip, confirm),
                        bootstyle="outline",  # type: ignore
                    )
                    btn.grid(column=0, row=row_number, sticky="ew", padx=5, pady=8)
                    btn2 = ttk.Button(
                        self.frame,
                        command=lambda ip=device["ip"]: self.window_yeelight_open(ip),
                        image=self.icon_cog,
                        bootstyle="link-light",  # type: ignore
                    )
                    btn2.grid(column=1, row=row_number, sticky="ew")
                    row_number += 1

        self.frame.pack()
        self.window_center()

    def tasmota_smart_plug_toogle(self, ip: str, confirm: bool = False) -> bool:
        query_string = "cmnd=Power%20Toggle"
        answer = True if confirm is False else self.dialog_confirm()
        if answer:
            try:
                url = f"http://{ip}/cm?{query_string}"
                print(url)
                r = requests.get(url=url, timeout=1, verify=False)
                if r.status_code == 200:
                    j = r.json()
                    if "POWER" in j:
                        return True
                    else:
                        return False
            except Exception as e:
                self.dialog_error(
                    title="Toogle Error",
                    message="Unable to complete action.\n Please check if device is connect to network.",
                )
        return False

    def yeelight_toggle(self, ip: str, confirm: bool = False) -> bool:
        answer = True if confirm is False else self.dialog_confirm()
        if answer:
            try:
                bulb = Bulb(ip=ip)
                bulb.toggle()
                return True
            except:
                print("Bulb failed")
        return False

    def window_yeelight_open(self, ip: str) -> None:
        new_window = ttk.Toplevel(self.primary)
        app = YeelightWindow(new_window, ip)

    def window_close(self) -> None:
        self.primary.destroy()

    def window_center(self) -> None:
        self.primary.update()
        w = self.primary.winfo_width()
        h = self.primary.winfo_height()
        ws = self.primary.winfo_screenwidth()
        hs = self.primary.winfo_screenheight()
        x = (ws / 2) - (w / 2)
        y = (hs / 2) - (h / 2)
        self.primary.geometry("+%d+%d" % (x, y))

    def dialog_confirm(self) -> bool:
        result = Messagebox.okcancel(
            message="Toogle the device?", title="Confirm", parent=self.primary
        )
        if result == "OK":
            return True
        return False

    def dialog_error(self, message: str, title: str = "Error") -> None:
        Messagebox.show_error(message=message, title=title, parent=self.primary)


class YeelightWindow:
    def __init__(self, primary, ip: str) -> None:
        self.bulb_ip = ip
        self.bulb_is_on = False
        self.bulb_rgb = ""
        self.bulb_brightness = 0
        self.bulb = Bulb(ip=self.bulb_ip)

        self.primary = primary
        self.primary.title("Settings")
        self.primary.geometry("350x250")
        self.primary.minsize(350, 250)
        self.primary.iconbitmap(Path(BASE_PATH, "resources", "window.ico"))
        self.primary.focus_set()

        self.icon_color_picker = ttk.PhotoImage(
            file=Path(BASE_PATH, "resources", "color_picker.png")
        )
        self.frame = ttk.Labelframe(self.primary, text="Yeelight")
        self.frame.grid_columnconfigure(0, weight=1, minsize=200)
        self.frame.pack(fill="both", expand=1, padx=10, pady=10)

        #  brightness input
        l = ttk.Label(self.frame, text="Bright")
        l.grid(column=0, row=1, sticky="ew", padx=5, pady=5)
        self.input_brightness_var = ttk.IntVar()
        self.input_brightness_field = ttk.Scale(
            self.frame,
            command=self.change_brightness,
            variable=self.input_brightness_var,
            value=0,
            from_=0,
            to=100,
            orient=ttk.HORIZONTAL,
        )
        self.input_brightness_field.grid(
            column=0, row=2, columnspan=2, sticky="ew", padx=10, pady=10
        )

        #  RGB color input
        l = ttk.Label(self.frame, text="Color")
        l.grid(column=0, row=3, sticky="ew", padx=5, pady=5)
        self.rgb_color_canvas = ttk.Canvas(self.frame, width=200, height=40)
        self.rgb_color_canvas.grid(column=0, row=4, sticky="ew", padx=20, pady=10)

        b = ttk.Button(
            self.frame,
            text=f"pick",
            command=self.window_color_chooser_open,
            image=self.icon_color_picker,
            bootstyle="link-light",  # type: ignore
        )
        b.grid(column=1, row=4, sticky="ew", padx=5, pady=10)

        # close button
        b = ttk.Button(self.frame, text="Close Window", command=self.window_close)
        b.grid(column=0, row=10, columnspan=2, padx=5, pady=20)

        self.frame.pack(fill="both", expand=1)

        self.primary.bind("<Escape>", self.window_close)

        self.window_center()
        self.get_bulb_props()

    def get_bulb_props(self) -> None:
        try:
            props = self.bulb.get_properties()
            hex_rgb = self._rgbint_to_rgbhex(props["rgb"])
            self.input_brightness_var = props["bright"]
            self.input_brightness_field.set(props["bright"])
            self.rgb_color_canvas.config(bg=hex_rgb)
            self.bulb_color = hex_rgb
            self.bulb_brightness = int(float(props["bright"]))
            self.bulb_is_on = True
        except:
            self.bulb_is_on = False

    def change_brightness(self, value) -> None:
        if self.bulb_is_on:
            brightness = int(float(value))
            self.bulb.set_brightness(brightness)

    def window_color_chooser_open(self) -> None:
        cd = ColorChooserDialog()
        cd.initialcolor = self.bulb_color
        cd.show()
        self.window_bring_to_front()

        if cd.result:
            colors = cd.result
            self.bulb.set_rgb(colors.rgb[0], colors.rgb[1], colors.rgb[2])
            self.bulb_color = colors.hex
            self.rgb_color_canvas.config(bg=colors.hex)

    def window_close(self, event=None) -> None:
        self.primary.destroy()

    def window_center(self) -> None:
        self.primary.update()
        w = self.primary.winfo_width()
        h = self.primary.winfo_height()
        ws = self.primary.winfo_screenwidth()
        hs = self.primary.winfo_screenheight()
        x = (ws / 2) - (w / 2)
        y = (hs / 2) - (h / 2)
        self.primary.geometry("+%d+%d" % (x, y))

    def window_bring_to_front(self) -> None:
        self.primary.attributes("-topmost", 1)
        self.primary.attributes("-topmost", 0)

    def dialog_error(self, message: str, title: str = "Error") -> None:
        Messagebox.show_error(message=message, title=title, parent=self.primary)

    @staticmethod
    def _rgbint_to_rgbtuple(rgb: int) -> tuple[int, int, int]:
        """convert RGB int to RGB tuple of int (r, g, b)"""
        RGBint = int(rgb)
        r = (RGBint >> 16) & 255
        g = (RGBint >> 8) & 255
        b = RGBint & 255
        return (r, g, b)

    @staticmethod
    def _rgbint_to_rgbhex(rgb: int) -> str:
        """convert RGB int to RBG #hex"""
        RGBint = int(rgb)
        r = (RGBint >> 16) & 255
        g = (RGBint >> 8) & 255
        b = RGBint & 255
        return "#%02x%02x%02x" % (r, g, b)


def main():

    root = ttk.Window()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
