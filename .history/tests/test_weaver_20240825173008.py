# File: tests/test_weaver.py

import os
import pytest
from unittest.mock import Mock, patch
from pathlib import Path
from ai_response_weaver.weaver import AIResponseWeaver, FileChangeHandler


@pytest.fixture
def mock_repo():
    with patch('ai_response_weaver.weaver.Repo') as mock:
        yield mock


@pytest.fixture
def mock_observer():
    with patch('ai_response_weaver.weaver.Observer') as mock:
        yield mock


@pytest.fixture
def weaver(tmp_path, mock_repo):
    file_to_monitor = tmp_path / "monitored_file.txt"
    log_folder = tmp_path / "logs"
    return AIResponseWeaver(str(file_to_monitor), str(log_folder))


def test_init(weaver, tmp_path):
    assert weaver.file_to_monitor == str(tmp_path / "monitored_file.txt")
    assert weaver.log_folder == str(tmp_path / "logs")
    assert os.path.exists(weaver.file_to_monitor)


def test_resolve_path(weaver):
    relative_path = "test/path"
    absolute_path = weaver.resolve_path(relative_path)
    assert os.path.isabs(absolute_path)


def test_ensure_file_exists(weaver, tmp_path):
    new_file = tmp_path / "new_file.txt"
    weaver.ensure_file_exists(str(new_file))
    assert os.path.exists(new_file)
    with open(new_file, 'r') as f:
        assert f.read().startswith("# This file was created by AI Response Weaver")


def test_load_config(weaver):
    config = weaver.load_config()
    assert isinstance(config, dict)
    assert 'file_types' in config


@patch('ai_response_weaver.weaver.Observer')
def test_run(mock_observer, weaver):
    weaver.run()
    mock_observer.return_value.schedule.assert_called_once()
    mock_observer.return_value.start.assert_called_once()


def test_extract_code_blocks(weaver, tmp_path):
    content = "```python\nprint('Hello')\n```\n```javascript\nconsole.log('World')\n```"
    with open(weaver.file_to_monitor, 'w') as f:
        f.write(content)
    blocks = weaver.extract_code_blocks()
    assert len(blocks) == 2
    assert blocks[0] == ('python', "print('Hello')\n")
    assert blocks[1] == ('javascript', "console.log('World')\n")


def extract_file_info(self, code, language):
    """Extract file name and path from the first line of the code block"""
    first_line = code.split('\n')[0].strip()
    for file_type, config in self.config['file_types'].items():
        if any(language.lower().endswith(ext) for ext in config['extensions']):
            match = re.match(config['regex'], first_line)
            if match:
                return match.group(1)
    return None  # Return None if no match is found


@patch('ai_response_weaver.weaver.AIResponseWeaver.git_operations')
@patch('ai_response_weaver.weaver.AIResponseWeaver.log_processed_response')
def test_create_or_update_file(mock_log, mock_git, weaver, tmp_path):
    file_path = "test/example.py"
    code = "print('Hello')"
    weaver.create_or_update_file(file_path, code)
    created_file = os.path.join(os.path.dirname(
        weaver.file_to_monitor), file_path)
    assert os.path.exists(created_file)
    with open(created_file, 'r') as f:
        assert f.read() == code
    mock_git.assert_called_once_with(file_path)
    mock_log.assert_called_once_with(file_path, code)


@patch('subprocess.run')
def test_git_operations(mock_run, weaver, mock_repo):
    file_path = "test/example.py"
    weaver.git_operations(file_path)
    mock_repo.return_value.create_head.assert_called_once()
    mock_repo.return_value.index.add.assert_called_once_with([file_path])
    mock_repo.return_value.index.commit.assert_called_once()
    mock_run.assert_called_once()


def test_log_processed_response(weaver, tmp_path):
    file_path = "test/example.py"
    content = "print('Hello')"
    weaver.log_processed_response(file_path, content)
    log_files = list(Path(weaver.log_folder).glob("*.md"))
    assert len(log_files) == 1
    with open(log_files[0], 'r') as f:
        log_content = f.read()
        assert file_path in log_content
        assert content in log_content


def test_file_change_handler(weaver):
    handler = FileChangeHandler(weaver)
    mock_event = Mock()
    mock_event.is_directory = False
    mock_event.src_path = weaver.file_to_monitor
    with patch.object(weaver, 'process_file') as mock_process:
        handler.on_modified(mock_event)
        mock_process.assert_called_once()

# Integration test


def test_end_to_end(weaver, tmp_path, mock_repo):
    # Setup
    content = "```python\n# File: test/example.py\nprint('Hello')\n```"
    with open(weaver.file_to_monitor, 'w') as f:
        f.write(content)

    # Run the weaver process
    with patch('ai_response_weaver.weaver.Observer'):
        weaver.process_file()

    # Check results
    created_file = tmp_path / "test" / "example.py"
    assert os.path.exists(created_file)
    with open(created_file, 'r') as f:
        assert f.read() == "print('Hello')\n"

    assert len(list(Path(weaver.log_folder).glob("*.md"))) == 1
    mock_repo.return_value.create_head.assert_called_once()
    mock_repo.return_value.index.add.assert_called_once()
    mock_repo.return_value.index.commit.assert_called_once()
