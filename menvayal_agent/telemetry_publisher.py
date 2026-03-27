"""Periodic telemetry publishing for readable inputs and controllable outputs."""

import logging
import threading
from typing import Optional

from .config import AgentConfig
from .mqtt_client import MenvayalMqttClient

logger = logging.getLogger(__name__)


class TelemetryPublisher:
    """Reads configured telemetry sources periodically and publishes telemetry."""

    def __init__(self, config: AgentConfig, mqtt_client: MenvayalMqttClient):
        self.config = config
        self.mqtt_client = mqtt_client
        self._timer: Optional[threading.Timer] = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._publish_cycle()
        logger.info(
            "Telemetry publisher started (interval=%ds)",
            self.config.telemetry.interval_seconds,
        )

    def stop(self) -> None:
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None

    def _schedule_next(self) -> None:
        if not self._running:
            return
        self._timer = threading.Timer(
            self.config.telemetry.interval_seconds,
            self._publish_cycle,
        )
        self._timer.daemon = True
        self._timer.start()

    def _publish_cycle(self) -> None:
        try:
            readings = self._read_all_telemetry_sources()
            if readings:
                self.mqtt_client.publish_telemetry(readings)
                logger.debug("Published %d telemetry readings", len(readings))
        except Exception as e:
            logger.error("Telemetry publish error: %s", e)
        finally:
            self._schedule_next()

    def _read_all_telemetry_sources(self) -> list[dict]:
        """Read all telemetry-capable pins and return telemetry readings."""
        from .command_executor import _get_handler

        readings = []
        readable_protocols = {
            "gpio_input",
            "analog_input",
            "oneWire",
            "gpio_output",
            "pwm",
        }

        for pin in self.config.pins:
            if pin.protocol not in readable_protocols:
                continue

            handler = _get_handler(pin.protocol)
            if not handler:
                continue

            try:
                value = handler.read(pin)
                if value is not None:
                    source_key = pin.label or f"pin_{pin.physical_pin}"
                    readings.append({
                        "sourceKey": source_key,
                        "value": value,
                    })
            except Exception as e:
                logger.debug("Failed to read pin %d: %s", pin.physical_pin, e)

        return readings
