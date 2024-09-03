# utils.py

import os
import json
import sys


def resolve_path(path):
    """
    Resolve a potentially relative path to an absolute path.
    
    Args:
        path (str): The path to resolve.

    Returns:
        str: The absolute path.
    """
    return os.path.abspath(os.path.expanduser(path))


def get_weaver_settings():
    """
    Get or prompt for the weaver settings.

    Returns:
        tuple: A tuple containing the file to monitor and the log folder path.
    """
    print("DEBUG: get_weaver_settings - Getting Weaver settings")
    if os.path.exists('.weaver'):
        with open('.weaver', 'r') as f:
            settings = json.load(f)
        print("DEBUG: get_weaver_settings - Settings loaded from .weaver file")
        file_to_monitor = resolve_path(settings['file_to_monitor'])
        log_folder = resolve_path(settings['log_folder'])
        return file_to_monitor, log_folder
    elif len(sys.argv) == 3:
        file_to_monitor = resolve_path(sys.argv[1])
        log_folder = resolve_path(sys.argv[2])
    else:
        file_to_monitor = resolve_path(
            input("Enter the file to monitor (default: weave.md): ") or "weave.md")
        log_folder = resolve_path(
            input("Enter the log folder (default: weaver): ") or "weaver")

    with open('.weaver', 'w') as f:
        json.dump({'file_to_monitor': file_to_monitor,
                  'log_folder': log_folder}, f)
    print("DEBUG: get_weaver_settings - Settings saved to .weaver file")
    return file_to_monitor, log_folder
