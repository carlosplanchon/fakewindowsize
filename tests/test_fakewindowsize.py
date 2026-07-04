"""Tests for FakeWindowSize class"""

import pytest
import responses
from datetime import date
from pathlib import Path
from fakewindowsize import FakeWindowSize, build_statcounter_url

# Year the library defaults to (previous, complete calendar year).
DEFAULT_YEAR = date.today().year - 1

# StatCounter URL used by the library (must match what the library builds).
STATCOUNTER_URL = build_statcounter_url(DEFAULT_YEAR)


class TestFakeWindowSizeInit:
    """Tests for FakeWindowSize initialization"""

    def test_initialization(self):
        """Test that FakeWindowSize initializes correctly"""
        fws = FakeWindowSize()
        assert fws.url.startswith("https://gs.statcounter.com/")
        assert "csv=1" in fws.url
        assert isinstance(fws.default_json_fp, Path)
        assert fws.scraped_dict is None

    def test_default_cache_path(self):
        """Test that default cache path is in home directory and param-keyed"""
        fws = FakeWindowSize()
        expected = Path.home() / f".fakewindowsize-desktop_tablet_mobile-ww-{DEFAULT_YEAR}.json"
        assert fws.default_json_fp == expected

    def test_cache_path_differs_by_params(self):
        """Different region/device/year must not share a cache file"""
        assert (
            FakeWindowSize(region="us").default_json_fp
            != FakeWindowSize(region="ww").default_json_fp
        )
        assert (
            FakeWindowSize(year=2024).default_json_fp
            != FakeWindowSize(year=2025).default_json_fp
        )


class TestScrapingMethods:
    """Tests for data scraping methods"""

    @responses.activate
    def test_scrape_window_size_dict_success(self, sample_csv_data, expected_scraped_dict):
        """Test successful scraping and parsing of StatCounter CSV data"""
        responses.add(
            responses.GET,
            STATCOUNTER_URL,
            body=sample_csv_data,
            status=200,
        )

        fws = FakeWindowSize()
        result = fws.scrape_window_size_dict()

        assert result == expected_scraped_dict
        assert len(result) == 10  # All resolutions except "Other"
        assert '1920x1080' in result
        assert result['1920x1080'] == 8.36
        # Verify cumulative percentages
        assert result['360x800'] == 15.07  # 8.36 + 6.71

    @responses.activate
    def test_scrape_with_proxy(self, sample_csv_data):
        """Test scraping with proxy configuration"""
        responses.add(
            responses.GET,
            STATCOUNTER_URL,
            body=sample_csv_data,
            status=200,
        )

        fws = FakeWindowSize()
        proxies = {"http": "http://proxy.example.com:8080"}
        result = fws.scrape_window_size_dict(request_proxies=proxies)

        assert result is not None
        assert len(result) > 0

    @responses.activate
    def test_scrape_filters_other_category(self, sample_csv_data):
        """Test that 'Other' category is filtered out"""
        responses.add(
            responses.GET,
            STATCOUNTER_URL,
            body=sample_csv_data,
            status=200,
        )

        fws = FakeWindowSize()
        result = fws.scrape_window_size_dict()

        assert 'Other' not in result
        assert 'other' not in result


class TestCachingMethods:
    """Tests for caching functionality"""

    def test_save_scraped_dict(self, fws_with_temp_cache, expected_scraped_dict):
        """Test saving scraped data to JSON cache"""
        fws_with_temp_cache.save_scraped_dict(expected_scraped_dict)

        assert fws_with_temp_cache.default_json_fp.exists()

        # Verify content
        import json
        with open(fws_with_temp_cache.default_json_fp, 'r') as f:
            loaded_data = json.load(f)
        assert loaded_data == expected_scraped_dict

    def test_load_scraped_dict_exists(self, fws_with_temp_cache, expected_scraped_dict):
        """Test loading scraped data from existing cache file"""
        # First save the data
        fws_with_temp_cache.save_scraped_dict(expected_scraped_dict)

        # Then load it
        result = fws_with_temp_cache.load_scraped_dict()

        assert result == expected_scraped_dict

    def test_load_scraped_dict_not_exists(self, fws_with_temp_cache):
        """Test loading when cache file doesn't exist"""
        result = fws_with_temp_cache.load_scraped_dict()
        assert result is None

    def test_save_and_load_custom_path(self, tmp_path, expected_scraped_dict):
        """Test saving and loading with custom path"""
        fws = FakeWindowSize()
        custom_path = tmp_path / "custom_cache.json"

        fws.save_scraped_dict(expected_scraped_dict, path=custom_path)
        assert custom_path.exists()

        result = fws.load_scraped_dict(path=custom_path)
        assert result == expected_scraped_dict


