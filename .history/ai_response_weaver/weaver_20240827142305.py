# file_handler.py

import os
import sys
import time
from watchdog.observers import Observer
from .file_handler import AIResponseWeaver
from .utils import get_weaver_settings
from .config import load_config


class AIResponseWeaver:
    """
    Handles file processing, Git operations, and logging for the AI Response Weaver.

    Attributes:
        file_to_monitor (str): Path of the file to monitor.
        log_folder (str): Path of the log folder.
        config (dict): Configuration dictionary.
        parser (CustomParser): Instance of CustomParser for parsing content.
        repo (Repo): Git repository instance.
    """

    def __init__(self, file_to_monitor, log_folder, config):
        """
        Initialize the AIResponseWeaver.

        Args:
            file_to_monitor (str): Path of the file to monitor.
            log_folder (str): Path of the log folder.
            config (dict): Configuration dictionary.
        """
        self.file_to_monitor = file_to_monitor
        self.log_folder = log_folder
        self.config = config
        self.parser = CustomParser(config)
        self.repo = Repo(os.getcwd())

    def process_file(self):
        """
        Process the monitored file, parse its content, and handle file creation/updates.
        """
        print(
            f"DEBUG: AIResponseWeaver.process_file - Starting to process file: {self.file_to_monitor}")
        with open(self.file_to_monitor, 'r') as file:
            content = file.read()

        if content.startswith('---\nParsed: true\n'):
            print("DEBUG: AIResponseWeaver.process_file - File already parsed. Skipping.")
            return

        report = self.parser.parse(content)

        # Check for existing files and duplicates
        existing_files = []
        new_files = []
        for file_info in self.parser.files:
            if os.path.exists(file_info.path):
                existing_files.append(file_info)
            else:
                new_files.append(file_info)

        # Create new files
        for file_info in new_files:
            self._create_file(file_info)

        # Update existing files
        if existing_files:
            branch_name = self._create_branch(existing_files)
            for file_info in existing_files:
                self._update_file(file_info)
            self._commit_changes(branch_name)
            self._trigger_merge(branch_name)

        # Update the monitored file with the report
        self._update_monitored_file(report, content)

        # Log instruction blocks
        self._log_instruction_blocks()

        print("DEBUG: AIResponseWeaver.process_file - File processing complete")

    def _create_file(self, file_info):
        """
        Create a new file with the given file information.

        Args:
            file_info (FileInfo): Information about the file to create.
        """
        print(
            f"DEBUG: AIResponseWeaver._create_file - Creating new file: {file_info.path}")
        full_path = os.path.join(os.getcwd(), file_info.path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as file:
            file.write('\n'.join(file_info.content))
        print(
            f"DEBUG: AIResponseWeaver._create_file - File created: {full_path}")

    def _update_file(self, file_info):
        """
        Update an existing file with the given file information.

        Args:
            file_info (FileInfo): Information about the file to update.
        """
        print(
            f"DEBUG: AIResponseWeaver._update_file - Updating file: {file_info.path}")
        full_path = os.path.join(os.getcwd(), file_info.path)
        # Create backup
