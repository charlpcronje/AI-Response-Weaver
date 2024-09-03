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
