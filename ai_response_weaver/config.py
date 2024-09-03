# config.py

import os
import json


def load_config():
    """
    Load the configuration from the config.json file.

    Returns:
        dict: The loaded configuration.
    """
    print("DEBUG: load_config - Loading configuration")
    config_path = os.path.join(os.path.dirname(
        __file__), '..', 'config', 'config.json')
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    print("DEBUG: load_config - Configuration loaded")
    return config
