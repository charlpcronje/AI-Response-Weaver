# File: ai_response_weaver/ai_response_weaver.py
import os
import logging
import time
import re
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from git import Repo

from .file_change_handler import FileChangeHandler
from .config_loader import load_config
from .git_operations import git_operations
from .utils import resolve_path, ensure_file_exists


class AIResponseWeaver:
    def __init__(self, file_to_monitor: str, log_folder: str):
        self.file_to_monitor = resolve_path(file_to_monitor)
        self.log_folder = resolve_path(log_folder)
        ensure_file_exists(self.file_to_monitor)
        self.config = load_config()
        self.repo = Repo(os.getcwd())

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
        for block in code_blocks:
            self.process_code_block(block)

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
            if any(language.lower().endswith(ext) for ext in config['extensions']):
                match = re.match(config['regex'], first_line)
                if match:
                    return match.group(1)
        return None

    def create_or_update_file(self, file_path, code):
        """Create or update a file with the extracted code"""
        full_path = resolve_path(file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, 'w') as file:
            file.write(code)

        logging.info(f"Created/Updated file: {full_path}")
        git_operations(self.repo, file_path)
        self.log_processed_response(file_path, code)

    def log_processed_response(self, file_path, content):
        """Log the processed response as a markdown file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file_name = f"{timestamp}_{os.path.basename(file_path)}.md"
        log_file_path = os.path.join(self.log_folder, log_file_name)

        with open(log_file_path, 'w') as log_file:
            log_file.write(f"# Processed Response for {file_path}\n\n")
            log_file.write(f"Timestamp: {timestamp}\n\n")
            log_file.write("```\n")
            log_file.write(content)
            log_file.write("\n```\n")

        logging.info(f"Logged processed response: {log_file_path}")
