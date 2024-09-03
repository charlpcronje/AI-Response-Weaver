# utils.py

import os
import json
import sys
from typing import Tuple, Optional


def resolve_path(path: str) -> str:
    """
    Resolve a potentially relative path to an absolute path.
    
    Args:
        path (str): The path to resolve.

    Returns:
        str: The absolute path.
    """
    return os.path.abspath(os.path.expanduser(path))


def get_weaver_settings() -> Tuple[str, str, Optional[str]]:
    """
    Get or prompt for the weaver settings.

    Returns:
        tuple: A tuple containing the file to monitor, log folder path, and Git repo path.
    """
    if os.path.exists('.weaver'):
        with open('.weaver', 'r') as f:
            settings = json.load(f)
        print("Settings loaded from .weaver file")
        return (
            resolve_path(settings['file_to_monitor']),
            resolve_path(settings['log_folder']),
            resolve_path(settings['git_repo_path']) if settings.get(
                'git_repo_path') else None
        )

    if len(sys.argv) >= 3:
        file_to_monitor = resolve_path(sys.argv[1])
        log_folder = resolve_path(sys.argv[2])
        git_repo_path = resolve_path(
            sys.argv[3]) if len(sys.argv) > 3 else None
    else:
        file_to_monitor = resolve_path(
            input("Enter the file to monitor (default: weaver.md): ") or "weaver.md")
        log_folder = resolve_path(
            input("Enter the log folder (default: weaver): ") or "weaver")
        git_repo_path = input(
            "Enter the Git repository path (optional, use '../' for parent directory, press Enter to skip): ")
        git_repo_path = resolve_path(git_repo_path) if git_repo_path else None

    settings = {
        'file_to_monitor': file_to_monitor,
        'log_folder': log_folder,
        'git_repo_path': git_repo_path
    }

    with open('.weaver', 'w') as f:
        json.dump(settings, f, indent=2)
    print("Settings saved to .weaver file")

    return file_to_monitor, log_folder, git_repo_path


def update_weaver_file(file_extension: str, comment_style: str):
    """
    Update the .weaver file with the new file extension and comment style.

    Args:
        file_extension (str): The file extension.
        comment_style (str): The comment style used.
    """
    weaver_file_path = '.weaver'

    if os.path.exists(weaver_file_path):
        with open(weaver_file_path, 'r') as f:
            weaver_data = json.load(f)
    else:
        weaver_data = {}

    if 'file_extensions' not in weaver_data:
        weaver_data['file_extensions'] = {}

    weaver_data['file_extensions'][file_extension] = comment_style

    with open(weaver_file_path, 'w') as f:
        json.dump(weaver_data, f, indent=2)

    print(
        f"Updated .weaver file with extension {file_extension} and comment style {comment_style}")
