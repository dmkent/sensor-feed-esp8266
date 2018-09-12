import time

from RPi import GPIO


GPIO.setmode(GPIO.BCM)


class PwmFan:
    def __init__(self, pin, freq, duty_cycle):
        self.pwm = None

        GPIO.setup(pin, GPIO.OUT)
        self.pwm = GPIO.PWM(pin, freq)
        
        self.pwm.start(duty_cycle)
        self._duty_cycle = duty_cycle

    def __del__(self):
        if self.pwm is not None:
            self.pwm.stop()

    @property
    def duty_cycle(self):
        return self._duty_cycle

    @duty_cycle.setter
    def duty_cycle(self, value):
        if value < 60:
            # Low duty cycle fails to start fan. Give it a burst to get
            # spinning.
            self.pwm.ChangeDutyCycle(90)
            time.sleep(3)
        self.pwm.ChangeDutyCycle(value)
        self._duty_cycle = value
