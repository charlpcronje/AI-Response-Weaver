# AI Response Weaver Project Files

## .gitignore
```gitignore
# File: .gitignore
# Python
__pycache__/
*.py[cod]
*.class
venv/

# Environment variables
.env

# Logs
logs/
*.log

# IDE specific files
.vscode/
.idea/

# Temporary files
*.tmp

# Operating system files
.DS_Store
Thumbs.db

# AI Response Weaver specific
.weaver

```

## requirements-dev.txt
```txt
# File: requirements-dev.txt
pytest==7.3.1
pytest-mock==3.10.0
```

## requirements.txt
```txt
# File: requirements.txt
watchdog==2.1.9
gitpython==3.1.30
python-dotenv>=1.0.0,<2.0.0
chainlit==1.0.0
pygments
```

## setup.py
```py
# File: setup.py
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    required = f.read().splitlines()

setup(
    name="ai-response-weaver",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=required,
    entry_points={
        "console_scripts": [
            "weaver=ai_response_weaver.weaver:main",
        ],
    },
)

```

## __init__.py
```py
# __init__.py

from .weaver import main
from .file_handler import AIResponseWeaver
from .parser import CustomParser
from .utils import get_weaver_settings
from .config import load_config

__all__ = ['main', 'AIResponseWeaver', 'CustomParser',
           'get_weaver_settings', 'load_config']

```

## config.py
```py
# config.py

import os
import json


def load_config():
    """
    Load the configuration from the config.json file.

    Returns:
        dict: The loaded configuration.
    """
    print("DEBUG: load_config - Loading configuration")
    config_path = os.path.join(os.path.dirname(
        __file__), '..', 'config', 'config.json')
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    print("DEBUG: load_config - Configuration loaded")
    return config

```

## file_handler.py
```py
# file_handler.py
import os
import shutil
import logging
import json
from datetime import datetime
from typing import List, Optional
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

    def _create_file(self, file_info: 'FileInfo'):
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

    def _update_file(self, file_info: 'FileInfo'):
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

```

