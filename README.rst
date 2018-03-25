================================================
``upy-sensor-feed``: A simple sensor data feed
================================================

Micropython code to interogate and manipulate a feed of data from one or more sensors.

Runs a simple event loop that checks current time against the time of a list
of scheduled events. Each event is just a method that is called if the time as 
been passed.

Relies on the following projects to talk to sensors:

* Adafruit ADS1015 ADC - https://github.com/adafruit/micropython-adafruit-ads1015
* SI1145 light sensor - https://github.com/neliogodoi/MicroPython-SI1145
* BME280 temp, humidity, pressure sensor - https://github.com/catdog2/mpy_bme280_esp8266

The script, ``get_third_pary.sh`` will download the main files from each. These can then be uploaded onto
the board.

Some configuration is required. This all lives in ``sensor_feed_config.py``. A skelton version
is in this repository.