"""Main sensor feed loop"""
import machine
import network
import utime
from umqtt.simple import MQTTClient

import ntptime

import bme280                                                                                                                                                                                                                                                        
import si1145 
import ads1x15

# 60 * 60 * 6
SECONDS_PER_6HOURS = 21600
OFFSET_3HOURS = 10800

def next_water_time(current_time):
    """
        Determine the next watering time.

        Water every 6 hours. Want 03:00, 09:00, 15:00, 21:00.
    """
    last_trigger = current_time // SECONDS_PER_6HOURS * SECONDS_PER_6HOURS + OFFSET_3HOURS
    next_trigger = last_trigger + SECONDS_PER_6HOURS
    return next_trigger


def wait_for_connection(sta_if):
    import utime
    while True:
        status = sta_if.status()
        if status == network.STAT_CONNECTING:
            pass
        elif status == network.STAT_GOT_IP:
            print('network config:', sta_if.ifconfig())
            return True
        else:
            # failed
            print('unable to connect to network')
            return False
        utime.sleep_us(100)


def do_network_connect(ssid, password):
    sta_if = network.WLAN(network.STA_IF)
    if not wait_for_connection(sta_if):
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect(ssid, password)
        wait_for_connection(sta_if)
    else:
        print('automatic reconnect successful')