## parser.py
```py
# parser.py

import os
import re
import logging
from typing import List, Optional, Tuple
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import TerminalFormatter


class ParserState:
    """
    Enum-like class to represent the state of the parser.
    """
    SCANNING = 1  # The parser is scanning for new blocks or instructions
    IN_CODE_BLOCK = 2  # The parser is currently inside a code block
    IN_INSTRUCTION_BLOCK = 3  # The parser is inside an instruction block
    IN_NESTED_CODE_BLOCK = 4  # The parser is inside a nested code block


class FileInfo:
    """
    Represents information about a file extracted from a code block.

    Attributes:
        path (str): The path of the file.
        content (List[str]): The content of the file as a list of strings.
    """

    def __init__(self, path: str, content: List[str]):
        """
        Initialize a FileInfo object.

        Args:
            path (str): The path of the file.
            content (List[str]): The content of the file as a list of strings.
        """
        self.path = path
        self.content = content


class CustomParser:
    """
    Parses content to extract file information and instruction blocks.

    This class is responsible for parsing AI-generated responses, handling nested code blocks,
    collecting instructions, and generating comprehensive reports.

    Attributes:
        config (dict): Configuration dictionary containing parsing rules and settings.
        ui (UserInterface): User interface object for handling user interactions.
        state (int): Current state of the parser (from ParserState).
        current_file (FileInfo): Currently processed file information.
        instruction_blocks (List[Tuple[str, int]]): List of collected instructions and their line numbers.
        files (List[FileInfo]): List of processed FileInfo objects.
        code_block_count (int): Count of code blocks encountered.
        instruction_block_count (int): Count of instruction blocks encountered.
        current_code_block (List[str]): Content of the current code block being processed.
        current_line_number (int): Current line number being processed.
        code_block_stack (List[Tuple[int, List[str]]]): Stack to manage nested code blocks.
        current_code_block_type (Optional[str]): Type of the current code block (e.g., 'python', 'javascript').
        lines (List[str]): All lines of the content being parsed.
        current_line_index (int): Index of the current line being processed.
        nested_block_decision (Optional[str]): User's decision on how to handle nested blocks ('separate' or 'parent').
        in_parent_block (bool): Flag indicating if the parser is currently inside a parent block.
        nested_block_count (int): Counter for tracking the nesting level of code blocks.
    """

    def __init__(self, config: dict, ui):
        """
        Initialize the CustomParser.

        Args:
            config (dict): Configuration dictionary containing parsing rules and settings.
            ui (UserInterface): User interface object for handling user interactions.
        """
        self.config = config
        self.ui = ui
        self.state = ParserState.SCANNING
        self.current_file = None
        self.instruction_blocks = []
        self.files = []
        self.code_block_count = 0
        self.instruction_block_count = 0
        self.current_code_block = []
        self.current_line_number = 0
        self.code_block_stack = []
        self.current_code_block_type = None
        self.lines = []
        self.current_line_index = -1
        self.nested_block_decision = None
        self.in_parent_block = False
        self.nested_block_count = 0

    def parse(self, content: str) -> str:
        """
        Parse the given content and extract file information and instruction blocks.

        This method processes the content line by line, handling different parsing states,
        and generates a comprehensive report of the parsing results.

        Args:
            content (str): The content to parse.

        Returns:
            str: A report of the parsing results.

        Raises:
            ValueError: If an unknown parser state is encountered.
        """
        logging.info("Starting to parse content")
        self.lines = content.split('\n')
        self.current_line_index = -1

        try:
            while self.current_line_index < len(self.lines) - 1:
                self.current_line_index += 1
                line = self.lines[self.current_line_index]
                self.current_line_number = self.current_line_index + 1

                logging.debug(
                    f"Processing line {self.current_line_number}: {line[:30]}...")

                if not self._validate_line(line):
                    logging.warning(
                        f"Invalid line detected at line {self.current_line_number}")
                    continue

                logging.debug(f"Current parser state: {self.state}")

                if self.state == ParserState.SCANNING:
                    self._handle_scanning_state(line)
                elif self.state == ParserState.IN_CODE_BLOCK:
                    self._handle_code_block_state(line)
                elif self.state == ParserState.IN_INSTRUCTION_BLOCK:
                    self._handle_instruction_block_state(line)
                elif self.state == ParserState.IN_NESTED_CODE_BLOCK:
                    self._handle_nested_code_block_state(line)
                else:
                    logging.error(
                        f"Unknown parser state at line {self.current_line_number}")
                    raise ValueError(f"Unknown parser state: {self.state}")

        except Exception as e:
            logging.error(
                f"Error occurred while parsing at line {self.current_line_number}: {str(e)}")
            raise

        logging.info(
            f"Parsing complete. Found {len(self.files)} files and {self.code_block_count} code blocks")
        return self._generate_report()

    def _validate_line(self, line: str) -> bool:
        """
        Validate a line before processing.

        This method performs basic validation on each line to ensure it meets
        certain criteria before being processed.

        Args:
            line (str): The line to validate.

        Returns:
            bool: True if the line is valid, False otherwise.
        """
        if len(line) > 1000:  # Example validation: line length
            logging.warning(
                f"Line {self.current_line_number} exceeds maximum length of 1000 characters")
            return False
        if not line.isprintable():
            logging.warning(
                f"Line {self.current_line_number} contains non-printable characters")
            return False
        return True

    def _handle_nested_code_block_state(self, line: str):
        if line.strip().startswith('```'):
            nested_parser = CustomParser(self.config, self.ui)
            nested_content = '\n'.join(self.current_code_block)
            nested_parser.parse(nested_content)

            self.files.extend(nested_parser.files)
            self.instruction_blocks.extend(nested_parser.instruction_blocks)
            self.code_block_count += nested_parser.code_block_count
            self.instruction_block_count += nested_parser.instruction_block_count

            self.state, self.current_code_block = self.code_block_stack.pop()
        else:
            self.current_code_block.append(line)

    def _handle_scanning_state(self, line: str):
        """
        Handle the scanning state of the parser.

        This method processes lines when the parser is in the scanning state,
        looking for code blocks, instructions, or file paths.

        Args:
            line (str): The line to process.
        """
        logging.debug(f"Scanning state: Processing line: {line[:50]}...")

        if line.strip().startswith('```'):
            logging.info(f"Detected code block start: {line[:50]}...")
            self._handle_code_block_start(line)
        else:
            instruction = self._extract_instruction(line)
            if instruction:
                logging.info(f"Extracted instruction: {instruction[:50]}...")
                self._collect_instruction(instruction)
            else:
                file_path = self._extract_file_path(line)
                if file_path:
                    logging.info(f"Extracted file path: {file_path}")
                    if self.current_file:
                        self.files.append(self.current_file)
                    self.current_file = FileInfo(file_path, [])
                    self.state = ParserState.IN_CODE_BLOCK
                    self.current_code_block = []
                else:
                    logging.debug(
                        "Line does not contain code block, instruction, or file path")

        logging.debug(f"After processing, parser state is: {self.state}")

    def _determine_code_block_type(self, line: str) -> str:
        """
        Determine the type of code block based on the opening line.

        Args:
            line (str): The line containing the code block opening.

        Returns:
            str: The type of code block (e.g., 'python', 'javascript'), or 'unknown' if not determined.
        """
        match = re.search(r'```(\w+)', line)
        return match.group(1) if match else 'unknown'

    def _handle_code_block_state(self, line: str):
        """
        Handle the code block state of the parser.

        Args:
            line (str): The line to process.
        """
        logging.debug(f"Processing line in code block state: {line}")

        if line.strip() == '```':
            # This is a closing tag for the current code block
            logging.debug("Detected end of current code block")
            self._handle_code_block_end()
        elif line.strip().startswith('```'):
            # This is the start of a nested code block
            logging.debug("Detected start of nested code block")
            self._handle_nested_code_block_start(line)
        else:
            # This is content within the current code block
            self.current_code_block.append(line)

    def _handle_nested_code_block_start(self, line: str):
        """
        Handle the start of a nested code block.

        Args:
            line (str): The line containing the nested code block start.
        """
        logging.debug(f"Handling nested code block start: {line}")
        self.nested_block_count += 1
        self.current_code_block.append(line)

        # Collect the content of the nested code block
        while True:
            next_line = self._get_next_line()
            if next_line is None:
                logging.warning(
                    "Reached end of file while parsing nested code block")
                break
            self.current_line_index += 1
            self.current_code_block.append(next_line)
            if next_line.strip() == '```':
                logging.debug("Detected end of nested code block")
                self.nested_block_count -= 1
                break

        if self.nested_block_count == 0:
            logging.debug(
                "All nested blocks closed, returning to main code block")
        else:
            logging.debug(f"Nested block count: {self.nested_block_count}")

    def _handle_instruction_block_state(self, line: str):
        """
        Handle the instruction block state of the parser.

        This method processes lines when the parser is inside an instruction block,
        collecting instructions and detecting the end of the block.

        Args:
            line (str): The line to process.
        """
        logging.debug("Processing line in instruction block state")
        if line.strip().startswith('```'):
            self.state = ParserState.SCANNING
            logging.debug("Ended instruction block")
        else:
            self._collect_instruction(line)

    def _collect_instruction(self, instruction: str):
        """
        Collect an instruction and add it to the instruction blocks.

        Args:
            instruction (str): The instruction to collect.
        """
        self.instruction_blocks.append((instruction, self.current_line_number))
        self.instruction_block_count += 1

    def _extract_instruction(self, line: str) -> Optional[str]:
        """
        Extract an instruction from a given line.

        This method checks for various formats of instructions, including:
        - Lines starting with "Instruction:" or "TODO:"
        - Lines containing "IMPORTANT:" or "NOTE:"
        - Lines enclosed in square brackets []

        Args:
            line (str): The line to check for instructions.

        Returns:
            Optional[str]: The extracted instruction if found, None otherwise.
        """
        line = line.strip()

        # Check for lines starting with "Instruction:" or "TODO:"
        if line.lower().startswith(("instruction:", "todo:")):
            return line

        # Check for lines containing "IMPORTANT:" or "NOTE:"
        if "important:" in line.lower() or "note:" in line.lower():
            return line

        # Check for lines enclosed in square brackets
        if line.startswith('[') and line.endswith(']'):
            return line[1:-1]  # Remove the brackets

        return None

    def _get_next_line(self) -> Optional[str]:
        """
        Get the next line from the content being parsed.

        Returns:
            Optional[str]: The next line if available, None if at the end of the content.
        """
        if self.current_line_index + 1 < len(self.lines):
            return self.lines[self.current_line_index + 1]
        return None

    def _handle_code_block_start(self, line: str):
        logging.debug(f"Entering _handle_code_block_start with line: {line}")

        file_path = self._extract_file_path(line)
        logging.debug(f"Extracted file path: {file_path}")

        # Collect the content of the code block
        self.current_code_block = [line]
        logging.debug("Starting to collect code block content")
        while True:
            next_line = self._get_next_line()
            logging.debug(f"Next line: {next_line}")
            if next_line is None or next_line.strip().startswith('```'):
                logging.debug("Reached end of code block")
                break
            self.current_line_index += 1
            self.current_code_block.append(next_line)
        logging.debug(f"Collected code block: {self.current_code_block}")

        # Display the code block and get user action
        logging.info("About to display code block and prompt for action")
        action = self.ui.display_code_block('\n'.join(self.current_code_block),
                                            self.current_line_number,
                                            len(self.current_code_block))
        logging.info(f"Received action from user: {action}")

        # Handle the action
        if action == 'instruction':
            logging.debug("Handling as instruction")
            self.state = ParserState.IN_INSTRUCTION_BLOCK
            self.instruction_block_count += 1
        elif action == 'code':
            logging.debug("Handling as code")
            if not file_path:
                file_path = self.ui.prompt_for_manual_file_path()
            if file_path:
                self.state = ParserState.IN_CODE_BLOCK
                self.current_file = FileInfo(
                    file_path, self.current_code_block)
                self.code_block_count += 1
        elif action == 'ignore':
            logging.debug("Ignoring code block")
            self.state = ParserState.SCANNING
        else:
            logging.warning(f"Unknown action: {action}. Ignoring code block.")
            self.state = ParserState.SCANNING

        logging.debug(
            f"Exiting _handle_code_block_start. Current state: {self.state}")

    def _handle_code_block_end(self):
        """
        Handle the end of a code block.
        """
        logging.debug("Handling end of code block")
        self.state = ParserState.SCANNING

        # Display the code block and prompt for action
        action = self.ui.display_code_block('\n'.join(self.current_code_block),
                                            self.current_line_number,
                                            len(self.current_code_block))

        self._process_code_block_action(action)

    def _process_code_block_action(self, action: str):
        """
        Process the user's action for the code block.

        Args:
            action (str): The action chosen by the user.
        """
        logging.info(f"Processing action for code block: {action}")
        if action == 'instruction':
            self.instruction_blocks.extend(self.current_code_block)
            self.instruction_block_count += 1
        elif action == 'code':
            file_path = self._extract_file_path(self.current_code_block[0])
            if not file_path:
                file_path = self.ui.prompt_for_manual_file_path()
            if file_path:
                self.files.append(FileInfo(file_path, self.current_code_block))
                self.code_block_count += 1
        elif action == 'ignore':
            logging.info("Code block ignored")
        else:
            logging.warning(f"Unknown action: {action}. Ignoring code block.")

        self.current_code_block = []
        self.current_code_block_type = None

    def _process_nested_code_blocks(self, content: List[str]):
        """
        Process nested code blocks within content blocks.

        Args:
            content (List[str]): The content of the current code block.
        """
        nested_parser = CustomParser(self.config, self.ui)
        nested_content = '\n'.join(content)
        nested_parser.parse(nested_content)

        # Merge results from nested parsing
        self.files.extend(nested_parser.files)
        self.instruction_blocks.extend(nested_parser.instruction_blocks)
        self.code_block_count += nested_parser.code_block_count
        self.instruction_block_count += nested_parser.instruction_block_count

    def _extract_file_extension(self, line: str) -> Optional[str]:
        """
        Extract the file extension from the line.

        Args:
            line (str): The line to extract the file extension from.

        Returns:
            Optional[str]: The extracted file extension, or None if not found.
        """
        match = re.search(r'```(\w+)', line)
        if match:
            return match.group(1)

        if self.current_code_block:
            first_line = self.current_code_block[0]
            match = re.search(r'\.(\w+)\s*$', first_line)
            if match:
                return match.group(1)

        return None

    def _prompt_for_file_extension(self) -> str:
        """
        Prompt the user for the file extension.

        Returns:
            str: The file extension provided by the user.
        """
        return self.ui.prompt_for_file_extension()

    def _display_code_block_info(self, file_extension: str):
        """
        Display information about the current code block.

        Args:
            file_extension (str): The file extension of the code block.
        """
        self.ui.display_code_block_info(
            self.current_line_number, file_extension)

    def _process_code_block(self, file_extension: str):
        """
        Process the current code block.

        Args:
            file_extension (str): The file extension of the code block.
        """
        highlighted_code = self._highlight_code(
            self.current_code_block, file_extension)
        self.ui.display_code_block(
            highlighted_code, self.current_line_number, len(self.current_code_block))

        comment_style = self._get_comment_style(file_extension)
        if not comment_style:
            comment_style = self.ui.prompt_for_comment_style(
                list(self.config['comment_styles'].keys()))

        file_path = self._extract_file_path_from_code_block(comment_style)
        if file_path:
            self.current_file = FileInfo(file_path, self.current_code_block)
        else:
            self._handle_code_block_without_file_path()

    def _highlight_code(self, code: List[str], file_extension: str) -> str:
        """
        Apply syntax highlighting to the code.

        Args:
            code (List[str]): The code to highlight.
            file_extension (str): The file extension to determine the language.

        Returns:
            str: The highlighted code.
        """
        try:
            lexer = get_lexer_by_name(file_extension)
            return highlight('\n'.join(code), lexer, TerminalFormatter())
        except:
            return '\n'.join(code)

    def _get_comment_style(self, file_extension: str) -> Optional[str]:
        """
        Get the comment style for the given file extension.

        Args:
            file_extension (str): The file extension.

        Returns:
            Optional[str]: The comment style, or None if not found.
        """
        for file_type, type_config in self.config['file_types'].items():
            if file_extension in type_config['extensions']:
                return type_config['comment_styles'][0]
        return None

    def _extract_file_path(self, line: str) -> Optional[str]:
        """
        Extract a file path from a given line.

        This method checks if the line contains a valid file path, either as a standalone path
        or within a comment. It supports various comment styles defined in the configuration.

        Args:
            line (str): The line to extract the file path from.

        Returns:
            Optional[str]: The extracted file path, or None if no valid path is found.
        """
        if self._is_valid_file_path(line.strip()):
            return line.strip()

        for comment_style, prefixes in self.config['comment_styles'].items():
            for prefix in prefixes:
                if line.strip().startswith(prefix):
                    potential_path = line.strip()[len(prefix):].strip()
                    if self._is_valid_file_path(potential_path):
                        return potential_path

        return None

    def _get_comment_style_for_extension(self, file_extension: str) -> Optional[str]:
        """
        Get the appropriate comment style for a given file extension.

        Args:
            file_extension (str): The file extension to look up.

        Returns:
            Optional[str]: The comment style for the given extension, or None if not found.
        """
        for file_type, type_info in self.config['file_types'].items():
            if file_extension in type_info['extensions']:
                # Return the first comment style
                return type_info['comment_styles'][0]
        return None

    def _extract_file_path_from_code_block(self, comment_style: str) -> Optional[str]:
        """
        Extract the file path from the current code block using the given comment style.

        Args:
            comment_style (str): The comment style to use.

        Returns:
            Optional[str]: The extracted file path, or None if not found.
        """
        if not self.current_code_block:
            return None

        first_line = self.current_code_block[0]
        comment_prefix = self.config['comment_styles'][comment_style][0]
        if first_line.strip().startswith(comment_prefix):
            potential_path = first_line.strip()[len(comment_prefix):].strip()
            if self._is_valid_file_path(potential_path):
                return potential_path
        return None

    def _is_valid_file_path(self, path: str) -> bool:
        """
        Check if a given string is a valid file path.

        This method performs various checks to determine if the given string
        represents a valid file path.

        Args:
            path (str): The string to check as a file path.

        Returns:
            bool: True if the string is a valid file path, False otherwise.
        """
        logging.debug(f"Validating path: {path}")
        path = path.strip()
        if not path:
            logging.debug("Path is empty")
            return False
        invalid_chars = set('<>:"|?*')
        if any(char in invalid_chars for char in path):
            logging.debug("Path contains invalid characters")

    def _handle_code_block_without_file_path(self):
        """
        Handle a code block that doesn't have a clear file path.
        """
        choice = self.ui.prompt_for_code_block_action()
        if choice == 'instruction':
            self.instruction_blocks.extend(
                [(line, self.current_line_number + i) for i, line in enumerate(self.current_code_block)])
            self.instruction_block_count += 1
        elif choice == 'manual':
            file_path = self.ui.prompt_for_manual_file_path()
            if file_path:
                self.current_file = FileInfo(
                    file_path, self.current_code_block)
                self.files.append(self.current_file)

    def _generate_report(self) -> str:
        """
        Generate a report of the parsing results.

        Returns:
            str: The generated report.
        """
        logging.debug("CustomParser._generate_report - Generating report")
        report = "---\n"
        report += f"Parsed: true\n"
        report += f"Files code blocks found: {len(self.files)}\n"
        report += f"Instruction blocks found: {self.instruction_block_count}\n"
        report += f"Files found: {len(self.files)}\n"
        report += f"New files created: {len(self.files)}\n"
        for i, file in enumerate(self.files, 1):
            report += f"   {i}. {file.path}\n"
        report += "Files updated: 0\n"
        report += "Instructions:\n"
        for instruction, line_number in self.instruction_blocks:
            report += f"   Line {line_number}: {instruction}\n"
        report += "---\n"
        logging.debug("CustomParser._generate_report - Report generated")
        return report

