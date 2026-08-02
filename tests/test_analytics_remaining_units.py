"""Cover remaining uncovered pure functions in evangelism_analytics.py."""
from __future__ import annotations

import math
from datetime import date, datetime

from backend.api import evangelism_analytics as analytics


class TestSemaforoTOF:
    def test_saturado(self):
        assert analytics._semaforo_tof(90) == "SATURADO"
        assert analytics._semaforo_tof(86) == "SATURADO"
        assert analytics._semaforo_tof(100) == "SATURADO"

    def test_saludable(self):
        assert analytics._semaforo_tof(70) == "SALUDABLE"
        assert analytics._semaforo_tof(60) == "SALUDABLE"
        assert analytics._semaforo_tof(85) == "SALUDABLE"

    def test_bajo(self):
        assert analytics._semaforo_tof(0) == "BAJO"
        assert analytics._semaforo_tof(30) == "BAJO"
        assert analytics._semaforo_tof(59) == "BAJO"


class TestShannonEntropy:
    def test_zero_total(self):
        assert analytics._shannon_entropy({}) == 0.0

    def test_single(self):
        assert analytics._shannon_entropy({"a": 10}) == 0.0

    def test_uniform(self):
        result = analytics._shannon_entropy({"a": 5, "b": 5})
        expected = -sum((5/10) * math.log(5/10) for _ in ["a", "b"])
        assert result == round(expected, 3)

    def test_skewed(self):
        result = analytics._shannon_entropy({"a": 1, "b": 9})
        assert 0 < result < 1.0


class TestAgeBucket:
    def test_none(self):
        assert analytics._age_bucket(None) == "Desconocido"

    def test_children(self):
        assert analytics._age_bucket(date(2020, 1, 1)) == "Niños"

    def test_young(self):
        assert analytics._age_bucket(date(2005, 1, 1)) == "Jóvenes"

    def test_young_adult(self):
        assert analytics._age_bucket(date(1995, 1, 1)) == "Jóvenes Adultos"

    def test_adult(self):
        assert analytics._age_bucket(date(1985, 1, 1)) == "Adultos"

    def test_older(self):
        assert analytics._age_bucket(date(1980, 1, 1)) == "Adultos"

    def test_elderly(self):
        assert analytics._age_bucket(date(1950, 1, 1)) == "Adultos Mayores"

    def test_datetime_input(self):
        assert analytics._age_bucket(datetime(2020, 6, 15)) == "Niños"


class TestAttended:
    def test_present(self):
        assert analytics._attended("ASISTIO") is True
        assert analytics._attended("Presente") is True
        assert analytics._attended("presente") is True

    def test_absent(self):
        assert analytics._attended("FALTO") is False
        assert analytics._attended("AUSENTE") is False

    def test_none(self):
        assert analytics._attended(None) is False


class TestIsPrimeraVez:
    def test_es_primera_vez_true(self):
        mock = type("A", (), {"es_primera_vez": True, "estado": "ASISTIO"})()
        assert analytics._is_primera_vez(mock) is True

    def test_es_primera_vez_false_with_first_time(self):
        mock = type("A", (), {"es_primera_vez": False, "estado": "first_time"})()
        assert analytics._is_primera_vez(mock) is True

    def test_not_first(self):
        mock = type("A", (), {"es_primera_vez": False, "estado": "ASISTIO"})()
        assert analytics._is_primera_vez(mock) is False

    def test_state_first_time_excused(self):
        mock = type("A", (), {"es_primera_vez": False, "estado": "EXCUSADO"})()
        assert analytics._is_primera_vez(mock) is False


class TestBucketLabel:
    def test_weeks(self):
        assert analytics._bucket_label("2026-W1", True) == "Sem 1"
        assert analytics._bucket_label("2026-W12", True) == "Sem 12"

    def test_month(self):
        result = analytics._bucket_label("2026-07", False)
        assert "Jul" in result and "26" in result

    def test_exception(self):
        """Line 400-402: invalid key triggers except block."""
        assert analytics._bucket_label("not-a-date", False) == "not-a-date"
        assert analytics._bucket_label("", False) == ""


class TestRolToFunnelStage:
    def test_unknown(self):
        """Line 66: unknown role returns fallback."""
        result = analytics._rol_to_funnel_stage("__test_unknown_role__")
        assert isinstance(result, str)
