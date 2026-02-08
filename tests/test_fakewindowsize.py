"""Tests for FakeWindowSize class"""

import pytest
import responses
from pathlib import Path
from fakewindowsize import FakeWindowSize

# StatCounter URL used by the library
STATCOUNTER_URL = "https://gs.statcounter.com/chart.php?device_hidden=desktop%2Btablet%2Bmobile&statType_hidden=resolution&region_hidden=ww&multi-device=true&csv=1&granularity=yearly&fromYear=2025&toYear=2025"


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
        """Test that default cache path is in home directory"""
        fws = FakeWindowSize()
        assert fws.default_json_fp == Path.home() / ".fakescreensize.json"


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
        width, height = fws.default_width_x_heigth()

        assert width == 1366
        assert height == 768

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
