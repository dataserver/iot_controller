import colorsys
import json
import re
from pathlib import Path

import requests
import ttkbootstrap as ttk
from ttkbootstrap.dialogs.colorchooser import ColorChooserDialog
from ttkbootstrap.dialogs.dialogs import Messagebox
from yeelight import Bulb

"""
Default factory:

    {'POWER': 'ON', 'Dimmer': 100, 'Color': '000000FF00', 'HSBColor': '0,0,0', 'White': 100, 'CT': 153, 'Channel': [0, 0, 0, 100, 0]}
    
    Use web console to reset it to factory if needed.
    > JSON {'POWER': 'ON', 'Dimmer': 100, 'Color': '000000FF00', 'HSBColor': '0,0,0', 'White': 100, 'CT': 153, 'Channel': [0, 0, 0, 100, 0]}

Athom Light

    internals https://youtu.be/jz3T-U16RuY?t=330
    https://www.esphome-devices.com/devices/Athom-E27-15W-Bulb
    https://templates.blakadder.com/athom_LB01-15W-E27.html
    https://www.esphome-devices.com/devices/Athom-E27-7W-Bulb
    https://templates.blakadder.com/athom_LB01-7W-B22.html
    https://tasmota.github.io/docs/GPIO-Conversion/#gpio-conversion

Warning RGBCCT type

    Athom 7W 600lm RGBCCT Bulb (LB017W)
    Do not turn on the cool/white color or warm color AND RGB channel at the same time, and do not turn on the white mixing mode
    (SetOption105 1 should not be executed). Otherwise, the bulb will be damaged

    Athom Light is type: RGBCCT
    5 Channels - RGBCCT Lights
    5 channel lights are RGBCCT - a 3 channel RGB light and an additional 2 channel CCT ligh
    https://tasmota.github.io/docs/Lights/#5-channels-rgbcct-lights

    Athom Bulb has 3 LEDS => rgb LED, warm LED, cold LED. Total 5 channels [R,G,B, Cold White, Warm CT] -> "Channel":[0,0,0,100,0]
    Setting White 100 means White LED 100% AND Red LED at 0%, Green LED at 0%, Blue LED at 0%
    RGB white color is not the same. Its combination of 3 LEDs R, G, B:
    eg:
        With white LED at 0% and RGB 0..100%, 0..100%, 0..100%

RESOURCES:

    https://www.pythontutorial.net/tkinter/
    https://ttkbootstrap.readthedocs.io/en/latest/
    https://yeelight.readthedocs.io/en/latest/
    https://iconarchive.com/

"""


BASE_PATH = Path(__file__).parent
IOT_JSON_FILE = "iot_devices.json"
# 0 - 100 = 100 -> 10 steps = 10
SLIDER_DIMMER_MULTIPLIER = 10
# 500 - 153 = 347 -> 10 steps ~ 35
SLIDER_CT_MULTIPLIER = 35


class ConnectionError(Exception):
    pass


class ResponseCodeError(Exception):
    pass


class RequestError(Exception):
    pass


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

        with Path(BASE_PATH, IOT_JSON_FILE).open("r") as filehandle:
            data = json.load(filehandle)
            for row_number, device in enumerate(data["iot"]["devices"], start=1):
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
                elif device["type"] == "tasmota-light-RGBCCT":
                    btn = ttk.Button(
                        self.frame,
                        text=f"{device['name']} Toggle",
                        command=lambda ip=device["ip"], confirm=device[
                            "confirm"
                        ]: self.tasmota_smart_plug_toogle(ip, confirm),
                        bootstyle="outline",  # type: ignore
                    )
                    btn.grid(column=0, row=row_number, sticky="ew", padx=5, pady=8)
                    btn2 = ttk.Button(
                        self.frame,
                        command=lambda ip=device["ip"]: self.window_tasmota_light_open(
                            ip
                        ),
                        image=self.icon_cog,
                        bootstyle="link-light",  # type: ignore
                    )
                    btn2.grid(column=1, row=row_number, sticky="ew")
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
                btn = None
                btn2 = None

        self.frame.pack()
        self.window_center()

    def tasmota_smart_plug_toogle(self, ip: str, confirm: bool = False) -> bool:
        query_string = "cmnd=Power%20Toggle"
        answer = True if not confirm else self.dialog_confirm()
        if answer:
            try:
                url = f"http://{ip}/cm?{query_string}"
                r = requests.get(url=url, timeout=3, verify=False)
                if r.status_code == 200:
                    j = r.json()
                    if j.get("POWER") is not None:
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
        answer = True if not confirm else self.dialog_confirm()
        if answer:
            try:
                bulb = Bulb(ip=ip)
                bulb.toggle()
                return True
            except:
                print("Failed to toggle Yeelight bulb")
        return False

    def window_yeelight_open(self, ip: str) -> None:
        new_window = ttk.Toplevel(self.primary)
        app = YeelightWindow(new_window, ip)

    def window_tasmota_light_open(self, ip: str) -> None:
        new_window = ttk.Toplevel(self.primary)
        app = TasmotaLightWindow(new_window, ip)

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


