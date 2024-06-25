import time

from gpiozero import PWMOutputDevice


class PwmFan:
    def __init__(self, pin, freq, duty_cycle):
        self.pwm = None

        self.pwm = PWMOutputDevice(pin, True, 0, freq)
        self.pwm.value = duty_cycle
        self.pwm.on()

    def __del__(self):
        if self.pwm is not None:
            self.pwm.off()

    @property
    def duty_cycle(self):
        return self.pwm.value

    @duty_cycle.setter
    def duty_cycle(self, value):
        if value < 60:
            # Low duty cycle fails to start fan. Give it a burst to get
            # spinning.
            self.pwm.value = 90
            time.sleep(3)
        self.pwm.value = value
