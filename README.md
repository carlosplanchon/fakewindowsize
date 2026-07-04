<div align="center">
  <img src="https://raw.githubusercontent.com/carlosplanchon/fakewindowsize/refs/heads/master/assets/banner.jpeg" alt="fakewindowsize banner">
</div>

# fakewindowsize

[![CI](https://github.com/carlosplanchon/fakewindowsize/actions/workflows/ci.yml/badge.svg)](https://github.com/carlosplanchon/fakewindowsize/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/fakewindowsize.svg)](https://pypi.org/project/fakewindowsize/)
[![Python versions](https://img.shields.io/pypi/pyversions/fakewindowsize.svg)](https://pypi.org/project/fakewindowsize/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/carlosplanchon/fakewindowsize)

*Python module to generate realistic screen resolutions.*

Generate random but statistically accurate **screen resolutions** based on real-world usage data from [StatCounter](https://gs.statcounter.com/). Perfect for web scraping, testing, and generating realistic browser fingerprints.

> **Note on terminology:** the data source is StatCounter's *screen resolution*
> stats (i.e. `screen.width` × `screen.height`, the physical display size), not
> the browser viewport / window inner size (`window.innerWidth`). For most
> fingerprinting use cases the screen resolution is exactly what you want.

## Features

- 📊 **Real-world data**: Uses screen resolution statistics from StatCounter (defaults to the previous, complete year)
- 🎲 **Weighted random selection**: More common resolutions are more likely to be returned
- 💾 **Smart caching**: Caches data locally (with a TTL) to minimize network requests
- 📱 **Multi-device support**: Includes desktop, tablet, and mobile resolutions
- 🌍 **Configurable**: Choose the `year`, `region` and `device` mix
- 🔒 **Proxy support**: Configure HTTP proxies for data fetching

## Installation

```bash
pip install fakewindowsize
```

Or with uv:
```bash
uv add fakewindowsize
```

## Usage

### Basic usage
```python
import fakewindowsize

f = fakewindowsize.FakeWindowSize()

# Get a random, statistically realistic window size
width, height = f.get_random_window_size()
print(f"{width}x{height}")  # e.g., (1920, 1080)
```

### Choosing year / region / device
```python
# US desktop resolutions from the 2024 dataset
f = fakewindowsize.FakeWindowSize(year=2024, region="us", device="desktop")
width, height = f.get_random_window_size()
```

- `year`: StatCounter yearly dataset (defaults to the previous calendar year, which is always complete).
- `region`: StatCounter region code (`ww`, `us`, `eu`, ...).
- `device`: `+`-joined device types (`desktop+tablet+mobile`, `desktop`, `mobile`, ...).
- `cache_ttl_days`: how long the local cache stays fresh (default `30`; `None` to never expire).
- `request_timeout`: seconds before an HTTP request times out (default `30`).

Each parameter combination is cached in its own file, so different regions/years never clobber each other.

### With proxy support
```python
f = fakewindowsize.FakeWindowSize()

proxies = {
    'http': 'http://proxy.example.com:8080',
    'https': 'http://proxy.example.com:8080',
}

data = f.scrape_window_size_dict(request_proxies=proxies)
```

## How it works

1. Fetches screen resolution statistics from StatCounter's global database
2. Converts market share percentages into a cumulative distribution
3. Uses weighted random selection to pick resolutions based on real-world usage
4. Caches data locally (`~/.fakewindowsize-<device>-<region>-<year>.json`) to reduce network requests
5. Returns resolution as a tuple of (width, height)

## Data source

Screen resolution data is sourced from [StatCounter Global Stats](https://gs.statcounter.com/screen-resolution-stats), which tracks browser usage across desktop, tablet, and mobile devices worldwide.
