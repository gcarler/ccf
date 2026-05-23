import json
import logging

import httpx

logger = logging.getLogger("AI-Engine")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3"


async def generate_ministerial_content(prompt: str, context: str = "") -> str:
    """Genera contenido utilizando Llama 3 local vía Ollama."""

    system_prompt = (
        "Eres un experto en gestión ministerial y comunicación de la iglesia CCF El Faro. "
        "Tu objetivo es ayudar a redactar descripciones de tareas, guiones y planes de acción claros, "
        "profesionales y con un tono honesto y cercano (Sello de Hijos). "
        "Responde siempre en español y de forma concisa."
    )

    full_prompt = f"{system_prompt}\n\nContexto: {context}\n\nInstrucción: {prompt}"

    if "pizarra" in prompt.lower() or "diagrama" in prompt.lower():
        full_prompt += "\n\nResponde únicamente con un objeto JSON que contenga una lista de 'elements' con tipo (rect, circle, text), posición (left, top), dimensiones y color. No añadas explicaciones."

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={"model": MODEL_NAME, "prompt": full_prompt, "stream": False},
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("response", "No se recibió respuesta de la IA.")
            else:
                return f"Error de Ollama: {response.status_code}"
    except Exception as e:
        logger.error(f"Fallo en conexión con Ollama: {e}")
        return "Error de conexión: Asegúrate de que Ollama esté corriendo."
