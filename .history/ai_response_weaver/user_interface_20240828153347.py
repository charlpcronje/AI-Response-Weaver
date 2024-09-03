# user_interface.py

import os
from typing import List, Tuple
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import TerminalFormatter


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

    def display_code_block_info(self, line_number: int, file_extension: str):
        """
        Display information about the current code block.

        Args:
            line_number (int): The current line number in the document.
            file_extension (str): The file extension of the code block.
        """
        print(f"\nParsing paused at line {line_number}")
        print(
            f"Comment Style for: {file_extension} can be found next to ``` opening code block ticks")
        print("-" * 40)

    def display_code_block(self, highlighted_code: str, start_line: int, total_lines: int):
        """
        Display a code block to the user, 20 lines at a time.

        Args:
            highlighted_code (str): The syntax-highlighted code block.
            start_line (int): The starting line number of the code block.
            total_lines (int): The total number of lines in the code block.
        """
        lines = highlighted_code.split('\n')
        total_pages = (len(lines) - 1) // self.lines_per_page + 1
        current_page = 0

        while True:
            start = current_page * self.lines_per_page
            end = start + self.lines_per_page
            print(
                f"\n----------- Lines {start_line + start}-{start_line + end - 1} of {start_line + total_lines - 1} ------------")
            for i, line in enumerate(lines[start:end], start + 1):
                print(f"{start_line + i - 1:4d} | {line}")
            print("-" * 60)
            print(f"Page {current_page + 1} of {total_pages}")
            print(
                "Press 'n' for next page, 'p' for previous page, or 'q' to quit viewing.")
            choice = input().lower()
            if choice == 'n' and current_page < total_pages - 1:
                current_page += 1
            elif choice == 'p' and current_page > 0:
                current_page -= 1
            elif choice == 'q':
                break

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

    def prompt_for_code_block_action(self) -> str:
        """
        Prompt the user for action on a code block without a clear file path.

        Returns:
            str: The selected action ('instruction' or 'manual').
        """
        print(
            "\nThis code block doesn't have a clear file path. What would you like to do?")
        print("1. Treat as instruction block")
        print("2. Enter file path manually")

        while True:
            choice = input("Enter your choice (1 or 2): ").strip()
            if choice == '1':
                return 'instruction'
            elif choice == '2':
                return 'manual'
            else:
                print("Invalid choice. Please enter 1 or 2.")

    def prompt_for_manual_file_path(self) -> str:
        """
        Prompt the user to manually enter a file path.

        Returns:
            str: The manually entered file path.
        """
        return input("Enter the file path for this code block: ").strip()

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
