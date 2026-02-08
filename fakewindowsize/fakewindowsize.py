#!/usr/bin/env python3

from csv import DictReader
from io import StringIO
from requests import get

from json import dump, load
from pathlib import Path
from secrets import randbelow


class FakeWindowSize:
    def __init__(self):
        """Browser display stats scraper."""
        self.url = "https://gs.statcounter.com/chart.php?device_hidden=desktop%2Btablet%2Bmobile&statType_hidden=resolution&region_hidden=ww&multi-device=true&csv=1&granularity=yearly&fromYear=2025&toYear=2025"
        self.default_json_fp: Path = Path().home() / ".fakescreensize.json"
        self.scraped_dict = None

    def scrape_window_size_dict(self, request_proxies=None):
        """Scrape browser display stats from StatCounter"""
        resp = get(self.url, proxies=request_proxies)
        csv_data = StringIO(resp.text)
        reader = DictReader(csv_data)

        scraped_dict = {}
        for row in reader:
            resolution = row.get('Screen Resolution', '').strip()
            percentage_str = row.get('Market Share Perc. (2025)', '').strip()

            # Skip "Other" and invalid entries
            if resolution and resolution.lower() != 'other' and 'x' in resolution:
                try:
                    percentage = float(percentage_str)
                    scraped_dict[resolution] = percentage
                except ValueError:
                    continue

        # Convert to cumulative percentages for weighted random selection
        cumulative_percentage = 0
        for element in scraped_dict:
            cumulative_percentage += scraped_dict[element]
            scraped_dict[element] = cumulative_percentage

        return scraped_dict

    def default_width_x_heigth(self):
        """Return the default width and height for browsers."""
        return 1366, 768

    def choice_random_window_size(self, scraped_dict):
        """Get a random window size based on browsers data."""
        max_percentage = max(scraped_dict.values())
        num = randbelow(int(max_percentage) + 1)
        width, heigth = self.default_width_x_heigth()
        keys = list(scraped_dict)
        i = 0
        while i < len(scraped_dict):
            if num < scraped_dict[keys[i]]:
                width, heigth = keys[i].split("x")
                i = len(scraped_dict)
            else:
                i += 1
        return int(width), int(heigth)

    def save_scraped_dict(self, scraped_dict, path=None):
        """Save JSON screen size to a file."""
        if not path:
            path = self.default_json_fp
        with open(path, "w") as json_file:
            dump(scraped_dict, json_file)

    def load_scraped_dict(self, path=None):
        """Load JSON screen size file."""
        if not path:
            path = self.default_json_fp
        if path.exists():
            with open(path, "r") as json_file:
                scraped_dict = load(json_file)
            return scraped_dict
        return None

    def get_random_window_size(self):
        """Get a random window size which is statistically real."""
        if self.scraped_dict is None:
            self.scraped_dict = self.load_scraped_dict()
        if self.scraped_dict is None:
            try:
                self.scraped_dict = self.scrape_window_size_dict()
            except Exception:
                return None
            # Check if scraping returned empty data
            if not self.scraped_dict:
                return None
            self.save_scraped_dict(self.scraped_dict)
        return self.choice_random_window_size(self.scraped_dict)
