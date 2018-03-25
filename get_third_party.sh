#!/bin/bash
#
# Fetches 3rd party packages from github ready to be uploaded to device.
#

PACKAGES="
https://github.com/adafruit/micropython-adafruit-ads1015/raw/master/ads1x15.py
https://github.com/neliogodoi/MicroPython-SI1145/raw/master/si1145.py
https://github.com/catdog2/mpy_bme280_esp8266/raw/master/bme280.py
"

for fname in ${PACKAGES}
do
    curl -O $fname
done