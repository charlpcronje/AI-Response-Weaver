#!/bin/bash
# File: create_project_structure.sh

# Create directory structure
mkdir -p ai_response_weaver config

# Create and populate ai_response_weaver/__init__.py
cat << EOF > ai_response_weaver/__init__.py
# File: ai_response_weaver/__init__.py
from .weaver import AIResponseWeaver
EOF

# Create and populate ai_response_weaver/weaver.py
cat << EOF > ai_response_weaver/weaver.py
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AIResponseWeaver:
    def __init__(self, file_to_monitor: str, log_folder: str):
        self.file_to_monitor = file_to_monitor
        self.log_folder = log_folder
        self.config = self.load_config()
        self.repo = Repo(os.getcwd())

    def load_config(self) -> dict:
        """Load the configuration from config.json"""
        config_path = Path(__file__).parent.parent / 'config' / 'config.json'
        with open(config_path, 'r') as config_file:
            return json.load(config_file)

    def run(self):
        """Main execution method"""
        logging.info(f"Monitoring file: {self.file_to_monitor}")
        logging.info(f"Log folder: {self.log_folder}")
        
        event_handler = FileChangeHandler(self)
        observer = Observer()
        observer.schedule(event_handler, path=os.path.dirname(self.file_to_monitor), recursive=False)
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
        code_block_pattern = r'\`\`\`(\w+)\n(.*?)\`\`\`'
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
                match = re.match(config['regex'], first_line)
                if match:
                    return match.group(1)
        return None

    def create_or_update_file(self, file_path, code):
        """Create or update a file with the extracted code"""
        full_path = os.path.join(os.getcwd(), file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Remove the first line (file info) from the code
        code_lines = code.split('\n')[1:]
        code_content = '\n'.join(code_lines)
        
        with open(full_path, 'w') as file:
            file.write(code_content)
        
        logging.info(f"Created/Updated file: {full_path}")
        self.git_operations(file_path)
        self.log_processed_response(file_path, code_content)

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
            subprocess.run([vscode_executable, '--wait', '--merge', current_branch.name, branch_name, file_path])

            logging.info(f"Git operations completed for {file_path}")
        except GitCommandError as e:
            logging.error(f"Git operation failed: {str(e)}")

    def log_processed_response(self, file_path, content):
        """Log the processed response as a markdown file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file_name = f"{timestamp}_{os.path.basename(file_path)}.md"
        log_file_path = os.path.join(self.log_folder, log_file_name)

        with open(log_file_path, 'w') as log_file:
            log_file.write(f"# Processed Response for {file_path}\n\n")
            log_file.write(f"Timestamp: {timestamp}\n\n")
            log_file.write("\`\`\`\n")
            log_file.write(content)
            log_file.write("\n\`\`\`\n")

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
EOF

# Create and populate config/config.json
cat << EOF > config/config.json
// File: config/config.json
{
  "file_types": {
    "python": {
      "extensions": [".py"],
      "comment_syntax": "#",
      "regex": "^#\\s*File:\\s*(.+)$"
    },
    "javascript": {
      "extensions": [".js"],
      "comment_syntax": "//",
      "regex": "^//\\s*File:\\s*(.+)$"
    },
    "html": {
      "extensions": [".html", ".htm"],
      "comment_syntax": "<!--",
      "regex": "^<!--\\s*File:\\s*(.+)\\s*-->$"
    },
    "css": {
      "extensions": [".css"],
      "comment_syntax": "/*",
      "regex": "^/\\*\\s*File:\\s*(.+)\\s*\\*/$"
    },
    "markdown": {
      "extensions": [".md"],
      "comment_syntax": "<!--",
      "regex": "^<!--\\s*File:\\s*(.+)\\s*-->$"
    }
  }
}
EOF

# Create and populate setup.py
cat << EOF > setup.py
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
EOF

# Create and populate requirements.txt
cat << EOF > requirements.txt
# File: requirements.txt
watchdog==2.1.9
gitpython==3.1.30
python-dotenv>=1.0.0,<2.0.0
chainlit==1.0.0
-e .
EOF

# Create and populate .gitignore
cat << EOF > .gitignore
# File: .gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
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
EOF

echo "Project structure and files created successfully."