import os
import sys
import json
import re
import logging
import time
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from git import Repo, GitCommandError
import subprocess

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class ParserState:
    SCANNING = 1
    IN_CODE_BLOCK = 2
    IN_INSTRUCTION_BLOCK = 3


class FileInfo:
    def __init__(self, path, content):
        self.path = path
        self.content = content


class CustomParser:
    def __init__(self, config, debug=False):
        self.config = config
        self.debug = debug
        self.state = ParserState.SCANNING
        self.current_file = None
        self.instruction_blocks = []
        self.files = []
        self.code_block_count = 0
        self.instruction_block_count = 0

    def parse(self, content):
        if self.debug:
            print(f"DEBUG: CustomParser.parse - Starting to parse content")
        lines = content.split('\n')
        for line in lines:
            if self.state == ParserState.SCANNING:
                self._handle_scanning_state(line)
            elif self.state == ParserState.IN_CODE_BLOCK:
                self._handle_code_block_state(line)
            elif self.state == ParserState.IN_INSTRUCTION_BLOCK:
                self._handle_instruction_block_state(line)
        if self.debug:
            print(
                f"DEBUG: CustomParser.parse - Parsing complete. Found {len(self.files)} files and {len(self.instruction_blocks)} instruction blocks")
        return self._generate_report()

    def _handle_scanning_state(self, line):
        if self.debug:
            print(
                f"DEBUG: CustomParser._handle_scanning_state - Processing line: {line[:30]}...")
        file_path = self._extract_file_path(line)
        if file_path:
            if self.current_file:
                self.files.append(self.current_file)
            self.current_file = FileInfo(file_path, [])
            self.state = ParserState.IN_CODE_BLOCK
            if self.debug:
                print(
                    f"DEBUG: CustomParser._handle_scanning_state - Found file path: {file_path}")
        elif line.strip().startswith('```'):
            self.state = ParserState.IN_INSTRUCTION_BLOCK
            self.instruction_blocks.append([])
            self.instruction_block_count += 1
            if self.debug:
                print(
                    f"DEBUG: CustomParser._handle_scanning_state - Started instruction block")

    def _handle_code_block_state(self, line):
        if self.debug:
            print(
                f"DEBUG: CustomParser._handle_code_block_state - Processing line in code block")
        if line.strip().startswith('```'):
            self.state = ParserState.SCANNING
            if self.debug:
                print(f"DEBUG: CustomParser._handle_code_block_state - Ended code block")
        else:
            self.current_file.content.append(line)

    def _handle_instruction_block_state(self, line):
        if self.debug:
            print(
                f"DEBUG: CustomParser._handle_instruction_block_state - Processing line in instruction block")
        if line.strip().startswith('```'):
            self.state = ParserState.SCANNING
            if self.debug:
                print(
                    f"DEBUG: CustomParser._handle_instruction_block_state - Ended instruction block")
        else:
            self.instruction_blocks[-1].append(line)

    def _extract_file_path(self, line):
        if self.debug:
            print(
                f"DEBUG: CustomParser._extract_file_path - Attempting to extract file path from: {line[:30]}...")
        for file_type, type_config in self.config['file_types'].items():
            for comment_style in type_config['comment_styles']:
                for comment_prefix in self.config['comment_styles'][comment_style]:
                    if line.strip().startswith(comment_prefix):
                        potential_path = line.strip(
                        )[len(comment_prefix):].strip()
                        if self._is_valid_file_path(potential_path):
                            if self.debug:
                                print(
                                    f"DEBUG: CustomParser._extract_file_path - Valid file path found: {potential_path}")
                            return potential_path
        if self.debug:
            print(f"DEBUG: CustomParser._extract_file_path - No valid file path found")
        return None

    def _is_valid_file_path(self, path):
        if self.debug:
            print(
                f"DEBUG: CustomParser._is_valid_file_path - Validating path: {path}")
        path = path.strip()
        if not path:
            if self.debug:
                print(f"DEBUG: CustomParser._is_valid_file_path - Path is empty")
            return False
        invalid_chars = set('<>:"|?*')
        if any(char in invalid_chars for char in path):
            if self.debug:
                print(
                    f"DEBUG: CustomParser._is_valid_file_path - Path contains invalid characters")
            return False
        components = re.split(r'[/\\]', path)
        for component in components:
            if not component:
                if self.debug:
                    print(
                        f"DEBUG: CustomParser._is_valid_file_path - Path contains empty components")
                return False
            if component in ('.', '..'):
                continue
            if not re.match(r'^[\w.-]+$', component):
                if self.debug:
                    print(
                        f"DEBUG: CustomParser._is_valid_file_path - Path contains invalid component: {component}")
                return False
        if self.debug:
            print(f"DEBUG: CustomParser._is_valid_file_path - Path is valid")
        return True

    def _generate_report(self):
        if self.debug:
            print(f"DEBUG: CustomParser._generate_report - Generating report")
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
        if self.debug:
            print(f"DEBUG: CustomParser._generate_report - Report generated")
        return report


