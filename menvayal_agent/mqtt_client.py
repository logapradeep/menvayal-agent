"""MQTT client for connecting to HiveMQ Cloud."""

import json
import logging
import ssl
import time
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from . import __version__
from .config import MqttConfig

logger = logging.getLogger(__name__)


class MenvayalMqttClient:
    """Persistent MQTT connection to HiveMQ Cloud."""

    def __init__(self, config: MqttConfig):
        self.config = config
        self._client: Optional[mqtt.Client] = None
        self._on_command: Optional[Callable[[dict], None]] = None
        self._connected = False

    def set_command_handler(self, handler: Callable[[dict], None]) -> None:
        self._on_command = handler

    def connect(self) -> None:
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv5,
        )

        if self.config.tls:
            self._client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)

        self._client.username_pw_set(self.config.username, self.config.password)

        # Set Last Will and Testament — broker publishes this when client
        # disconnects ungracefully (power loss, crash, network drop).
        will_payload = json.dumps({
            "type": "status",
            "payload": {
                "nodeUid": self.payload_node_uid,
                "online": False,
                "uptime": 0,
            },
        })
        self._client.will_set(
            self.config.status_topic,
            payload=will_payload,
            qos=1,
            retain=True,
        )

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        logger.info("Connecting to MQTT broker %s:%d", self.config.broker, self.config.port)
        self._client.connect(self.config.broker, self.config.port, keepalive=30)
        self._client.loop_start()

    def disconnect(self) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def payload_node_uid(self) -> str:
        return self.config.node_uid or self.config.username

    def publish_telemetry(self, readings: list[dict]) -> None:
        if not self._client or not self._connected:
            logger.warning("Cannot publish telemetry: not connected")
            return

        payload = json.dumps({
            "nodeUid": self.payload_node_uid,
            "readings": readings,
            "timestamp": int(time.time() * 1000),
        })

        self._client.publish(
            self.config.telemetry_topic,
            payload,
            qos=1,
        )

    def publish_status(self, online: bool, uptime: int, firmware_version: str = __version__) -> None:
        if not self._client or not self._connected:
            logger.warning("Cannot publish status: not connected")
            return

        payload = json.dumps({
            "nodeUid": self.payload_node_uid,
            "online": online,
            "uptime": uptime,
            "firmwareVersion": firmware_version,
        })

        self._client.publish(
            self.config.status_topic,
            payload,
            qos=1,
        )

    def publish_lora_uplink(self, uplink_data: dict) -> None:
        """Publish a LoRa uplink payload to the cloud for processing."""
        if not self._client or not self._connected:
            logger.warning("Cannot publish LoRa uplink: not connected")
            return

        payload = json.dumps({
            "nodeUid": self.payload_node_uid,
            "type": "lora_uplink",
            "data": uplink_data,
            "timestamp": int(time.time() * 1000),
        })

        self._client.publish(
            self.config.telemetry_topic,
            payload,
            qos=1,
        )
        logger.debug("Published LoRa uplink from devAddr=%s", uplink_data.get("devAddr", "?"))

    def publish_lora_event(self, event: dict) -> None:
        """Publish a LoRa network event (join, leave, error) to the cloud."""
        if not self._client or not self._connected:
            logger.warning("Cannot publish LoRa event: not connected")
            return

        payload = json.dumps({
            "nodeUid": self.payload_node_uid,
            "type": "lora_event",
            "event": event,
            "timestamp": int(time.time() * 1000),
        })

        self._client.publish(
            self.config.status_topic,
            payload,
            qos=1,
        )
        logger.debug("Published LoRa event: %s", event.get("type", "unknown"))

    def publish_command_ack(
        self,
        command_id: str,
        status: str,
        applied_value: Optional[object] = None,
        error: Optional[str] = None,
    ) -> None:
        if not self._client or not self._connected:
            return

        payload: dict = {
            "nodeUid": self.payload_node_uid,
            "commandId": command_id,
            "status": status,
        }
        if applied_value is not None:
            payload["appliedValue"] = applied_value
        if error:
            payload["error"] = error

        # Publish ack on status topic (backend listens for commandAck type)
        self._client.publish(
            self.config.status_topic,
            json.dumps({"type": "commandAck", "payload": payload}),
            qos=1,
        )

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self._connected = True
            logger.info("Connected to MQTT broker")
            client.subscribe(self.config.commands_topic, qos=1)
            logger.info("Subscribed to %s", self.config.commands_topic)
        else:
            logger.error("MQTT connection failed with code %d", rc)

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        self._connected = False
        if rc != 0:
            logger.warning("Unexpected MQTT disconnect (rc=%d), will auto-reconnect", rc)

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            logger.debug("Received command: %s", payload)
            if self._on_command:
                self._on_command(payload)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in MQTT message: %s", msg.payload)
        except Exception as e:
            logger.error("Error handling MQTT message: %s", e)
