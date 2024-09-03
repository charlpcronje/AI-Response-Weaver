# file_handler.py
import os
import shutil
import logging
import json
from datetime import datetime
from typing import List, Optional
from git import Repo, InvalidGitRepositoryError
import subprocess
from .parser import CustomParser, FileInfo
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

    def __init__(self, file_to_monitor: str, log_folder: str, config: dict, git_repo_path: Optional[str] = None):
        """
        Initialize the AIResponseWeaver.

        Args:
            file_to_monitor (str): Path of the file to monitor.
            log_folder (str): Path of the log folder.
            config (dict): Configuration dictionary.
            git_repo_path (Optional[str], optional): Path to the Git repository. Defaults to None.
        """
        self.file_to_monitor = file_to_monitor
        self.log_folder = log_folder
        self.config = config
        self.ui = UserInterface()
        self.parser = CustomParser(config, self.ui)
        self.repo = None
        self.git_repo_path = git_repo_path if git_repo_path is not None else os.getcwd()

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
        for file_info in self.parser.files:
            if os.path.exists(file_info.path):
                existing_files.append(file_info)
            else:
                new_files.append(file_info)

        # Create new files
        for file_info in new_files:
            self._create_file(file_info)

        # Update existing files
        if existing_files and self.repo:
            branch_name = self._create_branch(existing_files)
            if branch_name:
                for file_info in existing_files:
                    self._update_file(file_info)
                self._commit_changes(branch_name)
                self._trigger_merge(branch_name)
        elif existing_files:
            for file_info in existing_files:
                self._update_file(file_info)

        # Update the monitored file with the report
        self._update_monitored_file(report, content)

        # Log instruction blocks
        self._log_instruction_blocks()

        logging.info("File processing complete")

    def _create_file(self, file_info: FileInfo):
        """
        Create a new file with the given file information.

        Args:
            file_info (FileInfo): Information about the file to create.
        """
        logging.info(f"Creating new file: {file_info.path}")
        full_path = os.path.join(os.getcwd(), file_info.path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as file:
            file.write('\n'.join(file_info.content))
        logging.info(f"File created: {full_path}")

    def _update_file(self, file_info: FileInfo):
        """
        Update an existing file with the given file information.

        Args:
            file_info (FileInfo): Information about the file to update.
        """
        logging.info(f"Updating file: {file_info.path}")
        full_path = os.path.join(os.getcwd(), file_info.path)
        # Create backup
        backup_path = self._create_backup(full_path)
        # Update file
        with open(full_path, 'w') as file:
            file.write('\n'.join(file_info.content))
        logging.info(
            f"File updated: {full_path}, Backup created: {backup_path}")

    def _create_backup(self, file_path: str) -> str:
        """
        Create a backup of the given file.

        Args:
            file_path (str): Path of the file to backup.

        Returns:
            str: Path of the created backup file.
        """
        logging.info(f"Creating backup for file: {file_path}")
        backup_dir = os.path.join(self.log_folder, "history")
        os.makedirs(backup_dir, exist_ok=True)
        file_name = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"{file_name}-{timestamp}")
        shutil.copy2(file_path, backup_path)
        logging.info(f"Backup created: {backup_path}")
        return backup_path

    def _create_branch(self, files_to_update: List['FileInfo']) -> Optional[str]:
        """
        Create a new Git branch for the files to be updated.

        Args:
            files_to_update (list): List of FileInfo objects to be updated.

        Returns:
            str: Name of the created branch, or None if branch creation failed.
        """
        if not self.repo:
            logging.warning(
                "Git repository not initialized. Skipping branch creation.")
            return None

        logging.info("Creating new branch for updates")
        try:
            branch_name = f"update-{'-'.join([os.path.basename(f.path) for f in files_to_update])}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            logging.info(f"New branch created: {branch_name}")
            return branch_name
        except Exception as e:
            logging.error(f"Failed to create new branch: {str(e)}")
            return None

    def _commit_changes(self, branch_name: str):
        """
        Commit changes to the current Git branch.

        Args:
            branch_name (str): Name of the current branch.
        """
        if not self.repo:
            return
        logging.info(f"Committing changes to branch: {branch_name}")
        self.repo.git.add(A=True)
        self.repo.index.commit(f"Update files in branch {branch_name}")
        logging.info("Changes committed")

    def _trigger_merge(self, branch_name: str):
        """
        Trigger a merge operation in VS Code.

        Args:
            branch_name (str): Name of the branch to merge.
        """
        if not self.repo:
            return
        logging.info(f"Triggering merge for branch: {branch_name}")
        vscode_executable = os.getenv('VSCODE_EXECUTABLE', 'code')
        try:
            subprocess.run([vscode_executable, '--wait', '--merge',
                           'main', branch_name], check=True, cwd=self.git_repo_path)
            logging.info("Merge triggered in VS Code")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error triggering merge: {str(e)}")

    def _update_monitored_file(self, report: str, content: str):
        """
        Update the monitored file with the generated report.

        Args:
            report (str): The generated report to prepend to the file.
            content (str): The original content of the file.
        """
        logging.info("Updating monitored file with report")
        updated_content = report + content
        with open(self.file_to_monitor, 'w') as file:
            file.write(updated_content)
        # Copy to log folder
        log_file_path = os.path.join(
            self.log_folder, f"parsed_{os.path.basename(self.file_to_monitor)}")
        shutil.copy2(self.file_to_monitor, log_file_path)
        logging.info(f"Monitored file updated and copied to: {log_file_path}")

    def _log_instruction_blocks(self):
        """
        Log instruction blocks to separate files in the log folder.
        """
        logging.info("Logging instruction blocks")
        for i, (instruction, line_number) in enumerate(self.parser.instruction_blocks, 1):
            log_file_path = os.path.join(
                self.log_folder, f"instruction_block_{i}.md")
            with open(log_file_path, 'w') as file:
                file.write(f"Line {line_number}: {instruction}\n")
            logging.info(f"Instruction block logged: {log_file_path}")

    def update_weaver_file(self, file_path: str, comment_style: str):
        """
        Update the .weaver file with the new file extension and comment style.

        Args:
            file_path (str): The file path.
            comment_style (str): The comment style used.
        """
        extension = os.path.splitext(file_path)[1]
        weaver_file_path = '.weaver'

        if os.path.exists(weaver_file_path):
            with open(weaver_file_path, 'r') as f:
                weaver_data = json.load(f)
        else:
            weaver_data = {}

        if 'file_extensions' not in weaver_data:
            weaver_data['file_extensions'] = {}

        weaver_data['file_extensions'][extension] = comment_style

        with open(weaver_file_path, 'w') as f:
            json.dump(weaver_data, f, indent=2)

        logging.info(
            f"Updated .weaver file with extension {extension} and comment style {comment_style}")