class AIResponseWeaver:
    def __init__(self, file_to_monitor, log_folder, config, debug=False):
        self.file_to_monitor = file_to_monitor
        self.log_folder = log_folder
        self.config = config
        self.debug = debug
        self.parser = CustomParser(config, debug=debug)
        self.repo = Repo(os.getcwd())

    def process_file(self):
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver.process_file - Starting to process file: {self.file_to_monitor}")
        with open(self.file_to_monitor, 'r') as file:
            content = file.read()

        if content.startswith('---\nParsed: true\n'):
            if self.debug:
                print(
                    f"DEBUG: AIResponseWeaver.process_file - File already parsed. Skipping.")
            return

        report = self.parser.parse(content)

        # Check for existing files and duplicates
        existing_files = []
        new_files = []
        for file_info in self.parser.files:
            if os.path.exists(file_info.path):
                existing_files.append(file_info)
            else:
                new_files.append(file_info)

        # Create new files
        for file_info in new_files:
            self._create_file(file_info)

        # Update existing files
        if existing_files:
            branch_name = self._create_branch(existing_files)
            for file_info in existing_files:
                self._update_file(file_info)
            self._commit_changes(branch_name)
            self._trigger_merge(branch_name)

        # Update the monitored file with the report
        self._update_monitored_file(report, content)

        # Log instruction blocks
        self._log_instruction_blocks()

        if self.debug:
            print(f"DEBUG: AIResponseWeaver.process_file - File processing complete")

    def _create_file(self, file_info):
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._create_file - Creating new file: {file_info.path}")
        os.makedirs(os.path.dirname(file_info.path), exist_ok=True)
        with open(file_info.path, 'w') as file:
            file.write('\n'.join(file_info.content))
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._create_file - File created: {file_info.path}")

    def _update_file(self, file_info):
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._update_file - Updating file: {file_info.path}")
        # Create backup
        backup_path = self._create_backup(file_info.path)
        # Update file
        with open(file_info.path, 'w') as file:
            file.write('\n'.join(file_info.content))
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._update_file - File updated: {file_info.path}, Backup created: {backup_path}")

    def _create_backup(self, file_path):
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._create_backup - Creating backup for file: {file_path}")
        backup_dir = os.path.join(self.log_folder, "history")
        os.makedirs(backup_dir, exist_ok=True)
        file_name = os.path.basename(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"{file_name}-{timestamp}")
        shutil.copy2(file_path, backup_path)
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._create_backup - Backup created: {backup_path}")
        return backup_path

    def _create_branch(self, files_to_update):
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._create_branch - Creating new branch for updates")
        branch_name = f"update-{'-'.join([os.path.basename(f.path) for f in files_to_update])}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        new_branch = self.repo.create_head(branch_name)
        new_branch.checkout()
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._create_branch - New branch created: {branch_name}")
        return branch_name

    def _commit_changes(self, branch_name):
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._commit_changes - Committing changes to branch: {branch_name}")
        self.repo.git.add(A=True)
        self.repo.index.commit(f"Update files in branch {branch_name}")
        if self.debug:
            print(f"DEBUG: AIResponseWeaver._commit_changes - Changes committed")

    def _trigger_merge(self, branch_name):
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._trigger_merge - Triggering merge for branch: {branch_name}")
        vscode_executable = os.getenv('VSCODE_EXECUTABLE', 'code')
        try:
            subprocess.run([vscode_executable, '--wait',
                           '--merge', 'main', branch_name], check=True)
            if self.debug:
                print(
                    f"DEBUG: AIResponseWeaver._trigger_merge - Merge triggered in VS Code")
        except subprocess.CalledProcessError as e:
            if self.debug:
                print(
                    f"DEBUG: AIResponseWeaver._trigger_merge - Error triggering merge: {str(e)}")

    def _update_monitored_file(self, report, content):
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._update_monitored_file - Updating monitored file with report")
        updated_content = report + content
        with open(self.file_to_monitor, 'w') as file:
            file.write(updated_content)
        # Copy to log folder
        log_file_path = os.path.join(
            self.log_folder, f"parsed_{os.path.basename(self.file_to_monitor)}")
        shutil.copy2(self.file_to_monitor, log_file_path)
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._update_monitored_file - Monitored file updated and copied to: {log_file_path}")

    def _log_instruction_blocks(self):
        if self.debug:
            print(
                f"DEBUG: AIResponseWeaver._log_instruction_blocks - Logging instruction blocks")
        for i, block in enumerate(self.parser.instruction_blocks, 1):
            log_file_path = os.path.join(
                self.log_folder, f"instruction_block_{i}.md")
            with open(log_file_path, 'w') as file:
                file.write('\n'.join(block))
            if self.debug:
                print(
                    f"DEBUG: AIResponseWeaver._log_instruction_blocks - Instruction block logged: {log_file_path}")


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, weaver):
        self.weaver = weaver

    def on_modified(self, event):
        if not event.is_directory and event.src_path == self.weaver.file_to_monitor:
            if self.weaver.debug:
                print(
                    f"DEBUG: FileChangeHandler.on_modified - File change detected: {event.src_path}")
            self.weaver.process_file()


