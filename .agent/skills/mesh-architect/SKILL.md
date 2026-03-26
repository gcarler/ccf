---
name: mesh-architect
description: Asesora y asiste en el diseño y la conexión de nodos en la malla (mesh) del sistema, optimizando el flujo de eventos y la comunicación entre agentes.
---

# Mesh Architect Skill

Este skill permite al agente actuar como un arquitecto de sistemas distribuido dentro del ecosistema CCF.

## When to use this skill
- Cuando se necesite añadir un nuevo agente al ecosistema.
- Para debugear problemas de comunicación en el `AgentBus`.
- Para mapear dependencias entre servicios y nodos.

## How to use it
1. **Analizar Topología**: Consultar el `NodeRegistry` para ver los nodos activos.
2. **Diseñar Eventos**: Definir payloads y tópicos para nuevos eventos siguiendo el estándar de la plataforma.
3. **Auditar Flujos**: Usar logs de `NeuralLog` para identificar cuellos de botella en la comunicación.

## Resources & Integration
- **Mesh Connection:** `NodeRegistry`, `AgentBus`, `NeuralLog`.
- **Standards:** Seguir el patrón de diseño de eventos asíncronos implementado en `shared/mesh`.
