# parser.py

import os
import re
import logging
from typing import List, Tuple, Optional


class ParserState:
    """
    Enum-like class to represent the state of the parser.
    """
    SCANNING = 1
    IN_CODE_BLOCK = 2
    IN_INSTRUCTION_BLOCK = 3


class FileInfo:
    """
    Represents information about a file extracted from a code block.

    Attributes:
        path (str): The path of the file.
        content (list): The content of the file as a list of strings.
    """

    def __init__(self, path: str, content: List[str]):
        """
        Initialize a FileInfo object.

        Args:
            path (str): The path of the file.
            content (list): The content of the file as a list of strings.
        """
        self.path = path
        self.content = content


class CustomParser:
    """
    Parses content to extract file information and instruction blocks.

    Attributes:
        config (dict): Configuration dictionary.
        state (int): Current state of the parser.
        current_file (FileInfo): Currently processed file information.
        instruction_blocks (list): List of instruction blocks.
        files (list): List of FileInfo objects.
        code_block_count (int): Count of code blocks.
        instruction_block_count (int): Count of instruction blocks.
        current_code_block (list): Content of the current code block.
        ui (UserInterface): User interface object for interactions.
    """

    def __init__(self, config: dict, ui):
        """
        Initialize the CustomParser.

        Args:
            config (dict): Configuration dictionary.
            ui (UserInterface): User interface object for interactions.
        """
        self.config = config
        self.state = ParserState.SCANNING
        self.current_file = None
        self.instruction_blocks = []
        self.files = []
        self.code_block_count = 0
        self.instruction_block_count = 0
        self.current_code_block = []
        self.ui = ui

    def parse(self, content: str) -> str:
        """
        Parse the given content.

        Args:
            content (str): The content to parse.

        Returns:
            str: A report of the parsing results.
        """
        logging.debug("CustomParser.parse - Starting to parse content")
        lines = content.split('\n')
        for line_number, line in enumerate(lines, 1):
            if self.state == ParserState.SCANNING:
                self._handle_scanning_state(line, line_number)
            elif self.state == ParserState.IN_CODE_BLOCK:
                self._handle_code_block_state(line)
            elif self.state == ParserState.IN_INSTRUCTION_BLOCK:
                self._handle_instruction_block_state(line, line_number)

        # Handle any remaining current_file
        if self.current_file and self.current_code_block:
            self.current_file.content = self.current_code_block
            self.files.append(self.current_file)

        logging.debug(
            f"CustomParser.parse - Parsing complete. Found {len(self.files)} files and {self.code_block_count} code blocks")
        return self._generate_report()

    def _handle_scanning_state(self, line: str, line_number: int):
        """
        Handle the scanning state of the parser.

        Args:
            line (str): The line to process.
            line_number (int): The current line number.
        """
        logging.debug(
            f"CustomParser._handle_scanning_state - Processing line: {line[:30]}...")
        file_path = self._extract_file_path(line)
        if file_path:
            if self.current_file:
                self.files.append(self.current_file)
            self.current_file = FileInfo(file_path, [])
            self.state = ParserState.IN_CODE_BLOCK
            self.current_code_block = []
            logging.debug(
                f"CustomParser._handle_scanning_state - Found file path: {file_path}")
        elif line.strip().startswith('```'):
            self.state = ParserState.IN_CODE_BLOCK
            self.current_file = None
            self.current_code_block = []
            self.code_block_count += 1
            logging.debug(
                "CustomParser._handle_scanning_state - Started code block without file path")

    def _handle_code_block_state(self, line: str):
        """
        Handle the code block state of the parser.

        Args:
            line (str): The line to process.
        """
        logging.debug(
            "CustomParser._handle_code_block_state - Processing line in code block")
        if line.strip().startswith('```'):
            self.state = ParserState.SCANNING
            if self.current_file:
                self.current_file.content = self.current_code_block
                self.files.append(self.current_file)
                self.current_file = None
            else:
                self._handle_code_block_without_file_path()
            logging.debug(
                "CustomParser._handle_code_block_state - Ended code block")
        else:
            self.current_code_block.append(line)

    def _handle_instruction_block_state(self, line: str, line_number: int):
        """
        Handle the instruction block state of the parser.

        Args:
            line (str): The line to process.
            line_number (int): The current line number.
        """
        logging.debug(
            "CustomParser._handle_instruction_block_state - Processing line in instruction block")
        if line.strip().startswith('```'):
            self.state = ParserState.SCANNING
            logging.debug(
                "CustomParser._handle_instruction_block_state - Ended instruction block")
        else:
            self.instruction_blocks.append((line, line_number))

    def _extract_file_path(self, line: str) -> Optional[str]:
        """
        Extract the file path from a line.

        Args:
            line (str): The line to extract the file path from.

        Returns:
            str: The extracted file path, or None if no valid path is found.
        """
        logging.debug(f"Attempting to extract file path from: {line[:30]}...")

        for file_type, type_config in self.config['file_types'].items():
            for comment_style in type_config['comment_styles']:
                for comment_prefix in self.config['comment_styles'][comment_style]:
                    if line.strip().startswith(comment_prefix):
                        potential_path = line.strip(
                        )[len(comment_prefix):].strip()
                        if self._is_valid_file_path(potential_path):
                            logging.debug(
                                f"Valid file path found: {potential_path}")
                            return potential_path

        logging.debug("No valid file path found")
        return None

    def _is_valid_file_path(self, path: str) -> bool:
        """
        Check if a given path is a valid file path.

        Args:
            path (str): The path to validate.

        Returns:
            bool: True if the path is valid, False otherwise.
        """
        logging.debug(f"Validating path: {path}")
        path = path.strip()
        if not path:
            logging.debug("Path is empty")
            return False
        invalid_chars = set('<>:"|?*')
        if any(char in invalid_chars for char in path):
            logging.debug("Path contains invalid characters")
            return False
        components = re.split(r'[/\\]', path)
        for component in components:
            if not component:
                logging.debug("Path contains empty components")
                return False
            if component in ('.', '..'):
                continue
            if not re.match(r'^[\w.-]+$', component):
                logging.debug(f"Path contains invalid component: {component}")
                return False
        logging.debug("Path is valid")
        return True

    def _handle_code_block_without_file_path(self):
        """
        Handle a code block that doesn't have a clear file path.
        """
        self.ui.display_code_block(self.current_code_block)
        comment_style = self.ui.prompt_for_comment_style(
            list(self.config['comment_styles'].keys()))

        if comment_style == 'instruction':
            self.instruction_blocks.extend(
                [(line, -1) for line in self.current_code_block])
            self.instruction_block_count += 1
        elif comment_style == 'manual':
            file_path = self.ui.prompt_for_manual_file_path()
            if file_path:
                self.current_file = FileInfo(
                    file_path, self.current_code_block)
                self.files.append(self.current_file)
        else:
            file_path = self._test_comment_style(comment_style)
            if file_path:
                self.current_file = FileInfo(
                    file_path, self.current_code_block)
                self.files.append(self.current_file)
                self._update_weaver_file(file_path, comment_style)

    def _test_comment_style(self, comment_style: str) -> Optional[str]:
        """
        Test the selected comment style to extract a file path.

        Args:
            comment_style (str): The selected comment style.

        Returns:
            str: The extracted file path, or None if no valid path is found.
        """
        comment_prefix = self.config['comment_styles'][comment_style][0]
        first_line = self.current_code_block[0]
        potential_path = first_line.strip()[len(comment_prefix):].strip()

        if self._is_valid_file_path(potential_path):
            relative_path = os.path.normpath(potential_path)
            absolute_path = os.path.abspath(relative_path)
            self.ui.display_file_path_info(
                comment_style, comment_prefix, first_line, relative_path, absolute_path)
            return relative_path if self.ui.confirm_file_path() else None
        return None

    def _update_weaver_file(self, file_path: str, comment_style: str):
        """
        Update the .weaver file with the new file extension and comment style.

        Args:
            file_path (str): The file path.
            comment_style (str): The comment style used.
        """
        extension = os.path.splitext(file_path)[1]
        # Implementation for updating .weaver file goes here

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
