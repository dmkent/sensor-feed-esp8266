import os
import unittest
from unittest import mock

from sensor_app.sensor_app_cpython import CPythonSensorApplication


class SimpleApp(CPythonSensorApplication):
    def init_events(self):
        self.mock_event = mock.Mock()

        self.event_schedule_offset(2, self.mock_event)
        self.event_schedule_offset(3, self.mock_event)
        self.event_schedule_offset(8, self.mock_event)
        self.event_schedule_offset(10, self.bail)

    def bail(self, current_time):
        self.should_bail = True
        
class SensorAppTestCase(unittest.TestCase):
    def test_single(self):
        host = os.getenv('MQTT_HOST', '::1')
        app = SimpleApp(host, 'mqtt', {}, True)
        app.run()

        self.assertEqual(app.mock_event.call_count, 3)