class Application:
    DEFAULT_EVENT_PERIOD = 300 # seconds

    def __init__(self, ssid, password, mqtt_host, mqtt_root_topic, pin_soil_power, pin_pump, pin_scl, pin_sda, i2c_addr_bme280, event_periods, debug):
        """Setup the application"""
        self._events = []

        self.should_bail = False
        self.debug = debug
        self.event_periods = event_periods

        # ensure network is up
        do_network_connect(ssid, password)

        # configure mqtt client
        self.mqtt_root_topic = mqtt_root_topic
        self.mqtt_client = MQTTClient("umqtt_client", mqtt_host)
        self.mqtt_client.set_callback(self.mqtt_recieve)
        self.mqtt_client.connect()

        # configure output pins
        self.pin_soil_power = machine.Pin(pin_soil_power, machine.Pin.OUT)
        self.pin_pump = machine.Pin(pin_pump, machine.Pin.OUT)

        # set up i2c bus and sensors
        self.i2c = machine.I2C(scl=machine.Pin(pin_scl), sda=machine.Pin(pin_sda))
        self.sensor_bme280 = bme280.BME280(i2c=self.i2c, address=i2c_addr_bme280)    
        self.sensor_si1145 = si1145.SI1145(i2c=self.i2c)      
        self.sensor_adc = ads1x15.ADS1015(self.i2c)                                                                                                 

        # topic to trigger event loop end
        self.mqtt_client.subscribe(self.mqtt_make_topic("halt"))
        self.mqtt_client.subscribe(self.mqtt_make_topic("water_plant"))

        # fire off initial events. These are self submitting so each one
        # will submit the next job to the event queue.
        self.event_update_ntp(utime.time())
        current_time = utime.time()
        self.event_temperature(current_time)
        self.event_light(current_time)
        self.event_soil_moisture(current_time)
        self.schedule_pump_on(current_time)

    def __del__(self):
        self.mqtt_client.disconnect()

    def log(self, current_time, message):
        """Simple logging to stout."""
        if self.debug:
            print(utime.localtime(current_time), message)

    def mqtt_make_topic(self, *sub_topics):
        """Build mqtt topic strings."""
        return bytes("/".join((self.mqtt_root_topic,) + sub_topics), "utf-8")

    def mqtt_recieve(self, topic, msg):
        """Received messages from subscriptions will be delivered to this callback."""
        if topic == self.mqtt_make_topic("halt"):
            self.should_bail = True
        elif topic == self.mqtt_make_topic("water_plant"):
            self.event_pump_on(utime.time())

        self.log(utime.time(), topic + b': ' + msg)
    
    def event_schedule_dtime(self, dtime, event):
        """
            Add a new event to the queue to be triggered at specific date/time.
        
            Trigger date/time is specified in epoch seconds. i.e. response from
            ``utime.time()``.
        """
        self._events.append((dtime, event))

    def event_schedule_offset(self, offset_secs, event):
        """
            Add a new event to the queue to be triggered ``offset_secs`` from current time.
        """
        dtime_secs = utime.time() + offset_secs
        self._events.append((dtime_secs, event))

    def event_period(self, value):
        """Look-up period in event_periods, default if not found."""
        return self.event_periods.get(value, self.DEFAULT_EVENT_PERIOD)

    def run(self):
        """Main event loop. Will run loop until ``should_bail`` is True."""
        self.should_bail = False
        while not self.should_bail:
            self.loop()

    def loop(self):
        """The inner-event loop."""
        # Do house-keeping
        self.mqtt_client.check_msg()

        # Get current time
        current_time = utime.time()

        # loop over list of pending events
        triggered = []
        for i in range(len(self._events)):
            # if current time greater than event trigger time then
            # trigger event
            if self._events[i][0] <= current_time:
                # call the event callback.
                self._events[i][1](current_time)
                triggered.append(i)

        # remove handled events
        for i in triggered[::-1]:
            del self._events[i]       

        # sleep a bit
        utime.sleep(1)

    def event_update_ntp(self, current_time):
        """Sync RTC time from NTP."""
        self.log(current_time, 'Event: ntptime.settime')
        ntptime.settime()
        self.event_schedule_offset(self.event_period('ntp_sync'), self.event_update_ntp)

    def event_temperature(self, current_time):
        """Get temperature fields from BME280."""
        self.log(current_time, 'Event: temperature')
        temp, press, humid = self.sensor_bme280.read_compensated_data()
        self.mqtt_client.publish(self.mqtt_make_topic('temperature'), bytes(str(temp / 100), 'utf-8'))
        self.mqtt_client.publish(self.mqtt_make_topic('pressure'), bytes(str(press / 256 / 100), 'utf-8'))
        self.mqtt_client.publish(self.mqtt_make_topic('humidity'), bytes(str(humid / 1024), 'utf-8'))
        self.event_schedule_offset(self.event_period('temperature'), self.event_temperature)

    def event_light(self, current_time):
        """Get light fields from SI1145."""
        self.log(current_time, 'Event: light')
        self.mqtt_client.publish(self.mqtt_make_topic('uv'), bytes(str(self.sensor_si1145.read_uv), 'utf-8'))
        self.mqtt_client.publish(self.mqtt_make_topic('visible'), bytes(str(self.sensor_si1145.read_visible), 'utf-8'))
        self.mqtt_client.publish(self.mqtt_make_topic('ir'), bytes(str(self.sensor_si1145.read_ir), 'utf-8'))
        self.event_schedule_offset(self.event_period('light'), self.event_light)

    def event_soil_moisture(self, current_time):
        """Get current soil mositure value from ADC."""
        # Need to power up the sensor first. This is left powered off to prolong the
        # life of the sensor.
        self.log(current_time, 'Event: soil moisture')
        self.pin_soil_power.on()
        utime.sleep_ms(2000)
        value = self.sensor_adc.read(1)
        self.pin_soil_power.off()
        self.mqtt_client.publish(self.mqtt_make_topic('soil_moisture'), bytes(str(value), 'utf-8'))
        self.event_schedule_offset(self.event_period('soil_moisture'), self.event_soil_moisture)

    def event_pump_on(self, current_time):
        """Turn on pump, schedule it off."""
        self.log(current_time, 'Event: pump on')
        self.mqtt_client.publish(self.mqtt_make_topic('pump'), b'on')
        self.pin_pump.on()
        self.event_schedule_offset(self.event_period('pump_running'), self.event_pump_off)
        self.schedule_pump_on(current_time)

    def schedule_pump_on(self, current_time):
        next_trigger = next_water_time(current_time)
        self.log(current_time, "Scheduled next pump on at " + str(utime.localtime(next_trigger)))
        self.event_schedule_dtime(next_trigger, self.event_pump_on)

    def event_pump_off(self, current_time):
        """Turn off pump."""
        self.log(current_time, 'Event: pump off')
        self.mqtt_client.publish(self.mqtt_make_topic('pump'), b'off')
        self.pin_pump.off()

def main():
    import sensor_feed_config as config
    app = Application(
        config.network_ssid, config.network_password, config.mqtt_host, config.mqtt_root_topic,
        config.pin_soil_power, config.pin_pump, config.pin_scl, config.pin_sda,
        config.i2c_addr_bme280, config.event_periods, config.debug,
    )
    app.run()

# Run the program. Will stop and drop out to webrepl on mqtt message.
main()