def load_config():
    config_path = os.path.join(os.path.dirname(
        __file__), '..', 'config', 'config.json')
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    return config


def get_weaver_settings():
    parser = argparse.ArgumentParser(description="AI Response Weaver")
    parser.add_argument("file_to_monitor", nargs="?",
                        help="File to monitor for changes")
    parser.add_argument("log_folder", nargs="?", help="Folder to store logs")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode")
    args = parser.parse_args()

    weaver_file = Path('.weaver')
    if weaver_file.exists():
        print("Found .weaver file. Loading settings...")
        with open(weaver_file, 'r') as f:
            settings = json.load(f)
        print(f"Settings loaded from .weaver file:")
        print(f"  File to monitor: {settings['file_to_monitor']}")
        print(f"  Log folder: {settings['log_folder']}")
        print(
            f"  Debug mode: {'Enabled' if settings.get('debug', False) else 'Disabled'}")
    else:
        print("No .weaver file found.")
        settings = {}

    if args.file_to_monitor:
        settings['file_to_monitor'] = args.file_to_monitor
    if args.log_folder:
        settings['log_folder'] = args.log_folder
    if args.debug:
        settings['debug'] = True

    if 'file_to_monitor' not in settings or 'log_folder' not in settings:
        print("\nMissing required settings. Please provide the following:")
        if 'file_to_monitor' not in settings:
            settings['file_to_monitor'] = input(
                "Enter the file to monitor (default: weaver.md): ") or "weaver.md"
        if 'log_folder' not in settings:
            settings['log_folder'] = input(
                "Enter the log folder (default: weaver_logs): ") or "weaver_logs"

    with open(weaver_file, 'w') as f:
        json.dump(settings, f)
    print("\nSettings saved to .weaver file.")

    return settings['file_to_monitor'], settings['log_folder'], settings.get('debug', False)


def main():
    print("Welcome to AI Response Weaver!")
    print("Debug mode can be enabled by adding the --debug flag.")
    print("Available arguments:")
    print("  weaver [file_to_monitor] [log_folder] [--debug]")
    print("\nChecking for .weaver file...")

    file_to_monitor, log_folder, debug = get_weaver_settings()

    config = load_config()
    weaver = AIResponseWeaver(file_to_monitor, log_folder, config, debug=debug)

    print(f"\nMonitoring file: {file_to_monitor}")
    print(f"Log folder: {log_folder}")
    print(f"Debug mode: {'Enabled' if debug else 'Disabled'}")

    event_handler = FileChangeHandler(weaver)
    observer = Observer()
    observer.schedule(event_handler, path=os.path.dirname(
        file_to_monitor), recursive=False)
    observer.start()

    try:
        print("\nAI Response Weaver is now running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping AI Response Weaver...")
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
