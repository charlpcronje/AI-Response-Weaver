# File: ai_response_weaver/utils.py
import os
import logging
from pathlib import Path


def resolve_path(path: str) -> str:
    """Resolve relative paths to absolute paths"""
    return str(Path(path).resolve())


def ensure_file_exists(file_path: str):
    """Ensure that the file to be monitored exists, create if it doesn't"""
    if not os.path.exists(file_path):
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        with open(file_path, 'w') as f:
            f.write("# This file was created by AI Response Weaver\n")
        logging.info(f"Created file to monitor: {file_path}")
