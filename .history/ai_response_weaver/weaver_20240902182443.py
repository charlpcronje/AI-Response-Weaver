# weaver.py

import os
import sys
import time
import logging
import argparse
from typing import TYPE_CHECKING
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .file_handler import AIResponseWeaver
from .utils import get_weaver_settings, resolve_path
from .config import load_config
from .user_interface import UserInterface

if TYPE_CHECKING:
    from watchdog.observers import Observer

# Set up logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')


class FileChangeHandler(FileSystemEventHandler):
    """
    Handles file system events for the monitored file.

    Attributes:
        weaver (AIResponseWeaver): The AIResponseWeaver instance to process file changes.
    """

    def __init__(self, weaver: AIResponseWeaver):
        """
        Initialize the FileChangeHandler.

        Args:
            weaver (AIResponseWeaver): The AIResponseWeaver instance to process file changes.
        """
        self.weaver = weaver

    def on_modified(self, event):
        """
        Called when a file modification is detected.

        Args:
            event (FileSystemEvent): The event object representing the file system event.
        """
        if not event.is_directory and event.src_path == self.weaver.file_to_monitor:
            logging.info(f"File change detected: {event.src_path}")
            self.weaver.process_file()


def setup_file_monitoring(file_to_monitor: str, weaver: AIResponseWeaver) -> 'Observer':
    """
    Set up file monitoring for the specified file.

    Args:
        file_to_monitor (str): Path to the file to monitor.
        weaver (AIResponseWeaver): The AIResponseWeaver instance to process file changes.

    Returns:
        Observer: The file system observer object.
    """
    logging.info("Setting up file monitoring")
    event_handler = FileChangeHandler(weaver)
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(
        file_to_monitor), recursive=False)
    observer.start()
    logging.debug("File monitoring set up successfully")
    return observer


def process_existing_content(weaver: AIResponseWeaver):
    """
    Process the existing content of the monitored file.

    Args:
        weaver (AIResponseWeaver): The AIResponseWeaver instance to process the file.
    """
    logging.info("Processing existing content")
    try:
        weaver.process_file()
        logging.info("Existing content processed successfully")
    except Exception as e:
        logging.error(f"Error processing existing content: {str(e)}")
        raise


def main():
    """
    Main function to run the AI Response Weaver application.
    """
    parser = argparse.ArgumentParser(description="AI Response Weaver")
    parser.add_argument("file_to_monitor", nargs="?", help="File to monitor")
    parser.add_argument("log_folder", nargs="?", help="Log folder")
    parser.add_argument("git_repo_path", nargs="?", help="Git repository path")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logging.info("Starting AI Response Weaver")

    if args.file_to_monitor and args.log_folder:
        file_to_monitor = args.file_to_monitor
        log_folder = args.log_folder
        git_repo_path = args.git_repo_path
    else:
        file_to_monitor, log_folder, git_repo_path = get_weaver_settings()

    file_to_monitor = resolve_path(file_to_monitor)
    log_folder = resolve_path(log_folder)
    git_repo_path = resolve_path(git_repo_path) if git_repo_path else None

    logging.info(f"Monitoring file: {file_to_monitor}")
    logging.info(f"Log folder: {log_folder}")
    logging.info(f"Git repository path: {git_repo_path or 'Not specified'}")

    if not os.path.exists(file_to_monitor):
        logging.error(f"The file to monitor does not exist: {file_to_monitor}")
        sys.exit(1)

    os.makedirs(log_folder, exist_ok=True)

    try:
        config = load_config()
        logging.debug("Configuration loaded successfully")
    except Exception as e:
        logging.error(f"Error loading configuration: {str(e)}")
        sys.exit(1)

    ui = UserInterface()
    logging.debug("UserInterface initialized")

    try:
        weaver = AIResponseWeaver(
            file_to_monitor, log_folder, config, git_repo_path)
        logging.debug("AIResponseWeaver initialized")
    except Exception as e:
        logging.error(f"Error initializing AIResponseWeaver: {str(e)}")
        sys.exit(1)

    # Process existing content before starting the file monitoring
    try:
        process_existing_content(weaver)
    except Exception as e:
        logging.error(f"Error processing existing content: {str(e)}")
        sys.exit(1)

    observer = setup_file_monitoring(file_to_monitor, weaver)

    try:
        logging.info("Entering main loop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, stopping observer")
        observer.stop()
    except Exception as e:
        logging.error(f"Unexpected error in main loop: {str(e)}")
    finally:
        observer.join()
        logging.info("AI Response Weaver shutting down")


if __name__ == "__main__":
    main()
