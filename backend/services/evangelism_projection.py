"""Servicio canonico de proyeccion temporal para evangelismo."""

from __future__ import annotations

from backend.models_evangelism import FrecuenciaEnum
from backend.services.calculo_sesiones import calcular_sesiones

FRECUENCIAS = {
    FrecuenciaEnum.SEMANAL.value: "Semanal",
    FrecuenciaEnum.QUINCENAL.value: "Quincenal",
    FrecuenciaEnum.MENSUAL.value: "Mensual",
    FrecuenciaEnum.BIMENSUAL.value: "Bimensual",
    FrecuenciaEnum.TRIMESTRAL.value: "Trimestral",
    FrecuenciaEnum.SEMESTRAL.value: "Semestral",
    FrecuenciaEnum.ANUAL.value: "Anual",
}

proyectar_sesiones = calcular_sesiones

__all__ = ["FRECUENCIAS", "proyectar_sesiones"]
