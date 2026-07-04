#!/usr/bin/env python3

import os

from csv import DictReader
from io import StringIO
from requests import get

from datetime import date
from json import dump, load, JSONDecodeError
from pathlib import Path
from random import uniform
from time import time
from urllib.parse import urlencode


DEFAULT_DEVICE = "desktop+tablet+mobile"
DEFAULT_REGION = "ww"


def _slugify(value) -> str:
    """Reduce a value to a filesystem-safe token (alnum, rest -> '_')."""
    return "".join(c if c.isalnum() else "_" for c in str(value))


def build_statcounter_url(
    year: int,
    region: str = DEFAULT_REGION,
    device: str = DEFAULT_DEVICE,
) -> str:
    """Build the StatCounter CSV export URL for the given parameters."""
    query = urlencode([
        ("device_hidden", device),
        ("statType_hidden", "resolution"),
        ("region_hidden", region),
        ("multi-device", "true"),
        ("csv", "1"),
        ("granularity", "yearly"),
        ("fromYear", year),
        ("toYear", year),
    ])
    return f"https://gs.statcounter.com/chart.php?{query}"


class FakeWindowSize:
    def __init__(
        self,
        year: int | None = None,
        region: str = DEFAULT_REGION,
        device: str = DEFAULT_DEVICE,
        cache_ttl_days: float | None = 30,
        request_timeout: float | None = 30,
    ):
        """Browser display (screen resolution) stats scraper.

        Note: the data source is StatCounter's *screen resolution* stats
        (``screen.width`` x ``screen.height``), not the browser viewport /
        window inner size.

        Args:
            year: StatCounter yearly dataset to use. Defaults to the previous
                calendar year, which is always complete.
            region: StatCounter region code (e.g. ``ww``, ``us``, ``eu``).
            device: ``+``-joined device types (``desktop+tablet+mobile``).
            cache_ttl_days: How long the local cache is considered fresh.
                ``None`` means never expire.
            request_timeout: Seconds before an HTTP request times out.
        """
        if year is None:
            # Previous year: StatCounter's current-year yearly aggregate is
            # incomplete until the year ends.
            year = date.today().year - 1

        self.year = year
        self.region = region
        self.device = device
        self.cache_ttl_days = cache_ttl_days
        self.request_timeout = request_timeout

        self.url = build_statcounter_url(year, region, device)
        self.market_share_column = f"Market Share Perc. ({year})"

        # Cache is keyed by the parameters that determine its contents so
        # different regions/devices/years don't clobber each other. Each
        # component is slugified so an odd region/device value can't inject a
        # path separator and escape the home directory.
        slug = f"{_slugify(device)}-{_slugify(region)}-{_slugify(year)}"
        self.default_json_fp: Path = Path.home() / f".fakewindowsize-{slug}.json"

        self.scraped_dict = None

    def scrape_window_size_dict(self, request_proxies=None, timeout=None):
        """Scrape browser display stats from StatCounter"""
        resp = get(
            self.url,
            proxies=request_proxies,
            timeout=timeout if timeout is not None else self.request_timeout,
        )
        resp.raise_for_status()
        csv_data = StringIO(resp.text)
        reader = DictReader(csv_data)

        scraped_dict = {}
        for row in reader:
            resolution = row.get('Screen Resolution', '').strip()
            percentage_str = row.get(self.market_share_column, '').strip()

            # Keep only well-formed "WIDTHxHEIGHT" rows with ASCII-decimal
            # dimensions. This filters out "Other" and any junk, and guarantees
            # every stored key is safely int()-parseable later.
            parts = resolution.split('x')
            if len(parts) != 2 or not all(
                p.isascii() and p.isdigit() for p in parts
            ):
                continue

            try:
                percentage = float(percentage_str)
            except ValueError:
                continue
            scraped_dict[resolution] = percentage

        # Convert to cumulative percentages for weighted random selection
        cumulative_percentage = 0.0
        for element in scraped_dict:
            cumulative_percentage += scraped_dict[element]
            scraped_dict[element] = cumulative_percentage

        return scraped_dict

    def default_width_x_height(self):
        """Return the default width and height for browsers."""
        return 1366, 768

    # Backwards-compatible alias for the old (misspelled) method name.
    default_width_x_heigth = default_width_x_height

    def choice_random_window_size(self, scraped_dict):
        """Get a random window size based on browsers data."""
        # scraped_dict maps resolution -> cumulative percentage, so the last
        # value is the total weight. Draw a continuous point in [0, total) to
        # avoid discretizing the sub-percent fractional shares.
        total = max(scraped_dict.values())
        num = uniform(0, total)
        width, height = self.default_width_x_height()
        for resolution, threshold in scraped_dict.items():
            if num < threshold:
                width, height = resolution.split("x")
                break
        return int(width), int(height)

    def save_scraped_dict(self, scraped_dict, path=None):
        """Save JSON screen size to a file, atomically.

        Writes to a temp file in the same directory and renames it into place
        so a concurrent reader never sees a half-written cache.
        """
        if not path:
            path = self.default_json_fp
        path = Path(path)
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        try:
            with open(tmp, "w") as json_file:
                dump(scraped_dict, json_file)
            os.replace(tmp, path)
        except BaseException:
            # Don't leave a stray temp file behind on failure/interrupt.
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def load_scraped_dict(self, path=None):
        """Load JSON screen size file.

        Returns ``None`` if the file is missing, unreadable, or corrupt (e.g.
        a torn write from a concurrent process) so the caller can re-scrape
        instead of crashing.
        """
        if not path:
            path = self.default_json_fp
        path = Path(path)
        try:
            with open(path, "r") as json_file:
                return load(json_file)
        except (OSError, ValueError, JSONDecodeError):
            return None

    def _cache_is_fresh(self, path=None):
        """Return whether the cache file exists and is within its TTL."""
        if self.cache_ttl_days is None:
            return True
        if not path:
            path = self.default_json_fp
        if not path.exists():
            return False
        age_seconds = time() - path.stat().st_mtime
        return age_seconds < self.cache_ttl_days * 86400

    def get_random_window_size(self):
        """Get a random window size which is statistically real."""
        if self.scraped_dict is None:
            cached = self.load_scraped_dict()
            if cached and self._cache_is_fresh():
                self.scraped_dict = cached

        if self.scraped_dict is None:
            try:
                fresh = self.scrape_window_size_dict()
            except Exception:
                fresh = None

            if fresh:
                self.scraped_dict = fresh
                try:
                    self.save_scraped_dict(self.scraped_dict)
                except OSError:
                    # Caching is best-effort; an unwritable HOME must not stop
                    # us from returning a valid size.
                    pass
            else:
                # Network/scrape failed or returned nothing: fall back to a
                # stale cache if one exists.
                self.scraped_dict = self.load_scraped_dict()

        if not self.scraped_dict:
            return None
        return self.choice_random_window_size(self.scraped_dict)
