# weaver.py

import os
import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .file_handler import AIResponseWeaver
from .utils import get_weaver_settings, resolve_path
from .config import load_config

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class FileChangeHandler(FileSystemEventHandler):
    """
    Handles file system events for the monitored file.

    Attributes:
        weaver (AIResponseWeaver): The AIResponseWeaver instance to process file changes.
    """

    def __init__(self, weaver):
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


def setup_file_monitoring(file_to_monitor, weaver):
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
    return observer


def process_existing_content(weaver):
    """
    Process the existing content of the monitored file.

    Args:
        weaver (AIResponseWeaver): The AIResponseWeaver instance to process the file.
    """
    logging.info("Processing existing content")
    weaver.process_file()


def main():
    """
    Main function to run the AI Response Weaver application.
    """
    logging.info("Starting AI Response Weaver")
    file_to_monitor, log_folder, git_repo_path = get_weaver_settings()

    logging.info(f"Monitoring file: {file_to_monitor}")
    logging.info(f"Log folder: {log_folder}")
    logging.info(f"Git repository path: {git_repo_path or 'Not specified'}")

    if not os.path.exists(file_to_monitor):
        logging.error(f"The file to monitor does not exist: {file_to_monitor}")
        sys.exit(1)

    os.makedirs(log_folder, exist_ok=True)

    config = load_config()
    weaver = AIResponseWeaver(
        file_to_monitor, log_folder, config, git_repo_path)

    # Process existing content before starting the file monitoring
    process_existing_content(weaver)

    observer = setup_file_monitoring(file_to_monitor, weaver)

    try:
        logging.info("Entering main loop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, stopping observer")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
