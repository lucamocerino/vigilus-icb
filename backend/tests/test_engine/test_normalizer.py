"""Tests for sentinella.engine.normalizer — z-score normalization."""
from sentinella.engine.normalizer import z_score, z_to_score, normalize_proxy, aggregate_proxies


class TestZScore:
    def test_z_score_at_mean(self):
        assert z_score(50.0, 50.0, 10.0) == 0.0

    def test_z_score_above_mean(self):
        assert z_score(70.0, 50.0, 10.0) == 2.0

    def test_z_score_below_mean(self):
        assert z_score(30.0, 50.0, 10.0) == -2.0

    def test_z_score_zero_std_returns_zero(self):
        assert z_score(100.0, 50.0, 0.0) == 0.0

    def test_z_score_negative_value(self):
        result = z_score(-10.0, 0.0, 5.0)
        assert result == -2.0


class TestZToScore:
    def test_z_zero_maps_to_50(self):
        # z=0 → center of [-3,+3] mapped to [0,100] → 50
        assert z_to_score(0.0) == 50.0

    def test_z_plus_3_maps_to_100(self):
        assert z_to_score(3.0) == 100.0

    def test_z_minus_3_maps_to_0(self):
        assert z_to_score(-3.0) == 0.0

    def test_z_clipped_above(self):
        assert z_to_score(5.0) == 100.0

    def test_z_clipped_below(self):
        assert z_to_score(-5.0) == 0.0

    def test_z_1_5_gives_expected(self):
        # z=1.5 → (1.5+3)/6 * 100 = 75
        assert z_to_score(1.5) == 75.0

    def test_custom_clip(self):
        assert z_to_score(2.0, clip=2.0) == 100.0
        assert z_to_score(-2.0, clip=2.0) == 0.0


class TestNormalizeProxy:
    def test_at_baseline_gives_50(self):
        # value == mean → z=0 → 50
        result = normalize_proxy(80.0, mean=80.0, std=30.0)
        assert result == 50.0

    def test_above_baseline_gives_higher(self):
        result = normalize_proxy(140.0, mean=80.0, std=30.0)
        assert result > 50.0

    def test_below_baseline_gives_lower(self):
        result = normalize_proxy(20.0, mean=80.0, std=30.0)
        assert result < 50.0

    def test_invert_flips_direction(self):
        normal = normalize_proxy(100.0, mean=80.0, std=30.0)
        inverted = normalize_proxy(100.0, mean=80.0, std=30.0, invert=True)
        assert normal > 50.0
        assert inverted < 50.0

    def test_always_in_range(self):
        for val in [0, 1, 50, 100, 500, 1000, -100]:
            result = normalize_proxy(float(val), mean=50.0, std=10.0)
            assert 0.0 <= result <= 100.0


class TestAggregateProxies:
    def test_empty_returns_default(self):
        assert aggregate_proxies({}) == 30.0

    def test_simple_mean_without_weights(self):
        result = aggregate_proxies({"a": 60.0, "b": 40.0})
        assert result == 50.0

    def test_weighted_mean(self):
        result = aggregate_proxies(
            {"a": 100.0, "b": 0.0},
            {"a": 0.5, "b": 0.5},
        )
        assert result == 50.0

    def test_weighted_mean_unequal(self):
        result = aggregate_proxies(
            {"a": 100.0, "b": 0.0},
            {"a": 0.75, "b": 0.25},
        )
        assert result == 75.0

    def test_missing_weight_defaults_to_1(self):
        result = aggregate_proxies(
            {"a": 80.0, "b": 20.0},
            {"a": 1.0},  # b defaults to w=1.0
        )
        assert result == 50.0

    def test_all_zero_weights_returns_default(self):
        result = aggregate_proxies(
            {"a": 80.0},
            {"a": 0.0},
        )
        assert result == 30.0
