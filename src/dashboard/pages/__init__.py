"""Dashboard page modules."""

import importlib
from pathlib import Path

# Import modules with numeric prefixes using importlib
_pages_dir = Path(__file__).parent

page_01_overview = importlib.import_module("src.dashboard.pages.01_overview")
page_02_campaigns = importlib.import_module("src.dashboard.pages.02_campaigns")
page_03_keywords = importlib.import_module("src.dashboard.pages.03_keywords")
page_04_traffic = importlib.import_module("src.dashboard.pages.04_traffic")
page_05_conversions = importlib.import_module("src.dashboard.pages.05_conversions")
page_06_alerts = importlib.import_module("src.dashboard.pages.06_alerts")
