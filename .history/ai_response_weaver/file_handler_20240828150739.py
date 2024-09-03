# file_handler.py

import os
import shutil
import logging
import json
from datetime import datetime
from git import Repo, InvalidGitRepositoryError
import subprocess
from .parser import CustomParser
from .user_interface import UserInterface


class AIResponseWeaver:
    """
    Handles file processing, Git operations, and logging for the AI Response Weaver.

    Attributes:
        file_to_monitor (str): Path of the file to monitor.
        log_folder (str): Path of the log folder.
        config (dict): Configuration dictionary.
        parser (CustomParser): Instance of CustomParser for parsing content.
        repo (Repo): Git repository instance, if available.
        git_repo_path (str): Path to the Git repository.
        ui (UserInterface): User interface instance for interactions.
    """

    def __init__(self, file_to_monitor: str, log_folder: str, config: dict, git_repo_path: str = None):
        """
        Initialize the AIResponseWeaver.

        Args:
            file_to_monitor (str): Path of the file to monitor.
            log_folder (str): Path of the log folder.
            config (dict): Configuration dictionary.
            git_repo_path (str, optional): Path to the Git repository. Defaults to None.
        """
        self.file_to_monitor = file_to_monitor
        self.log_folder = log_folder
        self.config = config
        self.ui = UserInterface()
        self.parser = CustomParser(config, self.ui)
        self.repo = None
        self.git_repo_path = git_repo_path or os.getcwd()

        try:
            self.repo = Repo(self.git_repo_path)
            if not self.repo.bare:
                logging.info(
                    f"Git repository detected at {self.git_repo_path}")
            else:
                logging.warning(
                    f"Git repository at {self.git_repo_path} is bare. Git operations may not work as expected.")
        except InvalidGitRepositoryError:
            logging.warning(
                f"No Git repository found at {self.git_repo_path}. Git-related features will be disabled.")
        except Exception as e:
            logging.error(f"Error initializing Git repository: {str(e)}")

    def process_file(self):
        """
        Process the monitored file, parse its content, and handle file creation/updates.
        """
        logging.info(f"Starting to process file: {self.file_to_monitor}")
        with open(self.file_to_monitor, 'r') as file:
            content = file.read()

        if content.startswith('---\nParsed: true\n'):
            logging.info("File already parsed. Skipping.")
            return

        report = self.parser.parse(content)

        # Check for existing files and duplicates
        existing_files = []
        new_files = []
        for file_info
