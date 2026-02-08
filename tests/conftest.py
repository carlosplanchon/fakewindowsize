"""Pytest configuration and fixtures"""

import pytest
from pathlib import Path
import tempfile
import json


@pytest.fixture
def sample_csv_data():
    """Sample CSV data mimicking StatCounter response"""
    return """Screen Resolution,Market Share Perc. (2025)
1920x1080,8.36
360x800,6.71
390x844,3.76
1536x864,3.53
1366x768,3.28
414x896,2.98
1920x1200,2.45
428x926,2.32
393x873,1.89
412x915,1.78
Other,43.19"""


@pytest.fixture
def expected_scraped_dict():
    """Expected dictionary after scraping and converting to cumulative percentages"""
    return {
        '1920x1080': 8.36,
        '360x800': 15.07,
        '390x844': 18.83,
        '1536x864': 22.36,
        '1366x768': 25.64,
        '414x896': 28.62,
        '1920x1200': 31.07,
        '428x926': 33.39,
        '393x873': 35.28,
        '412x915': 37.06
    }


@pytest.fixture
def temp_cache_file(tmp_path):
    """Create a temporary cache file path"""
    return tmp_path / ".fakescreensize.json"


@pytest.fixture
def fws_with_temp_cache(temp_cache_file, monkeypatch):
    """Create FakeWindowSize instance with temporary cache file"""
    from fakewindowsize import FakeWindowSize

    fws = FakeWindowSize()
    # Override the default cache file path
    monkeypatch.setattr(fws, 'default_json_fp', temp_cache_file)
    return fws
