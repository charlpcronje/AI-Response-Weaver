# File: ai_response_weaver/file_change_handler.py
from watchdog.events import FileSystemEventHandler


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, weaver):
        self.weaver = weaver

    def on_modified(self, event):
        if not event.is_directory and event.src_path == self.weaver.file_to_monitor:
            self.weaver.process_file()
