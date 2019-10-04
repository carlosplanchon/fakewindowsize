#!/usr/bin/env python3

from bs4 import BeautifulSoup
from requests import get

from json import dump, load
from pathlib import Path
from re import compile as comp
from secrets import randbelow


class FakeWindowSize:
    def __init__(self):
        """Browser display stats scraper."""
        self.url = "https://www.w3schools.com/browsers/browsers_display.asp"
        self.resolution_pattern = comp(r"^\d+x\d+$")
        self.percentage_pattern = comp(r"^\d{1,2}(\.?\d+)?%$")
        self.default_json_fp: Path = Path().home() / ".fakescreensize.json"
        self.scraped_dict = None

    def scrape_window_size_dict(self, request_proxies=None):
        """Scrape browser display stats from w3schools"""
        resp = get(self.url, proxies=request_proxies)
        soup = BeautifulSoup(resp.text, "lxml")
        resolution_table = soup.find(
                "table",
                {"class": "w3-table-all notranslate"}
            )
        rows = resolution_table.findAll("tr")
        scraped_dict = {}
        if len(rows) > 1:
            cells_row_tags = rows[0].findAll("th")
            cells_row_percentage = rows[1].findAll("td")
            for i in range(len(cells_row_tags)):
                if self.resolution_pattern.match(cells_row_tags[i].text) and \
                        self.percentage_pattern.match(
                            cells_row_percentage[i].text):
                    scraped_dict[cells_row_tags[i].text] = float(
                        cells_row_percentage[i].text.rstrip("%"))

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
        num = randbelow(round(max(scraped_dict.values())))
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
            self.save_scraped_dict(self.scraped_dict)
        return self.choice_random_window_size(self.scraped_dict)
