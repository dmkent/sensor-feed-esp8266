"""Abstract feed handler."""
import utime

from sensor_app.sensor_app_base import SensorApplication


class UPythonSensorApplication(SensorApplication):
    def __init__(self, *args, **kwargs):
        """Setup the application"""
        super(UPythonSensorApplication, self).__init__(*args, **kwargs)

    def time(self):
        """Get current time."""
        return utime.time()

    def sleep(self, seconds):
        """Delay for seconds."""
        return utime.sleep(seconds)

    def localtime(self, timeval):
        """Format timeval as localtime struct."""
        return utime.localtime(timeval)