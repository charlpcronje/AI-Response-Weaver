# parser.py

import re


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

    def __init__(self, path, content):
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
    """

    def __init__(self, config):
        """
        Initialize the CustomParser.

        Args:
            config (dict): Configuration dictionary.
        """
        self.config = config
        self.state = ParserState.SCANNING
        self.current_file = None
        self.instruction_blocks = []
        self.files = []
        self.code_block_count = 0
        self.instruction_block_count = 0
        self.current_code_block = []

    def parse(self, content):
        """
        Parse the given content.

        Args:
            content (str): The content to parse.

        Returns:
            str: A report of the parsing results.
        """
        print("DEBUG: CustomParser.parse - Starting to parse content")
        lines = content.split('\n')
        for line in lines:
            if self.state == ParserState.SCANNING:
                self._handle_scanning_state(line)
            elif self.state == ParserState.IN_CODE_BLOCK:
                self._handle_code_block_state(line)
            elif self.state == ParserState.IN_INSTRUCTION_BLOCK:
                self._handle_instruction_block_state(line)

        # Handle any remaining current_file
        if self.current_file and self.current_code_block:
            self.current_file.content = self.current_code_block
            self.files.append(self.current_file)

        print(
            f"DEBUG: CustomParser.parse - Parsing complete. Found {len(self.files)} files and {self.code_block_count} code blocks")
        return self._generate_report()

    def _handle_scanning_state(self, line):
        """
        Handle the scanning state of the parser.

        Args:
            line (str): The line to process.
        """
        print(
            f"DEBUG: CustomParser._handle_scanning_state - Processing line: {line[:30]}...")
        file_path = self._extract_file_path(line)
        if file_path:
            if self.current_file:
                self.files.append(self.current_file)
            self.current_file = FileInfo(file_path, [])
            self.state = ParserState.IN_CODE_BLOCK
            self.current_code_block = []
            print(
                f"DEBUG: CustomParser._handle_scanning_state - Found file path: {file_path}")
        elif line.strip().startswith('```'):
            self.state = ParserState.IN_CODE_BLOCK
            self.current_file = None
            self.current_code_block = []
            self.code_block_count += 1
            print(
                "DEBUG: CustomParser._handle_scanning_state - Started code block without file path")

    def _handle_code_block_state(self, line):
        """
        Handle the code block state of the parser.

        Args:
            line (str): The line to process.
        """
        print(
            "DEBUG: CustomParser._handle_code_block_state - Processing line in code block")
        if line.strip().startswith('```'):
            self.state = ParserState.SCANNING
            if self.current_file:
                self.current_file.content = self.current_code_block
                self.files.append(self.current_file)
                self.current_file = None
            print("DEBUG: CustomParser._handle_code_block_state - Ended code block")
        else:
            self.current_code_block.append(line)

    def _handle_instruction_block_state(self, line):
        """
        Handle the instruction block state of the parser.

        Args:
            line (str): The line to process.
        """
        print("DEBUG: CustomParser._handle_instruction_block_state - Processing line in instruction block")
        if line.strip().startswith('```'):
            self.state = ParserState.SCANNING
            print(
                "DEBUG: CustomParser._handle_instruction_block_state - Ended instruction block")
        else:
            self.instruction_blocks[-1].append(line)

    def _extract_file_path(self, line):
        """
        Extract the file path from a line.

        Args:
            line (str): The line to extract the file path from.

        Returns:
            str: The extracted file path, or None if no valid path is found.
        """
        print(
            f"DEBUG: CustomParser._extract_file_path - Attempting to extract file path from: {line[:30]}...")
        file_extension = os.path.splitext(line)[-1].lower()

        for file_type, type_config in self.config['file_types'].items():
            if file_extension in type_config['extensions']:
                for comment_style in type_config['comment_styles']:
                    for comment_prefix in self.config['comment_styles'][comment_style]:
                        if line.strip().startswith(comment_prefix):
                            potential_path = line.strip(
                            )[len(comment_prefix):].strip()
                            if self._is_valid_file_path(potential_path):
                                print(
                                    f"DEBUG: CustomParser._extract_file_path - Valid file path found: {potential_path}")
                                return potential_path

        print("DEBUG: CustomParser._extract_file_path - No valid file path found")
        return None

    def _is_valid_file_path(self, path):
        """
        Check if a given path is a valid file path.

        Args:
            path (str): The path to validate.

        Returns:
            bool: True if the path is valid, False otherwise.
        """
        print(
            f"DEBUG: CustomParser._is_valid_file_path - Validating path: {path}")
        path = path.strip()
        if not path:
            print("DEBUG: CustomParser._is_valid_file_path - Path is empty")
            return False
        invalid_chars = set('<>:"|?*')
        if any(char in invalid_chars for char in path):
            print(
                "DEBUG: CustomParser._is_valid_file_path - Path contains invalid characters")
            return False
        components = re.split(r'[/\\]', path)
        for component in components:
            if not component:
                print(
                    "DEBUG: CustomParser._is_valid_file_path - Path contains empty components")
                return False
            if component in ('.', '..'):
                continue
            if not re.match(r'^[\w.-]+$', component):
                print(
                    f"DEBUG: CustomParser._is_valid_file_path - Path contains invalid component: {component}")
                return False
        print("DEBUG: CustomParser._is_valid_file_path - Path is valid")
        return True

    def _generate_report(self):
        """
        Generate a report of the parsing results.

        Returns:
            str: The generated report.
        """
        print("DEBUG: CustomParser._generate_report - Generating report")
        report = "---\n"
        report += f"Parsed: true\n"
        report += f"Files code blocks found: {len(self.files)}\n"
        report += f"Instruction blocks found: {self.instruction_block_count}\n"
        report += f"Files found: {len(self.files)}\n"
        report += f"New files created: {len(self.files)}\n"
        for i, file in enumerate(self.files, 1):
            report += f"   {i}. {file.path}\n"
        report += "Files updated: 0\n"
        report += "---\n"
        print("DEBUG: CustomParser._generate_report - Report generated")
        return report