class TestRandomSelection:
    """Tests for random window size selection"""

    def test_default_width_x_height(self):
        """Test default fallback resolution"""
        fws = FakeWindowSize()
        width, height = fws.default_width_x_height()

        assert width == 1366
        assert height == 768

    def test_default_width_x_height_legacy_alias(self):
        """The old (misspelled) method name still works for back-compat"""
        fws = FakeWindowSize()
        assert fws.default_width_x_heigth() == fws.default_width_x_height()

    def test_choice_random_window_size(self, expected_scraped_dict):
        """Test random selection from scraped data"""
        fws = FakeWindowSize()

        # Run multiple times to ensure it always returns valid results
        for _ in range(20):
            width, height = fws.choice_random_window_size(expected_scraped_dict)

            assert isinstance(width, int)
            assert isinstance(height, int)
            assert width > 0
            assert height > 0

            # Verify the resolution exists in our data
            resolution = f"{width}x{height}"
            assert resolution in expected_scraped_dict

    def test_choice_random_window_size_distribution(self, expected_scraped_dict):
        """Test that random selection favors more common resolutions"""
        fws = FakeWindowSize()

        # Generate many samples
        samples = []
        for _ in range(1000):
            width, height = fws.choice_random_window_size(expected_scraped_dict)
            samples.append(f"{width}x{height}")

        # Most common resolution (1920x1080) should appear frequently
        count_1920x1080 = samples.count('1920x1080')

        # It should appear more than if it were uniform distribution
        # With 10 resolutions, uniform would be ~100 times
        # With 8.36% market share, it should appear ~80+ times
        assert count_1920x1080 > 50  # Being conservative to avoid flaky tests

    @responses.activate
    def test_get_random_window_size_with_scraping(self, sample_csv_data, fws_with_temp_cache):
        """Test get_random_window_size when it needs to scrape"""
        responses.add(
            responses.GET,
            STATCOUNTER_URL,
            body=sample_csv_data,
            status=200,
        )

        result = fws_with_temp_cache.get_random_window_size()

        assert result is not None
        width, height = result
        assert isinstance(width, int)
        assert isinstance(height, int)
        assert width > 0
        assert height > 0

        # Verify cache was created
        assert fws_with_temp_cache.default_json_fp.exists()

    def test_get_random_window_size_from_cache(self, fws_with_temp_cache, expected_scraped_dict):
        """Test get_random_window_size loads from cache"""
        # Pre-populate cache
        fws_with_temp_cache.save_scraped_dict(expected_scraped_dict)

        result = fws_with_temp_cache.get_random_window_size()

        assert result is not None
        width, height = result
        assert isinstance(width, int)
        assert isinstance(height, int)

    @responses.activate
    def test_get_random_window_size_network_error(self, fws_with_temp_cache):
        """Test get_random_window_size handles network errors gracefully"""
        responses.add(
            responses.GET,
            STATCOUNTER_URL,
            body="Server Error",
            status=500,
        )

        result = fws_with_temp_cache.get_random_window_size()

        # Should return None on error
        assert result is None


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_empty_scraped_dict(self):
        """Test behavior with empty scraped dictionary"""
        fws = FakeWindowSize()

        with pytest.raises(ValueError):
            fws.choice_random_window_size({})

    @responses.activate
    def test_malformed_csv_data(self):
        """Test handling of malformed CSV data"""
        fws = FakeWindowSize()

        # This should not crash, but return empty or partial data
        # depending on how much is parseable
        responses.add(
            responses.GET,
            STATCOUNTER_URL,
            body="Not a CSV\nJust garbage data",
            status=200,
        )

        result = fws.scrape_window_size_dict()

        # Should return empty dict for malformed data
        assert result == {}


class TestIntegration:
    """Integration tests"""

    @responses.activate
    def test_full_workflow(self, sample_csv_data, fws_with_temp_cache):
        """Test complete workflow: scrape, cache, and retrieve"""
        responses.add(
            responses.GET,
            STATCOUNTER_URL,
            body=sample_csv_data,
            status=200,
        )

        # First call should scrape and cache
        width1, height1 = fws_with_temp_cache.get_random_window_size()
        assert fws_with_temp_cache.default_json_fp.exists()

        # Second call should use cache (no new HTTP request needed)
        width2, height2 = fws_with_temp_cache.get_random_window_size()

        # Both should return valid resolutions
        assert isinstance(width1, int) and isinstance(height1, int)
        assert isinstance(width2, int) and isinstance(height2, int)

        # Verify only one HTTP call was made
        assert len(responses.calls) == 1


