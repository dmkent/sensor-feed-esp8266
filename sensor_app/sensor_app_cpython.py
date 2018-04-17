"""Abstract feed handler."""
import time

import paho.mqtt.client as mqtt

from sensor_app.sensor_app_base import SensorApplication


class CPythonSensorApplication(SensorApplication):
    def __init__(self, mqtt_host, mqtt_root_topic, mqtt_sub_topics, *args, **kwargs):
        """Setup the application"""
        super(CPythonSensorApplication, self).__init__(*args, **kwargs)
        self.mqtt_root_topic = mqtt_root_topic
        self.mqtt_sub_topics = mqtt_sub_topics
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.mqtt_on_connect
        self.mqtt_client.on_message = self.mqtt_recieve
        self.mqtt_client.connect(mqtt_host, 1883, 60)

    def time(self):
        """Get current time."""
        return time.time()

    def sleep(self, seconds):
        """Delay for seconds."""
        return time.sleep(seconds)

    def localtime(self, timeval):
        """Format timeval as localtime struct."""
        return time.localtime(timeval)

    def mqtt_make_topic(self, *sub_topics):
        """Build mqtt topic strings."""
        return "/".join((self.mqtt_root_topic,) + sub_topics)

    def mqtt_on_connect(self, client, userdata, flags, rc):
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        for topic in self.mqtt_sub_topics:
            self.mqtt_client.subscribe(self.mqtt_make_topic(topic))

    def mqtt_recieve(self, client, userdata, msg):
        """Received messages from subscriptions will be delivered to this callback."""
        if msg.topic == self.mqtt_make_topic("halt"):
            self.should_bail = True

        self.log(self.time(), msg.topic + ': ' + msg.payload.decode('utf-8'))

    def pre_event_handler(self):
        self.mqtt_client.loop()