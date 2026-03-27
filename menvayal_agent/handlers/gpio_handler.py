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


_setup_pins: dict[int, int] = {}  # gpio -> mode (GPIO.IN or GPIO.OUT)
_output_values: dict[int, int] = {}  # gpio -> last written logical level


class GpioHandler:
    def _setup(self, pin, mode):
        gpio = pin.gpio_number
        if gpio is None:
            raise ValueError(f"No GPIO number for physical pin {pin.physical_pin}")
        if _setup_pins.get(gpio) != mode:
            if _GPIO_AVAILABLE:
                GPIO.setup(gpio, mode)
            _setup_pins[gpio] = mode

    def read(self, pin) -> Optional[int]:
        gpio = pin.gpio_number
        if gpio is None:
            return None
        protocol = getattr(pin, "protocol", "")
        mode = GPIO.OUT if _GPIO_AVAILABLE and protocol == "gpio_output" else (
            GPIO.IN if _GPIO_AVAILABLE else None
        )
        self._setup(pin, mode)
        if _GPIO_AVAILABLE:
            return GPIO.input(gpio)
        simulated = _output_values.get(gpio, 0)
        logger.debug("Simulated read pin GPIO%d = %d", gpio, simulated)
        return simulated

    def write(self, pin, value) -> int:
        gpio = pin.gpio_number
        if gpio is None:
            raise ValueError(f"No GPIO number for physical pin {pin.physical_pin}")
        self._setup(pin, GPIO.OUT if _GPIO_AVAILABLE else None)
        out = 1 if value else 0
        if _GPIO_AVAILABLE:
            GPIO.output(gpio, out)
        _output_values[gpio] = out
        logger.info("GPIO%d set to %d", gpio, out)
        return out
