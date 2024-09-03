# File: ai_response_weaver/git_operations.py
import logging
import subprocess
from datetime import datetime
from git import GitCommandError
import os


def git_operations(repo, file_path):
    """Perform Git operations for the updated file"""
    try:
        # Create a new branch
        branch_name = f"update-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        current_branch = repo.active_branch
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()

        # Stage and commit the file
        repo.index.add([file_path])
        repo.index.commit(f"Update {file_path}")

        # Switch back to the original branch
        current_branch.checkout()

        # Trigger merge in VS Code
        vscode_executable = os.getenv('VSCODE_EXECUTABLE', 'code')
        subprocess.run([vscode_executable, '--wait', '--merge',
                       current_branch.name, branch_name, file_path])

        logging.info(f"Git operations completed for {file_path}")
    except GitCommandError as e:
        logging.error(f"Git operation failed: {str(e)}")
