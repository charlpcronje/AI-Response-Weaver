# File: ai_response_weaver/config_loader.py
import json
from pathlib import Path


def load_config() -> dict:
    """Load the configuration from config.json"""
    config_path = Path(__file__).parent.parent / 'config' / 'config.json'
    with open(config_path, 'r') as config_file:
        return json.load(config_file)
