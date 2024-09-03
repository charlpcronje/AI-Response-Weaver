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
    SCANNING = 1
    IN_CODE_BLOCK = 2
    IN_INSTRUCTION_BLOCK = 3
    IN_NESTED_CODE_BLOCK = 4


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
        self.current_line_number = 0
        self.code_block_stack = []

    def parse(self, content: str) -> str:
        """
        Parse the given content and extract file information and instruction blocks.

        Args:
            content (str): The content to parse.

        Returns:
            str: A report of the parsing results.
        """
        logging.debug("CustomParser.parse - Starting to parse content")
        lines = content.split('\n')
        for self.current_line_number, line in enumerate(lines, 1):
            if self.state == ParserState.SCANNING:
                self._handle_scanning_state(line)
            elif self.state == ParserState.IN_CODE_BLOCK:
                self._handle_code_block_state(line)
            elif self.state == ParserState.IN_INSTRUCTION_BLOCK:
                self._handle_instruction_block_state(line)
            elif self.state == ParserState.IN_NESTED_CODE_BLOCK:
                self._handle_nested_code_block_state(line)

        # Handle any remaining current_file
        if self.current_file and self.current_code_block:
            self.current_file.content = self.current_code_block
            self.files.append(self.current_file)

        logging.debug(
            f"CustomParser.parse - Parsing complete. Found {len(self.files)} files and {self.code_block_count} code blocks")
        return self._generate_report()

    def _handle_scanning_state(self, line: str):
        """
        Handle the scanning state of the parser.

        Args:
            line (str): The line to process.
        """
        logging.debug(
            f"CustomParser._handle_scanning_state - Processing line: {line[:30]}...")
        if line.strip().startswith('```'):
            self._handle_code_block_start(line)
        else:
            file_path = self._extract_file_path(line)
            if file_path:
                if self.current_file:
                    self.files.append(self.current_file)
                self.current_file = FileInfo(file_path, [])
                self.state = ParserState.IN_CODE_BLOCK
                self.current_code_block = []
                logging.debug(
                    f"CustomParser._handle_scanning_state - Found file path: {file_path}")

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
        self._handle_code_block_end()
    elif line.strip().startswith('```') and self._extract_file_extension(line):
        self._handle_code_block_start(line)
    else:
        self.current_code_block.append(line)

    def _handle_instruction_block_state(self, line: str):
        """
        Handle the instruction block state of the parser.

        Args:
            line (str): The line to process.
        """
        logging.debug(
            "CustomParser._handle_instruction_block_state - Processing line in instruction block")
        if line.strip().startswith('```'):
            self.state = ParserState.SCANNING
            logging.debug(
                "CustomParser._handle_instruction_block_state - Ended instruction block")
        else:
            self.instruction_blocks.append((line, self.current_line_number))

    def _handle_code_block_start(self, line: str):
        """
        Handle the start of a code block.

        Args:
            line (str): The line containing the code block start.
        """
        file_extension = self._extract_file_extension(line)

        if file_extension:
            self.state = ParserState.IN_CODE_BLOCK
            self.current_file = None
            self.current_code_block = []
            self.code_block_count += 1
            self._display_code_block_info(file_extension)
            self._process_code_block(file_extension)
        else:
            self.state = ParserState.IN_NESTED_CODE_BLOCK
            self.code_block_stack.append((self.state, self.current_code_block))
            self.current_code_block = []

    def _handle_code_block_end(self):
        """
        Handle the end of a code block.
        """
        if self.current_file:
            self.current_file.content = self.current_code_block
            self.files.append(self.current_file)
            self.current_file = None
        else:
            self._handle_code_block_without_file_path()
        logging.debug(
            "CustomParser._handle_code_block_state - Ended code block")

    def _extract_file_extension(self, line: str) -> Optional[str]:
        """
        Extract the file extension from the line.

        Args:
            line (str): The line to extract the file extension from.

        Returns:
            Optional[str]: The extracted file extension, or None if not found.
        """
        # Check for file extension next to the opening ```
        match = re.search(r'```(\w+)', line)
        if match:
            return match.group(1)

        # Check for file extension in the first line of the code block
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
        # Check for standalone file path
        if self._is_valid_file_path(line.strip()):
            return line.strip()

        # Check for file path within comments
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
