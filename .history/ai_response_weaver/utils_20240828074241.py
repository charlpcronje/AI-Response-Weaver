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
        tuple: A tuple containing the file to monitor, log folder path, and Git repo path.
    """
    if os.path.exists('.weaver'):
        with open('.weaver', 'r') as f:
            settings = json.load(f)
        logging.info("Settings loaded from .weaver file")

        # Check if all required keys are present, if not, update the file
        update_required = False
        if 'file_to_monitor' not in settings:
            settings['file_to_monitor'] = 'weaver.md'
            update_required = True
        if 'log_folder' not in settings:
            settings['log_folder'] = 'weaver'
            update_required = True
        if 'git_repo_path' not in settings:
            settings['git_repo_path'] = None
            update_required = True

        if update_required:
            with open('.weaver', 'w') as f:
                json.dump(settings, f)
            logging.info("Updated .weaver file with missing keys")

        return (
            resolve_path(settings['file_to_monitor']),
            resolve_path(settings['log_folder']),
            resolve_path(settings['git_repo_path']
                         ) if settings['git_repo_path'] else None
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
        json.dump(settings, f)
    logging.info("Settings saved to .weaver file")

    return file_to_monitor, log_folder, git_repo_path
