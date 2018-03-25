"""Main sensor feed loop"""
import machine
import utime
from umqtt.simple import MQTTClient

import ntptime

import bme280                                                                                                                                                                                                                                                        
import si1145 
import ads1x15

import sensor_feed_config as config

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


class Application:
    def __init__(self, mqtt_host):
        """Setup the application"""
        self._events = []

        self.should_bail = False
        self.debug = True

        # configure mqtt cloent
        self.mqtt_client = MQTTClient("umqtt_client", mqtt_host)
        self.mqtt_client.set_callback(self.recieve_mqtt)
        self.mqtt_client.connect()

        # configure output pins
        self.pin_soil_power = machine.Pin(13, machine.Pin.OUT)
        self.pin_pump = machine.Pin(12, machine.Pin.OUT)

        # set up i2c
        self.i2c = machine.I2C(scl=machine.Pin(5), sda=machine.Pin(4))
        self.sensor_bme280 = bme280.BME280(i2c=self.i2c, address=119)    
        self.sensor_si1145 = si1145.SI1145(i2c=self.i2c)      
        self.sensor_adc = ads1x15.ADS1015(self.i2c)                                                                                                 

        # topic to trigger event loop end
        self.mqtt_client.subscribe(b"plant/halt")

        # setup ntp, also schedules next event
        self.event_update_ntp(utime.time())
        current_time = utime.time()
        self.event_test(current_time)
        self.event_temperature(current_time)
        self.event_light(current_time)
        self.event_soil_moisture(current_time)
        self.schedule_pump_on(current_time)

    def __del__(self):
        self.mqtt_client.disconnect()

    def log(self, current_time, message):
        if self.debug:
            print(utime.localtime(current_time), message)

    # Received messages from subscriptions will be delivered to this callback
    def recieve_mqtt(self, topic, msg):
        if topic == b"plant/halt":
            self.should_bail = True

        print((topic, msg))
    
    def schedule_event_dtime(self, dtime, event):
        self._events.append((dtime, event))

    def schedule_event_offset(self, offset_secs, event):
        dtime_secs = utime.time() + offset_secs
        self._events.append((dtime_secs, event))

    def run(self):
        """Main event loop."""
        self.should_bail = False
        while not self.should_bail:
            self.loop()

    def loop(self):
        # Do house-keeping
        self.mqtt_client.check_msg()

        # Get current time
        current_time = utime.time()

        # loop over list of events
        triggered = []
        for i in range(len(self._events)):
            # if current time greater than event next trigger time then
            # trigger event
            if self._events[i][0] <= current_time:
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
        self.schedule_event_offset(60, self.event_update_ntp)

    def event_test(self, current_time):
        self.log(current_time, 'Event: test')
        self.schedule_event_offset(5, self.event_test)

    def event_temperature(self, current_time):
        """Get temperature fields from BME280."""
        self.log(current_time, 'Event: temperature')
        temp, press, humid = self.sensor_bme280.read_compensated_data()
        self.mqtt_client.publish(b'plant/temperature', bytes(str(temp / 100), 'utf-8'))
        self.mqtt_client.publish(b'plant/pressure', bytes(str(press / 256 / 100), 'utf-8'))
        self.mqtt_client.publish(b'plant/humidity', bytes(str(humid / 1024), 'utf-8'))
        self.schedule_event_offset(300, self.event_temperature)

    def event_light(self, current_time):
        """Get light fields from SI1145."""
        self.log(current_time, 'Event: light')
        self.mqtt_client.publish(b'plant/uv', bytes(str(self.sensor_si1145.read_uv), 'utf-8'))
        self.mqtt_client.publish(b'plant/visible', bytes(str(self.sensor_si1145.read_visible), 'utf-8'))
        self.mqtt_client.publish(b'plant/ir', bytes(str(self.sensor_si1145.read_ir), 'utf-8'))
        self.schedule_event_offset(300, self.event_light)

    def event_soil_moisture(self, current_time):
        """Get current soil mositure value from ADC."""
        # Need to power up the sensor first. This is left powered off to prolong the
        # life of the sensor.
        self.log(current_time, 'Event: soil moisture')
        self.pin_soil_power.on()
        utime.sleep_ms(2000)
        value = self.sensor_adc.read(1)
        self.pin_soil_power.off()
        self.mqtt_client.publish(b'plant/soil_moisture', bytes(str(value), 'utf-8'))
        self.schedule_event_offset(600, self.event_soil_moisture)

    def event_pump_on(self, current_time):
        """Turn on pump, schedule it off."""
        self.log(current_time, 'Event: pump on')
        self.mqtt_client.publish(b'plant/pump', b'on')
        self.pin_pump.on()
        self.schedule_event_offset(40, self.event_pump_off)
        self.schedule_pump_on(current_time)

    def schedule_pump_on(self, current_time):
        next_trigger = next_water_time(current_time)
        self.log(current_time, "Scheduled next pump on at " + str(utime.localtime(next_trigger)))
        self.schedule_event_dtime(next_trigger, self.event_pump_on)

    def event_pump_off(self, current_time):
        """Turn off pump."""
        self.log(current_time, 'Event: pump off')
        self.mqtt_client.publish(b'plant/pump', b'off')
        self.pin_pump.off()

def main():
    app = Application(config.mqtt_host)
    app.run()