```

## user_interface.py
```py
# user_interface.py

import os
from typing import List, Tuple
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import TerminalFormatter
import logging


class UserInterface:
    """
    Handles user interactions for the AI Response Weaver.

    This class provides methods for displaying information to the user,
    prompting for input, and handling navigation through code blocks.
    """

    def __init__(self):
        """
        Initialize the UserInterface.
        """
        self.lines_per_page = 20

    def display_code_block(self, highlighted_code: str, start_line: int, total_lines: int) -> str:
        logging.debug("Entering display_code_block method")
        lines = highlighted_code.split('\n')
        total_pages = (len(lines) - 1) // self.lines_per_page + 1
        current_page = 0

        while True:
            # Clear the screen (you might need to adjust this based on your OS)
            print("\033c", end="")

            start = current_page * self.lines_per_page
            end = start + self.lines_per_page
            print(
                f"\n----------- Lines {start_line + start}-{start_line + end - 1} of {start_line + total_lines - 1} ------------")
            for i, line in enumerate(lines[start:end], start + 1):
                print(f"{start_line + i - 1:4d} | {line}")
            print("-" * 60)
            print(f"Page {current_page + 1} of {total_pages}")

            print("\nActions:")
            print("n - Next page")
            print("p - Previous page")
            print("1 - Treat as instruction block")
            print("2 - Treat as code block")
            print("3 - Ignore this block")

            choice = input("Enter your choice: ").lower()

            if choice == 'n' and current_page < total_pages - 1:
                current_page += 1
            elif choice == 'p' and current_page > 0:
                current_page -= 1
            elif choice in ['1', '2', '3']:
                return self._process_action_choice(choice)
            else:
                print("Invalid choice. Please try again.")

        logging.debug("Exiting display_code_block method")

    def _process_action_choice(self, choice: str) -> str:
        if choice == '1':
            return 'instruction'
        elif choice == '2':
            return 'code'
        else:
            return 'ignore'

    def prompt_for_nested_block_action(self) -> str:
        logging.debug("Entering prompt_for_nested_block_action method")
        print("\nFound a nested code block. How would you like to handle it?")
        print("1. Parse as part of the parent block")
        print("2. Parse as a separate document")
        while True:
            choice = input("Enter your choice (1 or 2): ").strip()
            if choice == '1':
                logging.debug("User chose to parse as part of parent block")
                return 'parent'
            elif choice == '2':
                logging.debug("User chose to parse as separate document")
                return 'separate'
            else:
                print("Invalid choice. Please enter 1 or 2.")
        logging.debug("Exiting prompt_for_nested_block_action method")

    def prompt_for_file_extension(self) -> str:
        """
        Prompt the user for the file extension.

        Returns:
            str: The file extension provided by the user.
        """
        return input("Enter the file extension for this code block: ").strip()

    def prompt_for_comment_style(self, available_styles: List[str]) -> str:
        """
        Prompt the user to select a comment style for the code block.

        Args:
            available_styles (List[str]): List of available comment styles.

        Returns:
            str: The selected comment style.
        """
        print("\nSelect a comment style for this code block:")
        for i, style in enumerate(available_styles, 1):
            print(f"{i}. {style}")

        while True:
            try:
                choice = int(input("Enter your choice: "))
                if 1 <= choice <= len(available_styles):
                    return available_styles[choice - 1]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    def prompt_for_code_block_action(self, code_block_type: str) -> str:
        logging.debug(
            f"Entering prompt_for_code_block_action method with code_block_type: {code_block_type}")
        print(
            f"\nFound a {code_block_type} code block. What would you like to do?")
        print("1. Treat as instruction block")
        print("2. Enter file path manually")
        print("3. Parse as nested code block")
        print("4. Ignore this code block")

        while True:
            choice = input("Enter your choice (1-4): ").strip()
            if choice == '1':
                logging.debug("User chose to treat as instruction block")
                return 'instruction'
            elif choice == '2':
                logging.debug("User chose to enter file path manually")
                return 'code'
            elif choice == '3':
                logging.debug("User chose to parse as nested code block")
                return 'nested'
            elif choice == '4':
                logging.debug("User chose to ignore this code block")
                return 'ignore'
            else:
                print("Invalid choice. Please enter a number between 1 and 4.")
        logging.debug("Exiting prompt_for_code_block_action method")

    # def prompt_for_code_block_action(self, code_block_type: str) -> str:
    #     logging.debug(
    #         f"Entering prompt_for_code_block_action with code_block_type: {code_block_type}")
    #     print("\nWhat would you like to do with this code block?")
    #     print("1. Treat as instruction block")
    #     print("2. Treat as code block")
    #     print("3. Ignore this block")

    #     while True:
    #         choice = input("Enter your choice (1-3): ").strip()
    #         logging.debug(f"User input for code block action: {choice}")
    #         if choice == '1':
    #             logging.debug("User chose to treat as instruction block")
    #             return 'instruction'
    #         elif choice == '2':
    #             logging.debug("User chose to treat as code block")
    #             return 'code'
    #         elif choice == '3':
    #             logging.debug("User chose to ignore this block")
    #             return 'ignore'
    #         else:
    #             print("Invalid choice. Please enter a number between 1 and 3.")
    #     logging.debug("Exiting prompt_for_code_block_action method")

    def prompt_for_manual_file_path(self) -> str:
        """
        Prompt the user to manually enter a file path.

        Returns:
            str: The manually entered file path.
        """
        logging.debug("Entering prompt_for_manual_file_path method")
        file_path = input("Enter the file path for this code block: ").strip()
        logging.debug(f"User entered file path: {file_path}")
        return file_path

    def confirm_file_path(self) -> bool:
        """
        Prompt the user to confirm the extracted file path.

        Returns:
            bool: True if the user confirms, False otherwise.
        """
        while True:
            choice = input("Is this file path correct? (y/n): ").lower()
            if choice in ['y', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False
            else:
                print("Invalid input. Please enter 'y' or 'n'.")

    def display_file_path_info(self, comment_style: str, comment_prefix: str, first_line: str, relative_path: str, absolute_path: str):
        """
        Display information about the extracted file path.

        Args:
            comment_style (str): The comment style used.
            comment_prefix (str): The comment prefix.
            first_line (str): The first line of the code block.
            relative_path (str): The extracted relative file path.
            absolute_path (str): The corresponding absolute file path.
        """
        print(f"\nComment style: {comment_style}")
        print(f"Comment prefix: {comment_prefix}")
        print(f"First line: {first_line}")
        print(f"Extracted relative path: {relative_path}")
        print(f"Corresponding absolute path: {absolute_path}")

```

## utils.py
```py
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

```

## weaver.py
```py
# weaver.py

import os
import sys
import time
import logging
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .file_handler import AIResponseWeaver
from .utils import get_weaver_settings, resolve_path
from .config import load_config
from .user_interface import UserInterface

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


def setup_file_monitoring(file_to_monitor: str, weaver: AIResponseWeaver) -> Observer:
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

```

## config.json
```json
{
  "file_types": {
    "web": {
      "extensions": [
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".styl",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".vue",
        ".svelte"
      ],
      "comment_styles": [
        "html",
        "css",
        "js"
      ]
    },
    "markup": {
      "extensions": [
        ".md",
        ".markdown",
        ".rst",
        ".txt"
      ],
      "comment_styles": [
        "html"
      ]
    },
    "data": {
      "extensions": [
        ".json",
        ".json5",
        ".yaml",
        ".yml",
        ".xml",
        ".toml"
      ],
      "comment_styles": [
        "hash",
        "xml"
      ]
    },
    "config": {
      "extensions": [
        ".env",
        ".ini",
        ".cfg",
        ".conf",
        ".gitignore",
        ".gitattributes",
        ".editorconfig"
      ],
      "comment_styles": [
        "hash"
      ]
    },
    "script": {
      "extensions": [
        ".sh",
        ".bash",
        ".zsh",
        ".fish"
      ],
      "comment_styles": [
        "hash"
      ]
    },
    "python": {
      "extensions": [
        ".py",
        ".pyw",
        ".pyx",
        ".pxd",
        ".pyi"
      ],
      "comment_styles": [
        "hash",
        "python_docstring"
      ]
    },
    "ruby": {
      "extensions": [
        ".rb",
        ".rake",
        ".gemspec"
      ],
      "comment_styles": [
        "hash"
      ]
    },
    "php": {
      "extensions": [
        ".php",
        ".php5",
        ".php4",
        ".php3",
        ".phtml"
      ],
      "comment_styles": [
        "doubleslash",
        "hash",
        "php_docstring"
      ]
    },
    "java": {
      "extensions": [
        ".java",
        ".class",
        ".jar"
      ],
      "comment_styles": [
        "doubleslash",
        "java_docstring"
      ]
    },
    "csharp": {
      "extensions": [
        ".cs",
        ".csx"
      ],
      "comment_styles": [
        "doubleslash",
        "csharp_docstring"
      ]
    },
    "cpp": {
      "extensions": [
        ".cpp",
        ".hpp",
        ".c",
        ".h",
        ".cc",
        ".hh"
      ],
      "comment_styles": [
        "doubleslash",
        "multiline"
      ]
    },
    "go": {
      "extensions": [
        ".go"
      ],
      "comment_styles": [
        "doubleslash"
      ]
    },
    "rust": {
      "extensions": [
        ".rs"
      ],
      "comment_styles": [
        "doubleslash"
      ]
    },
    "swift": {
      "extensions": [
        ".swift"
      ],
      "comment_styles": [
        "doubleslash"
      ]
    },
    "sql": {
      "extensions": [
        ".sql"
      ],
      "comment_styles": [
        "doublehyphen",
        "hash"
      ]
    }
  },
  "comment_styles": {
    "hash": [
      "#"
    ],
    "doubleslash": [
      "//"
    ],
    "html": [
      "<!--"
    ],
    "css": [
      "/*"
    ],
    "js": [
      "//",
      "/*"
    ],
    "xml": [
      "<!--"
    ],
    "doublehyphen": [
      "--"
    ],
    "multiline": [
      "/*"
    ],
    "python_docstring": [
      "\"\"\""
    ],
    "php_docstring": [
      "/**"
    ],
    "java_docstring": [
      "/**"
    ],
    "csharp_docstring": [
      "///"
    ]
  }
}
```
