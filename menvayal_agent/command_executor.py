"""Routes incoming commands to the appropriate hardware handler."""

import logging
from typing import Optional

from .config import AgentConfig, PinConfig
from .http_reporter import HttpReporter
from .mqtt_client import MenvayalMqttClient

logger = logging.getLogger(__name__)

# Protocol → handler mapping (lazy-loaded)
_handlers: dict = {}


def _get_handler(protocol: str):
    """Lazy-load the appropriate handler for a pin protocol."""
    if protocol in _handlers:
        return _handlers[protocol]

    handler = None
    try:
        if protocol in ("gpio_input", "gpio_output"):
            from .handlers.gpio_handler import GpioHandler
            handler = GpioHandler()
        elif protocol in ("i2c_sda", "i2c_scl"):
            from .handlers.i2c_handler import I2CHandler
            handler = I2CHandler()
        elif protocol in ("spi_mosi", "spi_miso", "spi_sck", "spi_cs"):
            from .handlers.spi_handler import SpiHandler
            handler = SpiHandler()
        elif protocol in ("uart_tx", "uart_rx"):
            from .handlers.uart_handler import UartHandler
            handler = UartHandler()
        elif protocol == "oneWire":
            from .handlers.onewire_handler import OneWireHandler
            handler = OneWireHandler()
        elif protocol == "pwm":
            from .handlers.pwm_handler import PwmHandler
            handler = PwmHandler()
    except ImportError as e:
        logger.warning("Handler for %s not available: %s", protocol, e)

    _handlers[protocol] = handler
    return handler


def _find_pin(config: AgentConfig, command: dict) -> Optional[PinConfig]:
    """Find the pin config matching a command's gpio/pin number."""
    gpio = command.get("gpioNumber")
    pin_num = command.get("pinNumber")

    for pin in config.pins:
        if gpio is not None and pin.gpio_number == gpio:
            return pin
        if pin_num is not None and pin.physical_pin == pin_num:
            return pin

    return None


def _publish_ack(
    mqtt_client: MenvayalMqttClient,
    http_reporter: Optional[HttpReporter],
    command_id: str,
    status: str,
    applied_value=None,
    error: Optional[str] = None,
) -> None:
    mqtt_client.publish_command_ack(
        command_id,
        status,
        applied_value=applied_value,
        error=error,
    )
    if http_reporter:
        http_reporter.report_command_ack(
            command_id,
            status,
            applied_value=applied_value,
            error=error,
        )


def execute(
    config: AgentConfig,
    mqtt_client: MenvayalMqttClient,
    command: dict,
    http_reporter: Optional[HttpReporter] = None,
) -> None:
    """Execute a command received from MQTT."""
    command_id = command.get("commandId", "unknown")
    cmd_type = command.get("type", "setPower")
    value = command.get("value")
    protocol = command.get("pinProtocol")

    logger.info(
        "Executing command %s: type=%s, value=%s, protocol=%s",
        command_id, cmd_type, value, protocol
    )

    # Acknowledge receipt
    _publish_ack(mqtt_client, http_reporter, command_id, "acknowledged")

    pin = _find_pin(config, command)
    if not pin:
        error = f"No matching pin for command (gpio={command.get('gpioNumber')}, pin={command.get('pinNumber')})"
        logger.error(error)
        _publish_ack(mqtt_client, http_reporter, command_id, "failed", error=error)
        return

    # Use protocol from command or fall back to pin config
    effective_protocol = protocol or pin.protocol
    handler = _get_handler(effective_protocol)

    if not handler:
        error = f"No handler available for protocol {effective_protocol}"
        logger.error(error)
        _publish_ack(mqtt_client, http_reporter, command_id, "failed", error=error)
        return

    try:
        _publish_ack(mqtt_client, http_reporter, command_id, "executing")

        if cmd_type == "setPower":
            applied = handler.write(pin, 1 if value else 0)
        elif cmd_type == "setPortValue":
            applied = handler.write(pin, value)
        elif cmd_type == "readSensor":
            applied = handler.read(pin)
        else:
            error = f"Unknown command type: {cmd_type}"
            logger.error(error)
            _publish_ack(mqtt_client, http_reporter, command_id, "failed", error=error)
            return

        _publish_ack(mqtt_client, http_reporter, command_id, "completed", applied_value=applied)
        logger.info("Command %s completed, applied=%s", command_id, applied)

    except Exception as e:
        error = f"Execution error: {e}"
        logger.error(error)
        _publish_ack(mqtt_client, http_reporter, command_id, "failed", error=error)
