"""UART handler using pyserial."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import serial
    _SERIAL_AVAILABLE = True
except ImportError:
    _SERIAL_AVAILABLE = False
    logger.warning("pyserial not available - UART operations will be simulated")


class UartHandler:
    def __init__(self, port: str = "/dev/serial0", baudrate: int = 9600):
        self._serial = None
        if _SERIAL_AVAILABLE:
            try:
                self._serial = serial.Serial(port, baudrate, timeout=1)
            except Exception as e:
                logger.warning("Could not open UART port %s: %s", port, e)

    def read(self, pin) -> Optional[str]:
        if not self._serial:
            logger.debug("Simulated UART read")
            return None
        try:
            if self._serial.in_waiting:
                return self._serial.readline().decode("utf-8").strip()
            return None
        except Exception as e:
            logger.error("UART read error: %s", e)
            return None

    def write(self, pin, value) -> str:
        data = str(value)
        if not self._serial:
            logger.debug("Simulated UART write: %s", data)
            return data
        try:
            self._serial.write((data + "\n").encode("utf-8"))
            return data
        except Exception as e:
            logger.error("UART write error: %s", e)
            raise
