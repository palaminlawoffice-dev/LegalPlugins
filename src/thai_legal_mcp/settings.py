from pathlib import Path
import os
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.yaml"

def load_config() -> dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CONFIG = load_config()

HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "20"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "10"))
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "bing_html")
