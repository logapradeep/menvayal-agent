"""GPIO read/write handler using RPi.GPIO."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    _GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    _GPIO_AVAILABLE = False
    logger.warning("RPi.GPIO not available - GPIO operations will be simulated")


_setup_pins: set[int] = set()


class GpioHandler:
    def _setup(self, pin, mode):
        gpio = pin.gpio_number
        if gpio is None:
            raise ValueError(f"No GPIO number for physical pin {pin.physical_pin}")
        if gpio not in _setup_pins:
            if _GPIO_AVAILABLE:
                GPIO.setup(gpio, mode)
            _setup_pins.add(gpio)

    def read(self, pin) -> Optional[int]:
        gpio = pin.gpio_number
        if gpio is None:
            return None
        self._setup(pin, GPIO.IN if _GPIO_AVAILABLE else None)
        if _GPIO_AVAILABLE:
            return GPIO.input(gpio)
        logger.debug("Simulated read pin GPIO%d = 0", gpio)
        return 0

    def write(self, pin, value) -> int:
        gpio = pin.gpio_number
        if gpio is None:
            raise ValueError(f"No GPIO number for physical pin {pin.physical_pin}")
        self._setup(pin, GPIO.OUT if _GPIO_AVAILABLE else None)
        out = 1 if value else 0
        if _GPIO_AVAILABLE:
            GPIO.output(gpio, out)
        logger.info("GPIO%d set to %d", gpio, out)
        return out
