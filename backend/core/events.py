from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from importlib import import_module
from typing import Any, Dict

from .config import get_settings


log = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class DomainEvent:
    name: str
    payload: Dict[str, Any]

    def to_json(self) -> bytes:
        return json.dumps({"name": self.name, "payload": self.payload}).encode("utf-8")


class EventBus:
    def __init__(self):
        try:
            kafka_module = import_module("kafka")
            producer_cls = getattr(kafka_module, "KafkaProducer")
        except Exception:  # pragma: no cover
            log.warning("Kafka library not installed; event bus disabled")
            self._producer = None
            return

        try:
            self._producer = producer_cls(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        except Exception as exc:  # pragma: no cover
            log.warning("Kafka unavailable: %s", exc)
            self._producer = None

    def publish(self, topic: str, event: DomainEvent) -> None:
        if not self._producer:
            log.debug("Kafka producer not ready; dropping event %s", event.name)
            return
        try:
            self._producer.send(topic, asdict(event))
            self._producer.flush()
        except Exception as exc:  # pragma: no cover
            log.warning("Kafka send error: %s", exc)


event_bus = EventBus()
