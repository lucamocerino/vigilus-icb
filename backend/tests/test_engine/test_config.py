"""Tests for sentinella.config — settings and level logic."""
from sentinella.config import settings, get_level


class TestWeights:
    def test_weights_sum_to_one(self):
        total = sum(settings.WEIGHTS.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"

    def test_all_six_dimensions(self):
        expected = {"geopolitica", "terrorismo", "cyber", "eversione", "militare", "sociale"}
        assert set(settings.WEIGHTS.keys()) == expected

    def test_all_weights_positive(self):
        for dim, w in settings.WEIGHTS.items():
            assert w > 0, f"Weight for {dim} is {w}"


class TestGetLevel:
    def test_calmo(self):
        level = get_level(10.0)
        assert level["label"] == "CALMO"

    def test_normale(self):
        level = get_level(30.0)
        assert level["label"] == "NORMALE"

    def test_attenzione(self):
        level = get_level(50.0)
        assert level["label"] == "ATTENZIONE"

    def test_elevato(self):
        level = get_level(70.0)
        assert level["label"] == "ELEVATO"

    def test_critico(self):
        level = get_level(90.0)
        assert level["label"] == "CRITICO"

    def test_boundary_0(self):
        level = get_level(0.0)
        assert level["label"] == "CALMO"

    def test_boundary_100(self):
        level = get_level(100.0)
        assert level["label"] == "CRITICO"

    def test_boundary_20_21(self):
        assert get_level(20.0)["label"] == "CALMO"
        assert get_level(21.0)["label"] == "NORMALE"

    def test_levels_have_all_fields(self):
        for level_conf in settings.LEVELS:
            assert "min" in level_conf
            assert "max" in level_conf
            assert "label" in level_conf
            assert "color" in level_conf

    def test_levels_cover_full_range(self):
        assert settings.LEVELS[0]["min"] == 0
        assert settings.LEVELS[-1]["max"] == 100
        for i in range(len(settings.LEVELS) - 1):
            assert settings.LEVELS[i]["max"] + 1 == settings.LEVELS[i + 1]["min"]
