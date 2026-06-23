from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import Any, Dict

from backend.core.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class DomainEvent:
    name: str
    payload: Dict[str, Any]

    def to_json(self) -> bytes:
        return json.dumps({"name": self.name, "payload": self.payload}).encode("utf-8")


class EventBus:
    """Publicador de eventos del dominio.

    Por defecto opera en modo no-op (no publica en ningún lado).
    Para activar Redis: usa `RedisEventBus`.
    Para activar Kafka: instala ``kafka-python`` y configura ``KAFKA_BOOTSTRAP_SERVERS``.
    """

    def publish(self, topic: str, event: DomainEvent) -> None:
        pass


class RedisEventBus(EventBus):
    """Publica eventos usando Redis Pub/Sub (no requiere infraestructura adicional)."""

    def __init__(self):
        from backend.core.cache import get_redis

        self._redis = get_redis()

    def publish(self, topic: str, event: DomainEvent) -> None:
        try:
            self._redis.publish(topic, json.dumps(asdict(event)))
        except Exception as exc:
            log.warning("Redis publish error: %s", exc)


class KafkaEventBus(EventBus):
    """Publica eventos usando Kafka/Redpanda."""

    def __init__(self):
        from importlib import import_module

        try:
            kafka_module = import_module("kafka")
            producer_cls = getattr(kafka_module, "KafkaProducer")
            self._producer = producer_cls(
                bootstrap_servers=settings.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        except Exception as exc:
            log.warning("Kafka unavailable (%s); KafkaEventBus será no-op", exc)
            self._producer = None

    def publish(self, topic: str, event: DomainEvent) -> None:
        if not self._producer:
            return
        try:
            self._producer.send(topic, asdict(event))
            self._producer.flush()
        except Exception as exc:
            log.warning("Kafka send error: %s", exc)


# Instancia global: comienza como no-op.
# Las aplicaciones pueden reemplazarla con RedisEventBus o KafkaEventBus según configuración.
event_bus: EventBus = EventBus()


def configure_event_bus() -> None:
    """Configura el event_bus global según la infraestructura disponible.

    Prioridad: Redis > Kafka > no-op.
    """
    global event_bus
    if settings.redis_url:
        try:
            bus = RedisEventBus()
            bus.publish("__test", DomainEvent("healthcheck", {}))
            event_bus = bus
            log.info("EventBus configurado con Redis")
            return
        except Exception:
            log.warning("Redis no disponible para EventBus, probando Kafka...")

    if settings.kafka_bootstrap_servers:
        try:
            bus = KafkaEventBus()
            if bus._producer:
                event_bus = bus
                log.info("EventBus configurado con Kafka")
                return
        except Exception:
            log.warning("Kafka no disponible para EventBus")

    event_bus = EventBus()
    log.info("EventBus en modo no-op (sin Redis ni Kafka)")
