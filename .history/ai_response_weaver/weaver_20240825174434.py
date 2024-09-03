# File: ai_response_weaver/weaver.py
#!/usr/bin/env python3
"""
AI Response Weaver

This application monitors a specified file for changes, parses AI-generated code blocks,
and creates or updates corresponding files based on the content.

Usage:
    weaver <file_to_monitor> <log_folder>
"""

import os
import sys
import json
import logging
import time
import re
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from git import Repo, GitCommandError

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class AIResponseWeaver:
    def __init__(self, file_to_monitor: str, log_folder: str):
        self.file_to_monitor = self.resolve_path(file_to_monitor)
        self.log_folder = self.resolve_path(log_folder)
        self.ensure_file_exists(self.file_to_monitor)
        self.config = self.load_config()
        self.repo = Repo(os.getcwd())
        self.debug = True  # Set this to False to disable debug prints

    def resolve_path(self, path: str) -> str:
        """Resolve relative paths to absolute paths"""
        return str(Path(path).resolve())

    def ensure_file_exists(self, file_path: str):
        """Ensure that the file to be monitored exists, create if it doesn't"""
        if not os.path.exists(file_path):
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
            with open(file_path, 'w') as f:
                f.write("# This file was created by AI Response Weaver\n")
            logging.info(f"Created file to monitor: {file_path}")

    def load_config(self) -> dict:
        """Load the configuration from config.json"""
        config_path = Path(__file__).parent.parent / 'config' / 'config.json'
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
        if self.debug:
            print(f"DEBUG: Loaded config: {config}")
        return config

    def run(self):
        """Main execution method"""
        logging.info(f"Monitoring file: {self.file_to_monitor}")
        logging.info(f"Log folder: {self.log_folder}")

        event_handler = FileChangeHandler(self)
        observer = Observer()
        observer.schedule(event_handler, path=os.path.dirname(
            self.file_to_monitor), recursive=False)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    def process_file(self):
        """Process the monitored file when changes are detected"""
        logging.info(f"Processing file: {self.file_to_monitor}")
        code_blocks = self.extract_code_blocks()
        for language, code in code_blocks:
            file_path = self.extract_file_info(code, language)
            if file_path:
                self.create_or_update_file(file_path, code)
            else:
                logging.warning(
                    f"Could not extract file path from code block: {code[:50]}...")

    def extract_code_blocks(self):
        """Extract code blocks from the monitored file"""
        with open(self.file_to_monitor, 'r') as file:
            content = file.read()

        # Regular expression to match code blocks
        code_block_pattern = r'```(\w+)\n(.*?)```'
        return re.findall(code_block_pattern, content, re.DOTALL)

    def process_code_block(self, block):
        """Process a single code block"""
        language, code = block
        file_info = self.extract_file_info(code, language)
        if file_info:
            self.create_or_update_file(file_info, code)

    def extract_file_info(self, code, language):
        """Extract file name and path from the first line of the code block"""
        first_line = code.split('\n')[0].strip()
        for file_type, config in self.config['file_types'].items():
            if language.lower() in config['extensions']:
                match = re.search(config['regex'], first_line)
                if match:
                    return match.group(1)
        return None

    def create_or_update_file(self, file_path, code):
        """Create or update a file with the extracted code"""
        full_path = os.path.join(os.path.dirname(
            self.file_to_monitor), file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, 'w') as file:
            file.write(code)

        logging.info(f"Created/Updated file: {full_path}")
        self.git_operations(file_path)
        self.log_processed_response(file_path, code)

    def git_operations(self, file_path):
        """Perform Git operations for the updated file"""
        try:
            # Create a new branch
            branch_name = f"update-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            current_branch = self.repo.active_branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()

            # Stage and commit the file
            self.repo.index.add([file_path])
            self.repo.index.commit(f"Update {file_path}")

            # Switch back to the original branch
            current_branch.checkout()

            # Trigger merge in VS Code
            vscode_executable = os.getenv('VSCODE_EXECUTABLE', 'code')
            subprocess.run([vscode_executable, '--wait', '--merge',
                           current_branch.name, branch_name, file_path])

            logging.info(f"Git operations completed for {file_path}")
        except GitCommandError as e:
            logging.error(f"Git operation failed: {str(e)}")

    def log_processed_response(self, file_path, content):
        """Log the processed response as a markdown file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file_name = f"{timestamp}_{os.path.basename(file_path)}.md"
        log_file_path = os.path.join(self.log_folder, log_file_name)

        os.makedirs(self.log_folder, exist_ok=True)  # Ensure log folder exists

        with open(log_file_path, 'w') as log_file:
            log_file.write(f"# Processed Response for {file_path}\n\n")
            log_file.write(f"Timestamp: {timestamp}\n\n")
            log_file.write("```\n")
            log_file.write(content)
            log_file.write("\n```\n")

        logging.info(f"Logged processed response: {log_file_path}")

        logging.info(f"Logged processed response: {log_file_path}")


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, weaver):
        self.weaver = weaver

    def on_modified(self, event):
        if not event.is_directory and event.src_path == self.weaver.file_to_monitor:
            self.weaver.process_file()


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)

    file_to_monitor = sys.argv[1]
    log_folder = sys.argv[2]

    weaver = AIResponseWeaver(file_to_monitor, log_folder)
    weaver.run()


if __name__ == "__main__":
    main()
