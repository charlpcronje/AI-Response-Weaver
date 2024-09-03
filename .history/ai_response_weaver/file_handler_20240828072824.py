# file_handler.py

import os
import shutil
from datetime import datetime
from git import Repo
import subprocess
from .parser import CustomParser


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

    def __init__(self, file_to_monitor, log_folder, config, git_repo_path=None):
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
        self.parser = CustomParser(config)
        self.repo = None
        self.git_repo_path = git_repo_path or os.getcwd()

        try:
            self.repo = Repo(self.git_repo_path)
            logging.info(f"Git repository detected at {self.git_repo_path}")
        except InvalidGitRepositoryError:
            logging.warning(
                f"No Git repository found at {self.git_repo_path}. Git-related features will be disabled.")


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
        backup_path = self._create_backup(full_path)
        # Update file
        with open(full_path, 'w') as file:
            file.write('\n'.join(file_info.content))
        print(
            f"DEBUG: AIResponseWeaver._update_file - File updated: {full_path}, Backup created: {backup_path}")

    def _create_backup(self, file_path):
        """
        Create a backup of the given file.

        Args:
            file_path (str): Path of the file to backup.

        Returns:
            str: Path of the created backup file.
        """
        print(
            f"DEBUG: AIResponseWeaver._create_backup - Creating backup for file: {file_path}")
        backup_dir = os.path.join(self.log_folder, "history")
        os.makedirs(backup_dir, exist_ok=True)
        file_name = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"{file_name}-{timestamp}")
        shutil.copy2(file_path, backup_path)
        print(
            f"DEBUG: AIResponseWeaver._create_backup - Backup created: {backup_path}")
        return backup_path

    def _create_branch(self, files_to_update):
        """
        Create a new Git branch for the files to be updated.

        Args:
            files_to_update (list): List of FileInfo objects to be updated.

        Returns:
            str: Name of the created branch.
        """
        print("DEBUG: AIResponseWeaver._create_branch - Creating new branch for updates")
        branch_name = f"update-{'-'.join([os.path.basename(f.path) for f in files_to_update])}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        new_branch = self.repo.create_head(branch_name)
        new_branch.checkout()
        print(
            f"DEBUG: AIResponseWeaver._create_branch - New branch created: {branch_name}")
        return branch_name

    def _commit_changes(self, branch_name):
        """
        Commit changes to the current Git branch.

        Args:
            branch_name (str): Name of the current branch.
        """
        print(
            f"DEBUG: AIResponseWeaver._commit_changes - Committing changes to branch: {branch_name}")
        self.repo.git.add(A=True)
        self.repo.index.commit(f"Update files in branch {branch_name}")
        print("DEBUG: AIResponseWeaver._commit_changes - Changes committed")

    def _trigger_merge(self, branch_name):
        """
        Trigger a merge operation in VS Code.

        Args:
            branch_name (str): Name of the branch to merge.
        """
        print(
            f"DEBUG: AIResponseWeaver._trigger_merge - Triggering merge for branch: {branch_name}")
        vscode_executable = os.getenv('VSCODE_EXECUTABLE', 'code')
        try:
            subprocess.run([vscode_executable, '--wait',
                           '--merge', 'main', branch_name], check=True)
            print("DEBUG: AIResponseWeaver._trigger_merge - Merge triggered in VS Code")
        except subprocess.CalledProcessError as e:
            print(
                f"DEBUG: AIResponseWeaver._trigger_merge - Error triggering merge: {str(e)}")

    def _update_monitored_file(self, report, content):
        """
        Update the monitored file with the generated report.

        Args:
            report (str): The generated report to prepend to the file.
            content (str): The original content of the file.
        """
        print("DEBUG: AIResponseWeaver._update_monitored_file - Updating monitored file with report")
        updated_content = report + content
        with open(self.file_to_monitor, 'w') as file:
            file.write(updated_content)
        # Copy to log folder
        log_file_path = os.path.join(
            self.log_folder, f"parsed_{os.path.basename(self.file_to_monitor)}")
        shutil.copy2(self.file_to_monitor, log_file_path)
        print(
            f"DEBUG: AIResponseWeaver._update_monitored_file - Monitored file updated and copied to: {log_file_path}")

    def _log_instruction_blocks(self):
        """
        Log instruction blocks to separate files in the log folder.
        """
        print(
            "DEBUG: AIResponseWeaver._log_instruction_blocks - Logging instruction blocks")
        for i, block in enumerate(self.parser.instruction_blocks, 1):
            log_file_path = os.path.join(
                self.log_folder, f"instruction_block_{i}.md")
            with open(log_file_path, 'w') as file:
                file.write('\n'.join(block))
            print(
                f"DEBUG: AIResponseWeaver._log_instruction_blocks - Instruction block logged: {log_file_path}")
