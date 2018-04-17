import fcntl
import os
import struct
import time

I2C_SLAVE = 0x0703
I2C_CHANNEL = 1
ADDR = 0x40
READ_TEMP = 0xF3
READ_HUM = 0xF5


class SI7021:
    def __init__(self):
        # Get I2C bus
        self.i2c = os.open(f'/dev/i2c-{I2C_CHANNEL}', os.O_RDWR)
        fcntl.ioctl(self.i2c, I2C_SLAVE, ADDR)

    def read(self):
        # SI7021 address, 0x40(64)
        #		0xF5(245)	Select Relative Humidity NO HOLD master mode
        os.write(self.i2c, struct.pack('B', READ_HUM))
        time.sleep(0.3)
        # SI7021 address, 0x40(64)
        # Read data back, 2 bytes, Humidity MSB first, 1 byte CRC
        msg = os.read(self.i2c, 3)
        data = struct.unpack('>H', msg[:2])[0]

        # Convert the data
        humidity = (data * 125 / 65536.0) - 6

        time.sleep(0.3)

        # SI7021 address, 0x40(64)
        #		0xF3(243)	Select temperature NO HOLD master mode
        os.write(self.i2c, struct.pack('B', READ_TEMP))
        time.sleep(0.3)
        # SI7021 address, 0x40(64)
        # Read data back, 2 bytes, Temperature MSB first, 1 byte CRC
        msg = os.read(self.i2c, 3)
        data = struct.unpack('>H', msg[:2])[0]

        # Convert the data
        temp = (data * 175.72 / 65536.0) - 46.85

        return temp, humidity
