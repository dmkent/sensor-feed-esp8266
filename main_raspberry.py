"""Main sensor feed loop"""
import random

from sensor_app.sensor_app_cpython import CPythonSensorApplication
from sensor_app.si7021 import SI7021
from sensor_app.pwm_fan import PwmFan


def fan_speed_for_temp(temp):
    """Determine fan PWM duty cycle for given temp."""
    if temp < 26:
        return 0
    elif temp < 28:
        return 40
    elif temp < 32:
        return 50
    elif temp < 35:
        return 80
    else:
        return 100


class Application(CPythonSensorApplication):
    DEFAULT_EVENT_PERIOD = 300 # seconds

    def __init__(self, mqtt_host, mqtt_root_topic, pin_fan_pwm, proc_path_si7120, event_periods, debug):
        """Setup the application"""
        mqtt_sub_topics = ["halt"]
        super(Application, self).__init__(mqtt_host, mqtt_root_topic, mqtt_sub_topics, event_periods, debug)
        
        # configure output pins
        self.pwm_fan = PwmFan(pin_fan_pwm, 10, 25)
        self.si7120 = SI7021() 

        self.init_events()                                                                                        

    def init_events(self):
        # fire off initial events. These are self submitting so each one
        # will submit the next job to the event queue.
        self.event_temperature(self.time())

    def __del__(self):
        self.mqtt_client.disconnect()

    def event_temperature(self, current_time):
        """Get temperature fields from SI7120."""
        self.log(current_time, 'Event: temperature')
        temp, humidity = self.si7120.read()
        fan_speed = fan_speed_for_temp(temp)
        self.pwm_fan.duty_cycle = fan_speed
        self.mqtt_client.publish(self.mqtt_make_topic('temperature'), temp)
        self.mqtt_client.publish(self.mqtt_make_topic('humidity'), humidity)
        self.mqtt_client.publish(self.mqtt_make_topic('fan_duty_cycle'), fan_speed)
        self.event_schedule_offset(self.event_period('temperature'), self.event_temperature)

def main():
    import sensor_feed_config as config
    app = Application(
        config.mqtt_host, config.mqtt_root_topic,
        config.pin_fan, config.proc_path_si7120, config.event_periods, config.debug,
    )
    app.run()

if __name__ == '__main__':
    # Run the program. Will stop and drop out to webrepl on mqtt message.
    main()
