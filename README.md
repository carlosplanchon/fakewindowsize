<div align="center">
  <img src="https://raw.githubusercontent.com/carlosplanchon/fakewindowsize/refs/heads/master/assets/banner.jpeg" alt="fakewindowsize banner">
</div>

# fakewindowsize
*Python module to generate realistic browsers window size.*

Generate random but statistically accurate browser window sizes based on real-world usage data from [StatCounter](https://gs.statcounter.com/). Perfect for web scraping, testing, and generating realistic browser fingerprints.

## Features

- 📊 **Real-world data**: Uses current browser resolution statistics from StatCounter (2025 data)
- 🎲 **Weighted random selection**: More common resolutions are more likely to be returned
- 💾 **Smart caching**: Automatically caches data locally to minimize network requests
- 📱 **Multi-device support**: Includes desktop, tablet, and mobile resolutions
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
2. Converts market share percentages into cumulative distribution
3. Uses weighted random selection to pick resolutions based on real-world usage
4. Caches data locally (`~/.fakescreensize.json`) to reduce API calls
5. Returns resolution as a tuple of (width, height)

## Data source

Screen resolution data is sourced from [StatCounter Global Stats](https://gs.statcounter.com/screen-resolution-stats), which tracks browser usage across desktop, tablet, and mobile devices worldwide.
