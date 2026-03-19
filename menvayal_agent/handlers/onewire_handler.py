"""1-Wire handler using w1thermsensor."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from w1thermsensor import W1ThermSensor
    _W1_AVAILABLE = True
except (ImportError, Exception):
    _W1_AVAILABLE = False
    logger.warning("w1thermsensor not available - 1-Wire operations will be simulated")


class OneWireHandler:
    def __init__(self):
        self._sensors: list = []
        if _W1_AVAILABLE:
            try:
                self._sensors = W1ThermSensor.get_available_sensors()
                logger.info("Found %d 1-Wire sensors", len(self._sensors))
            except Exception as e:
                logger.warning("Could not enumerate 1-Wire sensors: %s", e)

    def read(self, pin) -> Optional[float]:
        if not _W1_AVAILABLE or not self._sensors:
            logger.debug("Simulated 1-Wire read = 25.0")
            return 25.0
        try:
            # Use first available sensor (or match by pin if multiple)
            sensor = self._sensors[0]
            return sensor.get_temperature()
        except Exception as e:
            logger.error("1-Wire read error: %s", e)
            return None

    def write(self, pin, value):
        raise NotImplementedError("1-Wire is read-only")
