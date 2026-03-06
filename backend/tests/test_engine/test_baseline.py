"""Tests for sentinella.engine.baseline — baseline management."""
from sentinella.engine.baseline import get_default_baseline, DEFAULT_BASELINES


class TestGetDefaultBaseline:
    def test_known_dimension_proxy(self):
        result = get_default_baseline("geopolitica", "article_count")
        assert "mean" in result
        assert "std" in result
        assert result["mean"] > 0
        assert result["std"] > 0

    def test_unknown_dimension_returns_fallback(self):
        result = get_default_baseline("nonexistent", "proxy")
        assert result == {"mean": 0.0, "std": 1.0}

    def test_unknown_proxy_returns_fallback(self):
        result = get_default_baseline("geopolitica", "nonexistent_proxy")
        assert result == {"mean": 0.0, "std": 1.0}

    def test_all_dimensions_have_baselines(self):
        expected_dims = ["geopolitica", "terrorismo", "cyber", "eversione", "militare", "sociale"]
        for dim in expected_dims:
            assert dim in DEFAULT_BASELINES, f"Missing baseline for {dim}"

    def test_all_baselines_have_valid_values(self):
        for dim, proxies in DEFAULT_BASELINES.items():
            for proxy, values in proxies.items():
                assert "mean" in values, f"Missing mean in {dim}/{proxy}"
                assert "std" in values, f"Missing std in {dim}/{proxy}"
                assert values["std"] > 0, f"Zero std in {dim}/{proxy}"
