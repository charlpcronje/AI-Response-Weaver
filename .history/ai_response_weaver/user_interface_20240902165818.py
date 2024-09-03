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