class TestRobustness:
    """Regression tests for edge cases found during review."""

    @responses.activate
    def test_malformed_resolution_rows_are_skipped(self, fws_with_temp_cache):
        """Junk rows that merely contain 'x' must not become dict keys."""
        csv = (
            f"Screen Resolution,Market Share Perc. ({DEFAULT_YEAR})\n"
            "1920x1080,8.36\n"
            "12xABC,5.00\n"        # non-numeric height
            "1920x1080x2,1.00\n"   # too many parts
            "1234,1.00\n"          # no 'x'
            "Other,80.00\n"
        )
        responses.add(responses.GET, STATCOUNTER_URL, body=csv, status=200)

        result = fws_with_temp_cache.scrape_window_size_dict()
        assert list(result.keys()) == ["1920x1080"]

        # Selection over the parsed data must never raise (every key is WxH).
        for _ in range(50):
            width, height = fws_with_temp_cache.choice_random_window_size(result)
            assert (width, height) == (1920, 1080)

    def test_cache_path_cannot_escape_home(self):
        """Odd region/device values must not inject a path separator."""
        fws = FakeWindowSize(region="us/../etc", device="a/b")
        assert fws.default_json_fp.parent == Path.home()

    @responses.activate
    def test_get_survives_unwritable_cache(self, sample_csv_data, monkeypatch):
        """A cache write failure must not stop a valid size being returned."""
        responses.add(responses.GET, STATCOUNTER_URL, body=sample_csv_data, status=200)

        fws = FakeWindowSize()
        monkeypatch.setattr(
            fws, "default_json_fp", Path("/nonexistent_dir_xyz/cache.json")
        )

        result = fws.get_random_window_size()
        assert result is not None
        width, height = result
        assert isinstance(width, int) and isinstance(height, int)

    @responses.activate
    def test_corrupt_cache_self_heals(self, sample_csv_data, fws_with_temp_cache):
        """A torn/corrupt cache is treated as missing and rewritten."""
        # Simulate a half-written cache from a concurrent process.
        fws_with_temp_cache.default_json_fp.write_text('{"1920x1080": 8.36, "360')
        assert fws_with_temp_cache.load_scraped_dict() is None

        responses.add(responses.GET, STATCOUNTER_URL, body=sample_csv_data, status=200)
        result = fws_with_temp_cache.get_random_window_size()
        assert result is not None

        # Cache is valid JSON again.
        import json
        json.loads(fws_with_temp_cache.default_json_fp.read_text())

    def test_save_is_atomic_and_leaves_no_tmp(self, tmp_path, expected_scraped_dict):
        """Atomic save must not leave temp files behind."""
        fws = FakeWindowSize()
        cache = tmp_path / "cache.json"
        fws.save_scraped_dict(expected_scraped_dict, path=cache)
        assert [p.name for p in tmp_path.iterdir()] == ["cache.json"]

    def test_stale_cache_used_when_network_fails(
        self, expected_scraped_dict, temp_cache_file, monkeypatch
    ):
        """When the cache is stale and the network is down, use the stale cache."""
        fws = FakeWindowSize(cache_ttl_days=0)  # ttl=0 => any cache is stale
        monkeypatch.setattr(fws, "default_json_fp", temp_cache_file)
        fws.save_scraped_dict(expected_scraped_dict)

        def boom(*args, **kwargs):
            raise RuntimeError("network down")

        monkeypatch.setattr(fws, "scrape_window_size_dict", boom)

        result = fws.get_random_window_size()
        assert result is not None
        width, height = result
        assert f"{width}x{height}" in expected_scraped_dict

    def test_ttl_none_never_expires(
        self, expected_scraped_dict, temp_cache_file, monkeypatch
    ):
        """cache_ttl_days=None uses the cache regardless of age (no scrape)."""
        import os
        import time

        fws = FakeWindowSize(cache_ttl_days=None)
        monkeypatch.setattr(fws, "default_json_fp", temp_cache_file)
        fws.save_scraped_dict(expected_scraped_dict)

        old = time.time() - 1000 * 86400  # backdate 1000 days
        os.utime(temp_cache_file, (old, old))
        assert fws._cache_is_fresh() is True

        scraped = []
        monkeypatch.setattr(
            fws, "scrape_window_size_dict",
            lambda *a, **k: scraped.append(1) or {},
        )
        result = fws.get_random_window_size()
        assert result is not None
        assert scraped == []  # cache used, scrape never called

    def test_expired_cache_triggers_rescrape(
        self, expected_scraped_dict, temp_cache_file, monkeypatch
    ):
        """An expired cache forces a re-scrape."""
        import os
        import time

        fws = FakeWindowSize(cache_ttl_days=30)
        monkeypatch.setattr(fws, "default_json_fp", temp_cache_file)
        fws.save_scraped_dict(expected_scraped_dict)

        old = time.time() - 1000 * 86400
        os.utime(temp_cache_file, (old, old))
        assert fws._cache_is_fresh() is False

        scraped = []

        def fake_scrape(*args, **kwargs):
            scraped.append(1)
            return dict(expected_scraped_dict)

        monkeypatch.setattr(fws, "scrape_window_size_dict", fake_scrape)
        result = fws.get_random_window_size()
        assert result is not None
        assert scraped == [1]  # stale cache -> re-scraped
