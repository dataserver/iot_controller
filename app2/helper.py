import colorsys
import re


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
    if bool(re.match(r"^(#|)([a-fA-F0-9]{6}|([0-9a-fA-F]){3})$", rgbhex)) is not True:
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


def rgbint_to_rgbtuple(rgb: int) -> tuple[int, int, int]:
    """convert RGB int to RGB tuple of int (r, g, b)"""
    RGBint = int(rgb)
    r = (RGBint >> 16) & 255
    g = (RGBint >> 8) & 255
    b = RGBint & 255
    return (r, g, b)


def rgbint_to_rgbhex(rgb: int) -> str:
    """convert RGB int to RBG #hex"""
    RGBint = int(rgb)
    r = (RGBint >> 16) & 255
    g = (RGBint >> 8) & 255
    b = RGBint & 255
    return "#%02x%02x%02x" % (r, g, b)
