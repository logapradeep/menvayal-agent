"""I2C handler using smbus2."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import smbus2
    _I2C_AVAILABLE = True
except ImportError:
    _I2C_AVAILABLE = False
    logger.warning("smbus2 not available - I2C operations will be simulated")


class I2CHandler:
    def __init__(self, bus_number: int = 1):
        self._bus = smbus2.SMBus(bus_number) if _I2C_AVAILABLE else None

    def read(self, pin) -> Optional[int]:
        if not self._bus:
            logger.debug("Simulated I2C read")
            return 0
        # Default: read a single byte from address based on pin
        address = pin.gpio_number or 0x48
        try:
            return self._bus.read_byte(address)
        except Exception as e:
            logger.error("I2C read error at 0x%02x: %s", address, e)
            return None

    def write(self, pin, value) -> int:
        if not self._bus:
            logger.debug("Simulated I2C write: %s", value)
            return int(value)
        address = pin.gpio_number or 0x48
        try:
            self._bus.write_byte(address, int(value))
            return int(value)
        except Exception as e:
            logger.error("I2C write error at 0x%02x: %s", address, e)
            raise
