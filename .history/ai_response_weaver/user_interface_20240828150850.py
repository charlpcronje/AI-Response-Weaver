# user_interface.py

import os
from typing import List, Tuple


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
        self.current_page = 0
        self.lines_per_page = 20

    def display_code_block(self, code_block: List[str]):
        """
        Display a code block to the user, 20 lines at a time.

        Args:
            code_block (List[str]): The code block to display.
        """
        total_pages = (len(code_block) - 1) // self.lines_per_page + 1
        while True:
            start = self.current_page * self.lines_per_page
            end = start + self.lines_per_page
            print("\n".join(code_block[start:end]))
            print(f"\nPage {self.current_page + 1} of {total_pages}")
            print(
                "Press 'n' for next page, 'p' for previous page, or 'q' to quit viewing.")
            choice = input().lower()
            if choice == 'n' and self.current_page < total_pages - 1:
                self.current_page += 1
            elif choice == 'p' and self.current_page > 0:
                self.current_page -= 1
            elif choice == 'q':
                break

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
        print(f"{len(available_styles) + 1}. This is an instruction block")
        print(f"{len(available_styles) + 2}. Enter file path manually")

        while True:
            try:
                choice = int(input("Enter your choice: "))
                if 1 <= choice <= len(available_styles):
                    return available_styles[choice - 1]
                elif choice == len(available_styles) + 1:
                    return "instruction"
                elif choice == len(available_styles) + 2:
                    return "manual"
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    def prompt_for_manual_file_path(self) -> str:
        """
        Prompt the user to manually enter a file path.

        Returns:
            str: The manually entered file path.
        """
        return input("Enter the file path for this code block: ").strip()

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