class TasmotaLightWindow:
    def __init__(self, primary, ip: str) -> None:
        self.ip = ip
        self.is_on = False
        self.curr_color = None
        self.curr_state = {}
        self.dimmer_cmd_disabled = False
        self.ct_cmd_disabled = False
        self.using_rgb_channels = False
        self.primary = primary
        self.primary.title("Settings")
        self.primary.geometry("350x350")
        self.primary.minsize(350, 250)
        self.primary.iconbitmap(Path(BASE_PATH, "resources", "window.ico"))
        self.primary.focus_set()

        self.icon_color_picker = ttk.PhotoImage(
            file=Path(BASE_PATH, "resources", "color_picker.png")
        )
        self.frame = ttk.Labelframe(self.primary, text="Tasmota Light")
        self.frame.grid_columnconfigure(0, weight=2, minsize=200)
        self.frame.pack(fill="both", expand=1, padx=10, pady=10)

        #  ROW 1 dimmer input
        l = ttk.Label(self.frame, text="Dimmer")
        l.grid(column=0, row=1, sticky="ew", padx=5, pady=5)
        self.input_dimmer_var = ttk.IntVar(master=self.primary)
        self.input_dimmer_field = ttk.Scale(
            self.frame,
            # command=self.change_dimmer,
            variable=self.input_dimmer_var,
            # tickinterval=1, missin from ttkbootstrap
            value=0,
            from_=0,
            to=10,
            orient=ttk.HORIZONTAL,
        )
        #  ROW 2
        self.input_dimmer_field.grid(
            column=0, row=2, columnspan=2, sticky="ew", padx=10, pady=10
        )

        #  ROW 3 LED option
        self.frame_option = ttk.Frame(self.frame)
        self.frame_option.grid(
            column=0, row=3, columnspan=2, sticky="ew", padx=0, pady=10
        )
        #  ROW 3.1
        l = ttk.Label(self.frame_option, text="LED type")
        l.grid(column=0, row=0, sticky="ew", padx=5, pady=5)
        #  ROW 3.2
        self.input_led_option_var = ttk.StringVar(master=self.primary)
        r1 = ttk.Radiobutton(
            self.frame_option,
            text="Use White LED",
            variable=self.input_led_option_var,
            value="white",
            command=self.check_radio_option,
        )
        r1.grid(column=0, row=1, sticky="w", padx=10, pady=10)
        r2 = ttk.Radiobutton(
            self.frame_option,
            text="Use RGB LEDs",
            variable=self.input_led_option_var,
            value="rgb",
            command=self.check_radio_option,
        )
        r2.grid(column=1, row=1, sticky="w", padx=10, pady=10)
        self.input_led_option_var.set("white")

        # ROW 4
        # rbg frame or white/CT
        self.input_ct_var = ttk.IntVar(master=self.primary)
        self.frame_rgb_or_ct = ttk.Frame(self.frame)
        self.frame_rgb_or_ct.columnconfigure(0, weight=1)
        self.frame_rgb_or_ct.grid(
            column=0, row=4, columnspan=2, sticky="ew", padx=0, pady=10
        )

        # ROW 5
        # close button
        b = ttk.Button(self.frame, text="Close Window", command=self.window_close)
        b.grid(column=0, row=20, columnspan=2, padx=5, pady=20)

        self.frame.pack(fill="both", expand=1)
        self.primary.bind("<Escape>", self.window_close)
        self.window_center()
        self.setup_bulb_props()

    def setup_bulb_props(self) -> None:
        try:
            self.get_device_state()
            self.toggle_frame_rgb_or_ct()
            self.update_gui()
            self.input_dimmer_field["command"] = self.change_dimmer
            self.input_ct_field["command"] = self.change_ct
            self.is_on = True
        except Exception as e:
            self.is_on = False
            self.dialog_error(
                title="Error",
                message=f"{e}",
            )

    def update_gui(self):
        self.dimmer_cmd_disabled = True
        self.ct_cmd_disabled = True

        self.input_dimmer_var.set(
            int(self.curr_state["Dimmer"] / SLIDER_DIMMER_MULTIPLIER)
        )
        self.input_dimmer_field.set(
            int(self.curr_state["Dimmer"] / SLIDER_DIMMER_MULTIPLIER)
        )
        self.input_ct_var.set(int(self.curr_state["CT"] / SLIDER_CT_MULTIPLIER))
        self.input_ct_field.set(int(self.curr_state["CT"] / SLIDER_CT_MULTIPLIER))
        if self.curr_state["HSBColor"] == "0,0,0":
            self.using_rgb_channels = False
            self.input_led_option_var.set("white")
        else:
            self.using_rgb_channels = True
            self.input_led_option_var.set("rgb")
            self.toggle_frame_rgb_or_ct()
            self.rgb_color_canvas.config(bg=self.hsv2rgb(self.curr_state["HSBColor"]))
        self.dimmer_cmd_disabled = False
        self.ct_cmd_disabled = False

    def toggle_frame_rgb_or_ct(self):
        for widgets in self.frame_rgb_or_ct.winfo_children():
            widgets.destroy()
        #  White/CT widgets
        if not self.using_rgb_channels:
            # row 0
            l = ttk.Label(self.frame_rgb_or_ct, text="Color Temperature")
            l.grid(column=0, row=0, columnspan=2, sticky="ew", padx=5, pady=5)
            # row 1
            min_v = round(153 / SLIDER_CT_MULTIPLIER) - 1
            max_v = round(500 / SLIDER_CT_MULTIPLIER) + 1
            self.input_ct_field = ttk.Scale(
                self.frame_rgb_or_ct,
                variable=self.input_ct_var,
                # tickinterval=1, missin from ttkbootstrap
                value=0,
                from_=min_v,
                to=max_v,
                orient=ttk.HORIZONTAL,
                bootstyle="warning",  # type: ignore
            )
            self.input_ct_field.grid(
                column=0, row=1, columnspan=2, sticky="ew", padx=10, pady=10
            )
        #  RGB color widget
        else:
            # row 0
            l = ttk.Label(self.frame_rgb_or_ct, text="Color")
            l.grid(column=0, row=0, sticky="ew", padx=5, pady=5)

            self.rgb_color_canvas = ttk.Canvas(
                self.frame_rgb_or_ct,
                width=200,
                height=40,
            )
            # row 1
            self.rgb_color_canvas.grid(column=0, row=1, sticky="ew", padx=20, pady=10)
            if self.curr_state["HSBColor"] != "0,0,0":
                self.rgb_color_canvas.config(
                    bg=self.hsv2rgb(self.curr_state["HSBColor"])
                )
            else:
                self.rgb_color_canvas.config(bg="#FFFFFF")

            b = ttk.Button(
                self.frame_rgb_or_ct,
                text=f"pick",
                command=self.window_color_chooser_open,
                image=self.icon_color_picker,
                bootstyle="link-light",  # type: ignore
            )
            b.grid(column=1, row=1, sticky="ew", padx=5, pady=10)

    def check_radio_option(self):
        opt = self.input_led_option_var.get()
        self.dimmer_cmd_disabled = True
        self.ct_cmd_disabled = True
        if opt == "rgb":
            self.using_rgb_channels = True
        else:
            self.using_rgb_channels = False
            self.send_cmd(cmnd="Color 0000008000")
            self.input_dimmer_var.set(int(50 / SLIDER_DIMMER_MULTIPLIER))
            self.input_dimmer_field.set(int(50 / SLIDER_DIMMER_MULTIPLIER))
        self.toggle_frame_rgb_or_ct()
        self.dimmer_cmd_disabled = False
        self.ct_cmd_disabled = False

    def send_cmd(self, cmnd: str) -> None:
        """
        Send web request to device.
            http://device_ip/cm?cmnd={cmnd}

        Parameters
        ----------
        cmnd : str
            The command to be attached to Web Request

            e.g.:
                Dimmer 10

                STATUS

                HSBColor 250,55,44

        """
        try:
            print("cmnd =", cmnd)
            url = f"http://{self.ip}/cm?cmnd={cmnd}"
            r = requests.get(url=url, timeout=4, verify=False)
            if r.status_code == 200:
                state = r.json()
                self.curr_state = state
                print("state: ", state)
                return
            else:
                raise ResponseCodeError()
        except requests.exceptions.Timeout:
            raise ConnectionError("Connection Time out")
        except requests.exceptions.TooManyRedirects:
            raise ConnectionError("Connection Too Many Redirects")
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
        except ResponseCodeError:
            raise ResponseCodeError("Got Wrong responde code from device")
        except:
            raise RequestError("Unknow Request Error")

    def get_device_state(self) -> None:
        self.send_cmd(cmnd="STATE")
        if self.curr_state.get("HSBColor") is None:
            if self.curr_state["HSBColor"] != "0,0,0":
                self.using_rgb_channels = True

    def change_dimmer(self, value) -> None:
        if self.is_on and not self.dimmer_cmd_disabled:
            try:
                # 0..100 = set dimmer value from 0 to 100%
                dv = round(SLIDER_DIMMER_MULTIPLIER * self.input_dimmer_var.get())
                val = self.clamp(value=dv, minx=0, maxx=100)
                if self.curr_state["Dimmer"] != val:
                    self.send_cmd(cmnd=f"Dimmer {val}")
            except Exception as e:
                self.dialog_error(
                    title="Error",
                    message="Code: {e} \n Unable to complete action.\n Please check if device is connect to network.",
                )

    def change_ct(self, value) -> None:
        if self.is_on and not self.ct_cmd_disabled:
            try:
                # set CT value from 153 to 500
                dv = round(SLIDER_CT_MULTIPLIER * self.input_ct_var.get())
                val = self.clamp(value=dv, minx=153, maxx=500)
                # if abs(self.curr_state["CT"] - val) > 50:
                if self.curr_state["CT"] != val:
                    self.send_cmd(cmnd=f"CT {val}")
            except Exception as e:
                self.dialog_error(
                    title="Error",
                    message="Code: {e} \n Unable to complete action.\n Please check if device is connect to network.",
                )

    def change_rgb_channel(self, rgb_str: str) -> None:
        if self.is_on:
            try:
                # Reset all channels to zero to avoid any chance to bulb damaged
                self.send_cmd(cmnd=f"Color 0000000000")
                # Set color using HSBColor parameter
                h, s, v = self.rgb2hsv(rgb_str)
                self.send_cmd(cmnd=f"HSBColor {h},{s},{v}")
            except Exception as e:
                self.dialog_error(
                    title="Error",
                    message="Code: {e} \n Unable to complete action.\n Please check if device is connect to network.",
                )

    def dialog_confirm(self) -> bool:
        result = Messagebox.okcancel(
            message="Confirm action?", title="Confirm", parent=self.primary
        )
        if result == "OK":
            return True
        return False

    def window_color_chooser_open(self) -> None:
        cd = ColorChooserDialog()
        if self.curr_state["HSBColor"] != "0,0,0":
            cd.initialcolor = self.hsv2rgb(self.curr_state["HSBColor"])
        else:
            cd.initialcolor = "#FFFFFF"
        cd.show()
        self.window_bring_to_front()
        if cd.result:
            colors = cd.result
            # h, s, l = (colors.hsl[0], colors.hsl[1], colors.hsl[2])
            # HSV(HSB) not available
            self.change_rgb_channel(rgb_str=colors.hex)
            self.color = colors.hex
            self.rgb_color_canvas.config(bg=colors.hex)
            self.using_rgb_channels = True

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
    def clamp(value: int | float, minx: int | float, maxx: int | float) -> int | float:
        """
        Constrain a value between a minimum and a maximum.
            If the value is larger than the maximum or lower than the minimum, the
            maximum or minimum will be returned instead.

        Parameters
        ----------
        value : int or float
            The value to clamp.

        minx: int or float
            Lower limit the value can take.

        maxx: int or float
            Upper limit the value can take.

        Returns
        ----------
        int or float
            If initial value > max_value, return celing value max_value

        """
        return max(minx, min(maxx, value))

    @staticmethod
    def hsv2rgb(hsb_str: str) -> str:
        """
        Convert a HSB|HSV from tasmosta light to rgb

        Parameters
        ----------
        hsb_str : str
            From HSB, aka HSV, value
            e.g. 245,97,97

        Returns
        ----------
        str
            A rgb string
            e.g.: #1b07f7

        https://en.wikipedia.org/wiki/HSL_and_HSV
        """

        def _clamp(value: float, minx: int, maxx: int):
            return max(minx, min(maxx, round(value)))

        hsb_str = hsb_str.strip()
        # re.match() method only checks if the RE matches at the start of a string, start() will always be zero.
        # The "^" is already set
        # https://regex101.com/
        if (
            bool(
                re.match(
                    r"^(3[0-5][0-9]|[12][0-9][0-9]|[1-9][0-9]|[0-9]),(100|[1-9][0-9]|[0-9]),(100|[1-9][0-9]|[0-9])$",
                    hsb_str,
                )
            )
            is not True
        ):
            return "#000000"

        hsb = hsb_str.split(",")
        # convert 0..359|0..100 to 0..1
        hue = int(hsb[0]) / 359
        sat = int(hsb[1]) / 100
        val = int(hsb[2]) / 100
        r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
        # convert 0..1 to 0..255
        red = r * 255
        green = g * 255
        blue = b * 255

        return "#%02x%02x%02x" % (
            _clamp(red, 0, 255),
            _clamp(green, 0, 255),
            _clamp(blue, 0, 255),
        )

    @staticmethod
    def rgb2hsv(rgbhex: str) -> tuple:
        """
        Convert RGB (#1b07f7) to HSB, aka HSV, in tuple (245,97,97)

        Parameters
        ----------
        rgbhex : str
            The rgb color
            eg: #1b07f7 or 1b07f7

        Returns
        ----------
        tuple
            A tuple of values (hue, saturation, value)
            eg: (245,97,97)

        https://en.wikipedia.org/wiki/HSL_and_HSV
        """

        def _clamp(value: float, minx: int, maxx: int):
            return max(minx, min(maxx, round(value)))

        rgbhex = rgbhex.strip()
        # re.match() method only checks if the RE matches at the start of a string, start() will always be zero.
        # The "^" is already set
        if (
            bool(re.match(r"^(#|)([a-fA-F0-9]{6}|([0-9a-fA-F]){3})$", rgbhex))
            is not True
        ):
            return (0, 0, 0)

        hex = rgbhex.replace("#", "")
        r, g, b = tuple(int(hex[i : i + 2], 16) for i in (0, 2, 4))
        # convert 0..255 to 0..1
        red = r / 255
        green = g / 255
        blue = b / 255
        h, s, v = colorsys.rgb_to_hsv(red, green, blue)
        # convert 0..1 to 0..359|0..100
        hue = h * 359
        sat = s * 100
        val = v * 100

        return (_clamp(hue, 0, 359), _clamp(sat, 0, 100), _clamp(val, 0, 100))


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

    def dialog_confirm(self) -> bool:
        result = Messagebox.okcancel(
            message="Confirm action?", title="Confirm", parent=self.primary
        )
        if result == "OK":
            return True
        return False

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
