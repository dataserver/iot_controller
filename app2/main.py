from functools import partial

from gui import App
from iot.service import IOTService
from iot_facade import IOTFacade

from iot_controller import get_status, power_speaker


def main() -> None:
    # iot = IOTFacade(IOTService())
    # power_speaker_fn = partial(power_speaker, iot=iot)
    # get_status_fn = partial(get_status, iot=iot)
    # app = SmartApp(power_speaker_fn, get_status_fn)
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
