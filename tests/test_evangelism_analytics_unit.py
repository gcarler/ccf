"""
Unit tests for evangelism_analytics.py — pure helper functions.
"""

from __future__ import annotations

from backend.api import evangelism_analytics as analytics


class TestNormalizeRol:
    def test_strips_accents(self):
        assert analytics._normalize_rol("Líder") == "lider"
        assert analytics._normalize_rol("Anfitrión") == "anfitrion"
        assert analytics._normalize_rol("Pastor") == "pastor"
        assert analytics._normalize_rol("") == ""


class TestRolToFunnelStage:
    def test_lider(self):
        assert analytics._rol_to_funnel_stage("Líder") == "lider"
        assert analytics._rol_to_funnel_stage("Pastor") == "lider"

    def test_colider(self):
        assert analytics._rol_to_funnel_stage("Colíder") == "colider"

    def test_anfitrion(self):
        assert analytics._rol_to_funnel_stage("Anfitrión") == "anfitrion"

    def test_asistente(self):
        assert analytics._rol_to_funnel_stage("Asistente") == "asistente"
        assert analytics._rol_to_funnel_stage("Colaborador") == "asistente"

    def test_visitante(self):
        assert analytics._rol_to_funnel_stage("Visitante") == "visitante"

    def test_unknown(self):
        assert analytics._rol_to_funnel_stage("Voluntario") == "personalizado"


class TestParsePeriod:
    def test_known(self):
        assert analytics._parse_period("7d") == 7
        assert analytics._parse_period("30d") == 30

    def test_unknown_defaults(self):
        assert analytics._parse_period("x") == 30


class TestDateRange:
    def test_returns_two_dates(self):
        start, end = analytics._date_range(30)
        assert end > start


class TestPrevRange:
    def test_returns_two_dates(self):
        start, end = analytics._prev_range(30)
        assert end > start


class TestDelta:
    def test_no_previous(self):
        assert analytics._delta(10, 0) == 100.0
        assert analytics._delta(0, 0) == 0.0

    def test_with_previous(self):
        assert analytics._delta(20, 10) == 100.0
        assert analytics._delta(10, 20) == -50.0
