# IoT Desktop Controller

Simple app to control IoT devices from your computer.

## Supported Devices

- smart plug with tasmota firmware
- smart switch with tasmota firmware
- yeelight light bulb


## iot_devices.json

    {
        "iot": {
            "devices": [
                {
                    "type": "tasmota-plug",
                    "name": "Smart Plug - living room",
                    "ip": "192.168.15.40",
                    "confirm": true
                },
                {
                    "type": "yeelight-bulb",
                    "name": "Smart Light Bulb - bedroom",
                    "ip": "192.168.15.50",
                    "confirm": false
                }
            ]
        }
    }

| keys       | description |
|---        |--- |
| type       | tasmota-plug, tasmota-switch or yeelight-bulb|
| name       | name for the device|
| ip         | ip address |
| confirm    | true or false. Require a confirmtion dialog window before toggle action? Useful to avoid unwanted mistakes.|


## License ##

[![CC0](https://licensebuttons.net/p/zero/1.0/88x31.png)](https://creativecommons.org/publicdomain/zero/1.0/)

This project is in the worldwide [public domain](LICENSE).

This project is in the public domain and copyright and related rights in the work worldwide are waived through the [CC0 1.0 Universal public domain dedication](https://creativecommons.org/publicdomain/zero/1.0/).

All contributions to this project will be released under the CC0 dedication. By submitting a pull request, you are agreeing to comply with this waiver of copyright interest.
